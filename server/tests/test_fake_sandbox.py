# Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
# Proprietary and confidential. See LICENSE in the project root.

import time

from app.domain.sandbox import RunResult
from app.infrastructure.sandbox.fake import FakeSandbox

LIMITS = {"perTestTimeoutMs": 2000, "maxOutputBytes": 65536}


async def test_fixed_result_two_of_three_passed() -> None:
    result = await FakeSandbox().run("def solve(nums, k):\n    return None\n", "solve", [], LIMITS)

    assert result.verdict == "failed"
    assert (result.passed, result.total) == (2, 3)
    assert [test.passed for test in result.tests] == [True, True, False]
    assert result.metrics.lines == 2


async def test_while_true_gives_timeout_after_delay() -> None:
    sandbox = FakeSandbox(timeout_delay_s=0.1)

    started = time.monotonic()
    result = await sandbox.run("def solve():\n    while True:\n        pass\n", "solve", [], LIMITS)

    assert result.verdict == "timeout"
    assert time.monotonic() - started >= 0.1


async def test_default_timeout_delay_is_one_second() -> None:
    assert FakeSandbox().timeout_delay_s == 1.0


def test_run_result_round_trips_contract_json() -> None:
    payload = {
        "verdict": "failed",
        "passed": 1,
        "total": 2,
        "tests": [
            {"name": "t1", "passed": True, "input": "[1], 1", "expected": "True", "actual": "True", "timeMs": 3, "error": None},
            {"name": "t2", "passed": False, "input": "[], 1", "expected": "False", "actual": "None", "timeMs": 2, "error": None},
        ],
        "stdout": "",
        "stderr": "",
        "truncated": False,
        "metrics": {"lines": 3, "functions": 1, "loops": 1, "maxLoopDepth": 1, "recursion": False, "usesBuiltinsSort": False},
    }

    result = RunResult.model_validate(payload)

    assert result.tests[0].time_ms == 3
    assert result.metrics.max_loop_depth == 1
    assert result.model_dump(mode="json") == payload
