# Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
# Proprietary and confidential. See LICENSE in the project root.
"""Sandbox runner: checks a solution against tests and prints a RunResult (contract 6.3, 6.5).

stdin:  {"code", "entry", "tests", "limits": {"perTestTimeoutMs", "maxOutputBytes"}, "nonce"}
stdout: the only line is <nonce>{RunResult JSON}.

The user's code is never imported here: metrics come from `ast`, every test runs in its
own `python -I -S` process. The nonce never leaves this process, so user output cannot
forge the result line.
"""

import ast
import json
import math
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
from dataclasses import dataclass, field
from typing import Any

DEFAULT_TEST_TIMEOUT_MS = 2000
DEFAULT_MAX_OUTPUT_BYTES = 65536
RESULT_LIMIT_BYTES = 1 << 20
READ_CHUNK = 65536
CHILD_ENV = {"PATH": "/usr/local/bin:/usr/bin:/bin", "LANG": "C.UTF-8"}

# Runs inside the per-test process. Reads its config from stdin before importing the
# solution and reports through a dedicated pipe, so stdout/stderr stay the user's.
DRIVER = r"""
import json, os, sys, time, traceback

cfg = json.loads(sys.stdin.read())
sys.path.insert(0, cfg["dir"])
SOLUTION = os.path.join(cfg["dir"], "solution.py")
RESULT_FD = cfg["resultFd"]


def emit(data):
    try:
        payload = json.dumps(data, ensure_ascii=False)
    except (TypeError, ValueError):
        data["repr"] = repr(data.pop("value"))
        payload = json.dumps(data, ensure_ascii=False)
    sys.stdout.flush()
    sys.stderr.flush()
    with os.fdopen(RESULT_FD, "w", encoding="utf-8") as out:
        out.write(payload)


def describe(exc):
    text = "".join(traceback.format_exception_only(type(exc), exc)).strip()
    for frame in reversed(traceback.extract_tb(exc.__traceback__)):
        if frame.filename == SOLUTION:
            return f"{text} (строка {frame.lineno})"
    return text


def plain(value):
    if isinstance(value, (list, tuple)):
        return [plain(item) for item in value]
    if isinstance(value, dict):
        return {str(key): plain(item) for key, item in value.items()}
    if isinstance(value, (set, frozenset)):
        items = [plain(item) for item in value]
        try:
            return sorted(items)
        except TypeError:
            return items
    return value


try:
    import solution
except BaseException as exc:
    emit({"stage": "import", "error": describe(exc)})
    sys.exit(0)

test = cfg["test"]
started = time.perf_counter()
elapsed = lambda: int((time.perf_counter() - started) * 1000)

if "assert" in test:
    try:
        exec(compile(test["assert"], "<test>", "exec"), vars(solution))
    except AssertionError as exc:
        message = "Проверка не прошла" + (f": {exc}" if str(exc) else "")
        emit({"stage": "test", "ok": False, "error": message, "timeMs": elapsed()})
    except BaseException as exc:
        emit({"stage": "test", "ok": False, "error": describe(exc), "timeMs": elapsed()})
    else:
        emit({"stage": "test", "ok": True, "timeMs": elapsed()})
else:
    entry = getattr(solution, cfg["entry"], None)
    if not callable(entry):
        emit({"stage": "import", "error": f"Не найдена функция {cfg['entry']}"})
        sys.exit(0)
    try:
        value = entry(*test.get("args", []))
    except BaseException as exc:
        emit({"stage": "test", "error": describe(exc), "timeMs": elapsed()})
    else:
        took = elapsed()
        emit({"stage": "test", "value": plain(value), "timeMs": took})
"""


class Capture(threading.Thread):
    """Drains a pipe, keeping at most `limit` bytes so a flood of output cannot exhaust memory."""

    def __init__(self, fd: int, limit: int) -> None:
        super().__init__(daemon=True)
        self.fd = fd
        self.limit = limit
        self.data = bytearray()
        self.overflow = False

    def run(self) -> None:
        try:
            while chunk := os.read(self.fd, READ_CHUNK):
                room = self.limit - len(self.data)
                if len(chunk) > room:
                    self.overflow = True
                    chunk = chunk[: max(room, 0)]
                self.data += chunk
        except OSError:
            pass
        finally:
            os.close(self.fd)


@dataclass
class TestRun:
    stdout: bytes
    stderr: bytes
    truncated: bool
    report: dict[str, Any] | None
    timed_out: bool
    returncode: int | None


@dataclass
class Metrics:
    lines: int = 0
    functions: int = 0
    loops: int = 0
    maxLoopDepth: int = 0
    recursion: bool = False
    usesBuiltinsSort: bool = False


@dataclass
class Outcome:
    tests: list[dict[str, Any]] = field(default_factory=list)
    stdout: bytearray = field(default_factory=bytearray)
    stderr: bytearray = field(default_factory=bytearray)
    truncated: bool = False
    error: str | None = None
    timed_out: bool = False


