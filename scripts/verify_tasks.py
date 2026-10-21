# Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
# Proprietary and confidential. See LICENSE in the project root.
"""Checks the task bank: every reference solution passes all its tests in sandbox/runner.py.

    python scripts/verify_tasks.py [content/tasks/python_basics.json ...] [--runner sandbox/runner.py]

The runner is started as a plain subprocess (no Docker) with the stdin/stdout protocol of
the contract, section 6.5. Besides the reference solution, the starter code is run too:
it must NOT pass, otherwise the tests check nothing. Exit code 1 if anything is wrong.
"""

import argparse
import json
import secrets
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LEVELS = {"junior", "middle", "senior"}
REQUIRED = ("topicCode", "level", "title", "statement", "entry", "starterCode", "tests", "limits", "referenceSolution")


def check_shape(task: dict[str, Any]) -> list[str]:
    """Static checks that need no runner."""
    missing = [key for key in REQUIRED if not task.get(key) and task.get(key) != []]
    if missing:
        return [f"нет полей: {', '.join(missing)}"]
    problems = []
    if task["level"] not in LEVELS:
        problems.append(f"level={task['level']!r}, ожидается одно из {sorted(LEVELS)}")
    if not 5 <= len(task["tests"]) <= 8:
        problems.append(f"тестов {len(task['tests'])}, нужно от 5 до 8")
    names = [test.get("name") for test in task["tests"]]
    if len(set(names)) != len(names) or not all(names):
        problems.append("имена тестов пустые или повторяются")
    for test in task["tests"]:
        if ("assert" in test) == ("args" in test and "expected" in test):
            problems.append(f"тест {test.get('name')!r}: нужен либо assert, либо пара args/expected")
    signature = f"def {task['entry']}("
    for field in ("starterCode", "referenceSolution"):
        if signature not in task[field]:
            problems.append(f"{field} не объявляет {signature}...)")
    return problems


def run_in_runner(runner: Path, task: dict[str, Any], code: str) -> dict[str, Any]:
    nonce = secrets.token_hex(16)
    payload = {"code": code, "entry": task["entry"], "tests": task["tests"], "limits": task["limits"], "nonce": nonce}
    timeout_s = len(task["tests"]) * task["limits"]["perTestTimeoutMs"] / 1000 + 30
    completed = subprocess.run(
        [sys.executable, "-I", str(runner)],
        input=json.dumps(payload, ensure_ascii=False),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",  # a crashing runner may print its traceback in the OS code page
        timeout=timeout_s,
        check=False,  # the verdict comes from the nonce line, not the exit code
    )
    for line in reversed(completed.stdout.splitlines()):
        if line.startswith(nonce):
            return json.loads(line[len(nonce):])
    raise RuntimeError(
        f"runner не вернул строку с nonce (код {completed.returncode}): {completed.stderr.strip()[-500:]}"
    )


def failed_tests(result: dict[str, Any]) -> str:
    failed = [test for test in result.get("tests", []) if not test.get("passed")]
    details = "; ".join(
        f"{test.get('name')}: ожидалось {test.get('expected')}, получено {test.get('actual')}"
        + (f", ошибка {test.get('error')}" if test.get("error") else "")
        for test in failed
    )
    return details or result.get("stderr", "").strip()[-300:]


def verify(task: dict[str, Any], runner: Path) -> list[str]:
    problems = check_shape(task)
    if problems:
        return problems
    reference = run_in_runner(runner, task, task["referenceSolution"])
    if reference.get("verdict") != "passed" or reference.get("passed") != reference.get("total"):
        problems.append(
            f"эталон: verdict={reference.get('verdict')}, {reference.get('passed')}/{reference.get('total')} — "
            + failed_tests(reference)
        )
    if reference.get("total") != len(task["tests"]):
        problems.append(f"runner выполнил {reference.get('total')} тестов из {len(task['tests'])}")
    starter = run_in_runner(runner, task, task["starterCode"])
    if starter.get("verdict") == "passed":
        problems.append("заготовка starterCode проходит все тесты — тесты ничего не проверяют")
    return problems


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")  # Cyrillic output also through Windows pipes
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("files", nargs="*", type=Path, default=[ROOT / "content" / "tasks" / "python_basics.json"])
    parser.add_argument("--runner", type=Path, default=ROOT / "sandbox" / "runner.py")
    args = parser.parse_args()

    if not args.runner.is_file():
        print(f"Нет {args.runner}: runner.py появится с задачей S3-D1 (песочница).", file=sys.stderr)
        return 2

    titles: set[tuple[str, str]] = set()
    broken = 0
    for path in args.files:
        tasks = json.loads(path.read_text(encoding="utf-8"))["tasks"]
        print(f"{path.relative_to(ROOT) if path.is_relative_to(ROOT) else path}: задач {len(tasks)}")
        for task in tasks:
            key = (task.get("topicCode", ""), task.get("title", ""))
            problems = ["задача с таким topicCode и title уже есть"] if key in titles else []
            titles.add(key)
            problems += verify(task, args.runner)
            mark = "OK  " if not problems else "FAIL"
            print(f"  {mark} [{task.get('level')}] {task.get('title')} — тестов {len(task.get('tests', []))}")
            for problem in problems:
                print(f"         {problem}")
            broken += bool(problems)
    print("Все задачи проверены." if not broken else f"С ошибками: {broken}")
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())
