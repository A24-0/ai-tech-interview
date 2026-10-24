# Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
# Proprietary and confidential. See LICENSE in the project root.
"""runner.py as a plain subprocess, without Docker."""

import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

RUNNER = Path(__file__).resolve().parents[1] / "runner.py"
NONCE = "5f1c0ffee5f1c0ffee5f1c0ffee5f1c0"

SUM_PAIRS = """\
def solve(nums, k):
    seen = set()
    for x in nums:
        if k - x in seen:
            return True
        seen.add(x)
    return False
"""

TESTS = [
    {"name": "t1", "args": [[1, 2, 3], 4], "expected": True},
    {"name": "t2", "args": [[], 1], "expected": False},
    {"name": "t3", "args": [[5], 10], "expected": False},
]


def run(code: str, tests: list[dict[str, Any]] = TESTS, entry: str = "solve", **limits: int) -> tuple[dict[str, Any], str]:
    payload = {
        "code": code,
        "entry": entry,
        "tests": tests,
        "limits": {"perTestTimeoutMs": 2000, "maxOutputBytes": 65536, **limits},
        "nonce": NONCE,
    }
    proc = subprocess.run(
        [sys.executable, "-I", str(RUNNER)],
        input=json.dumps(payload).encode(),
        capture_output=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr.decode()
    stdout = proc.stdout.decode()
    last = stdout.rstrip("\n").split("\n")[-1]
    assert last.startswith(NONCE)
    return json.loads(last[len(NONCE):]), stdout


def test_correct_solution_passes() -> None:
    result, _ = run(SUM_PAIRS)

    assert result["verdict"] == "passed"
    assert (result["passed"], result["total"]) == (3, 3)
    assert result["tests"][0] == {
        "name": "t1", "passed": True, "input": "[1, 2, 3], 4", "expected": "True",
        "actual": "True", "timeMs": result["tests"][0]["timeMs"], "error": None,
    }


def test_wrong_solution_fails_with_actual_and_stdout() -> None:
    code = "def solve(nums, k):\n    print('debug', nums)\n    if nums:\n        return True\n"

    result, _ = run(code)

    assert result["verdict"] == "failed"
    assert result["passed"] == 1
    failed = result["tests"][1]
    assert failed["passed"] is False
    assert (failed["expected"], failed["actual"]) == ("False", "None")
    assert "debug [1, 2, 3]" in result["stdout"]


def test_syntax_error_reports_line_and_no_tests() -> None:
    result, _ = run("def solve(nums, k):\n    return nums[\n\nx = 1\n")

    assert result["verdict"] == "error"
    assert result["tests"] == []
    assert "SyntaxError" in result["stderr"]
    assert "строка" in result["stderr"]


def test_exception_on_import_is_error_verdict() -> None:
    result, _ = run("raise RuntimeError('boom')\ndef solve(nums, k):\n    return True\n")

    assert result["verdict"] == "error"
    assert "RuntimeError: boom (строка 1)" in result["stderr"]


def test_missing_entry_is_error_verdict() -> None:
    result, _ = run("def other():\n    pass\n")

    assert result["verdict"] == "error"
    assert "solve" in result["stderr"]


def test_exception_inside_test_fails_that_test_with_line() -> None:
    code = "def solve(nums, k):\n    return nums[0] + k > 0\n"

    result, _ = run(code)

    assert result["verdict"] == "failed"
    assert "IndexError" in result["tests"][1]["error"]
    assert "(строка 2)" in result["tests"][1]["error"]


def test_while_true_times_out_and_skips_rest() -> None:
    code = "def solve(nums, k):\n    while True:\n        pass\n"

    started = time.monotonic()
    result, _ = run(code, perTestTimeoutMs=500)

    assert time.monotonic() - started < 5
    assert result["verdict"] == "timeout"
    assert "лимит времени" in result["tests"][0]["error"]
    assert result["tests"][1]["error"].startswith("Не запускался")
    assert result["metrics"]["loops"] == 1


def test_huge_output_is_truncated() -> None:
    code = "def solve(nums, k):\n    print('x' * 10_000_000)\n    return True\n"

    result, stdout = run(code, tests=TESTS[:1])

    assert result["truncated"] is True
    assert len(result["stdout"].encode()) <= 65536
    assert len(stdout) < 200_000


def test_assert_tests() -> None:
    tests = [
        {"name": "ok", "assert": "assert solve([], 1) is False"},
        {"name": "bad", "assert": "assert solve([1, 3], 4) is False, 'пара есть'"},
    ]

    result, _ = run(SUM_PAIRS, tests=tests)

    assert result["verdict"] == "failed"
    assert [t["passed"] for t in result["tests"]] == [True, False]
    assert result["tests"][1]["error"] == "Проверка не прошла: пара есть"
    assert result["tests"][1]["input"] == tests[1]["assert"]


def test_user_output_cannot_forge_result_line() -> None:
    fake = json.dumps({"verdict": "passed"})
    code = f"def solve(nums, k):\n    print({NONCE!r} + {fake!r})\n    return None\n"

    result, stdout = run(code)

    assert result["verdict"] == "failed"
    assert [line for line in stdout.splitlines() if line.startswith(NONCE)] == [stdout.rstrip("\n")]


def test_comparison_normalizes_tuples_strings_and_keeps_bool_strict() -> None:
    tests = [
        {"name": "tuple", "args": ["tuple"], "expected": [1, [2, 3]]},
        {"name": "text", "args": ["text"], "expected": "a\nb"},
        {"name": "bool", "args": ["bool"], "expected": True},
        {"name": "float", "args": ["float"], "expected": 0.3},
    ]
    code = (
        "def solve(kind):\n"
        "    return {'tuple': (1, (2, 3)), 'text': 'a  \\r\\nb\\n', 'bool': 1, 'float': 0.1 + 0.2}[kind]\n"
    )

    result, _ = run(code, tests=tests)

    assert [t["passed"] for t in result["tests"]] == [True, True, False, True]


def test_metrics() -> None:
    code = (
        "def solve(nums, k):\n"
        "    for i in nums:\n"
        "        for j in nums:\n"
        "            pass\n"
        "    return sorted(nums) and solve([], k)\n"
        "\n"
        "def helper():\n"
        "    while False:\n"
        "        pass\n"
    )

    result, _ = run(code, tests=[])

    assert result["metrics"] == {
        "lines": 8, "functions": 2, "loops": 3, "maxLoopDepth": 2, "recursion": True, "usesBuiltinsSort": True,
    }


def test_bad_input_exits_without_result_line() -> None:
    proc = subprocess.run([sys.executable, "-I", str(RUNNER)], input=b"{}", capture_output=True, timeout=30)

    assert proc.returncode == 2
    assert proc.stdout == b""