class _MetricsVisitor(ast.NodeVisitor):
    def __init__(self, metrics: Metrics) -> None:
        self.m = metrics
        self.depth = 0
        self.functions: list[str] = []

    def _function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        self.m.functions += 1
        outer_depth, self.depth = self.depth, 0
        self.functions.append(node.name)
        self.generic_visit(node)
        self.functions.pop()
        self.depth = outer_depth

    visit_FunctionDef = _function
    visit_AsyncFunctionDef = _function

    def _loop(self, node: ast.For | ast.AsyncFor | ast.While) -> None:
        self.m.loops += 1
        self.depth += 1
        self.m.maxLoopDepth = max(self.m.maxLoopDepth, self.depth)
        self.generic_visit(node)
        self.depth -= 1

    visit_For = _loop
    visit_AsyncFor = _loop
    visit_While = _loop

    def visit_Call(self, node: ast.Call) -> None:
        func = node.func
        name = func.id if isinstance(func, ast.Name) else func.attr if isinstance(func, ast.Attribute) else None
        if (isinstance(func, ast.Name) and name == "sorted") or (isinstance(func, ast.Attribute) and name == "sort"):
            self.m.usesBuiltinsSort = True
        if self.functions and name == self.functions[-1]:
            own_call = isinstance(func, ast.Name) or (
                isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name) and func.value.id in ("self", "cls")
            )
            self.m.recursion = self.m.recursion or own_call
        self.generic_visit(node)


def analyze(code: str) -> tuple[Metrics, str | None]:
    """Static metrics without executing the code; second item is a syntax error message."""
    metrics = Metrics(lines=sum(1 for line in code.splitlines() if line.strip()))
    try:
        tree = ast.parse(code, filename="solution.py")
    except SyntaxError as exc:
        return metrics, f"SyntaxError: {exc.msg} (строка {exc.lineno})"
    except ValueError as exc:
        return metrics, f"SyntaxError: {exc}"
    _MetricsVisitor(metrics).visit(tree)
    return metrics, None


def normalize_text(text: str) -> str:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    return "\n".join(line.rstrip() for line in lines).strip()


def same(expected: Any, actual: Any) -> bool:
    if isinstance(expected, bool) or isinstance(actual, bool):
        return type(expected) is type(actual) and expected == actual
    if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
        if isinstance(expected, float) or isinstance(actual, float):
            return math.isclose(expected, actual, rel_tol=1e-9, abs_tol=1e-9)
        return expected == actual
    if isinstance(expected, str) and isinstance(actual, str):
        return normalize_text(expected) == normalize_text(actual)
    if isinstance(expected, list) and isinstance(actual, list):
        return len(expected) == len(actual) and all(map(same, expected, actual))
    if isinstance(expected, dict) and isinstance(actual, dict):
        return expected.keys() == actual.keys() and all(same(expected[k], actual[k]) for k in expected)
    return type(expected) is type(actual) and expected == actual


def run_one(workdir: str, entry: str, test: dict[str, Any], timeout_s: float, cap: int) -> TestRun:
    result_r, result_w = os.pipe()
    proc = subprocess.Popen(
        [sys.executable, "-I", "-S", "-B", "-X", "utf8", "-c", DRIVER],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        pass_fds=(result_w,),
        cwd=workdir,
        env=CHILD_ENV,
        start_new_session=True,
    )
    os.close(result_w)
    assert proc.stdin and proc.stdout and proc.stderr
    readers = [
        Capture(os.dup(proc.stdout.fileno()), cap),
        Capture(os.dup(proc.stderr.fileno()), cap),
        Capture(result_r, RESULT_LIMIT_BYTES),
    ]
    proc.stdout.close()
    proc.stderr.close()
    for reader in readers:
        reader.start()

    try:
        proc.stdin.write(json.dumps({"dir": workdir, "entry": entry, "test": test, "resultFd": result_w}).encode())
        proc.stdin.close()
    except BrokenPipeError:
        pass

    timed_out = False
    try:
        proc.wait(timeout=timeout_s)
    except subprocess.TimeoutExpired:
        timed_out = True
    # Kill the whole session: also any processes the solution spawned that hold the pipes open.
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass
    proc.wait()
    for reader in readers:
        reader.join(timeout=1)

    out, err, res = readers
    report: dict[str, Any] | None = None
    if not timed_out and res.data and not res.overflow:
        try:
            parsed = json.loads(res.data.decode("utf-8", errors="replace"))
            report = parsed if isinstance(parsed, dict) else None
        except ValueError:
            report = None
    return TestRun(
        stdout=bytes(out.data),
        stderr=bytes(err.data),
        truncated=out.overflow or err.overflow,
        report=report,
        timed_out=timed_out,
        returncode=proc.returncode,
    )


def crash_message(returncode: int | None) -> str:
    if returncode == -signal.SIGKILL:
        return "Процесс решения принудительно завершён (возможно, превышен лимит памяти)"
    return f"Процесс решения завершился без результата (код {returncode})"


def run_tests(code: str, entry: str, tests: list[dict[str, Any]], timeout_ms: int, cap: int) -> Outcome:
    outcome = Outcome()
    workdir = tempfile.mkdtemp(prefix="run-")
    try:
        with open(os.path.join(workdir, "solution.py"), "w", encoding="utf-8") as f:
            f.write(code)
        for index, test in enumerate(tests):
            name = str(test.get("name") or f"t{index + 1}")
            is_assert = "assert" in test
            case: dict[str, Any] = {
                "name": name,
                "passed": False,
                "input": test["assert"] if is_assert else ", ".join(repr(arg) for arg in test.get("args", [])),
                "expected": None if is_assert else repr(test.get("expected")),
                "actual": None,
                "timeMs": 0,
                "error": None,
            }
            if outcome.timed_out:
                case["error"] = "Не запускался: предыдущий тест превысил лимит времени"
                outcome.tests.append(case)
                continue

            run = run_one(workdir, entry, test, timeout_ms / 1000, cap)
            for target, chunk in ((outcome.stdout, run.stdout), (outcome.stderr, run.stderr)):
                if chunk:
                    target += f"--- {name} ---\n".encode() + chunk + (b"" if chunk.endswith(b"\n") else b"\n")
            outcome.truncated = outcome.truncated or run.truncated
            report = run.report

            if run.timed_out:
                outcome.timed_out = True
                case["timeMs"] = timeout_ms
                case["error"] = f"Превышен лимит времени ({timeout_ms} мс)"
            elif report is None:
                case["error"] = crash_message(run.returncode)
            elif report.get("stage") == "import":
                outcome.error = str(report.get("error"))
                outcome.tests = []
                return outcome
            else:
                case["timeMs"] = int(report.get("timeMs", 0))
                case["error"] = report.get("error")
                if is_assert:
                    case["passed"] = bool(report.get("ok"))
                elif "repr" in report:
                    case["actual"] = str(report["repr"])
                elif "value" in report:
                    case["actual"] = repr(report["value"])
                    case["passed"] = same(test.get("expected"), report["value"])
            outcome.tests.append(case)
        return outcome
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def clip(data: bytes, cap: int) -> tuple[str, bool]:
    if len(data) <= cap:
        return data.decode("utf-8", errors="replace"), False
    return data[:cap].decode("utf-8", errors="replace"), True


def build_result(code: str, entry: str, tests: list[dict[str, Any]], limits: dict[str, Any]) -> dict[str, Any]:
    timeout_ms = int(limits.get("perTestTimeoutMs", DEFAULT_TEST_TIMEOUT_MS))
    cap = int(limits.get("maxOutputBytes", DEFAULT_MAX_OUTPUT_BYTES))
    metrics, syntax_error = analyze(code)
    base: dict[str, Any] = {"passed": 0, "total": len(tests), "truncated": False, "metrics": metrics.__dict__}
    if syntax_error:
        return {"verdict": "error", **base, "tests": [], "stdout": "", "stderr": syntax_error}

    outcome = run_tests(code, entry, tests, timeout_ms, cap)
    stdout, cut_out = clip(bytes(outcome.stdout), cap)
    stderr_bytes = bytes(outcome.stderr)
    if outcome.error:
        stderr_bytes = (stderr_bytes + b"\n" if stderr_bytes else b"") + outcome.error.encode()
    stderr, cut_err = clip(stderr_bytes, cap)

    passed = sum(1 for case in outcome.tests if case["passed"])
    if outcome.error:
        verdict = "error"
    elif outcome.timed_out:
        verdict = "timeout"
    elif passed == len(tests):
        verdict = "passed"
    else:
        verdict = "failed"
    return {
        "verdict": verdict,
        **base,
        "passed": passed,
        "tests": outcome.tests,
        "stdout": stdout,
        "stderr": stderr,
        "truncated": outcome.truncated or cut_out or cut_err,
    }


def main() -> int:
    try:
        payload = json.loads(sys.stdin.buffer.read().decode("utf-8"))
        code, entry, tests, nonce = payload["code"], payload["entry"], payload["tests"], payload["nonce"]
        limits = payload.get("limits") or {}
        if not (isinstance(code, str) and isinstance(entry, str) and isinstance(tests, list) and isinstance(nonce, str) and nonce):
            raise ValueError("code, entry, nonce must be strings and tests a list")
    except (ValueError, KeyError, TypeError) as exc:
        print(f"runner: bad input: {exc}", file=sys.stderr)
        return 2

    result = build_result(code, entry, tests, limits)
    sys.stdout.write(nonce + json.dumps(result, ensure_ascii=False) + "\n")
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
