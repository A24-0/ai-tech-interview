# Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
# Proprietary and confidential. See LICENSE in the project root.
"""FakeSandbox: fixed RunResult without running any code (SANDBOX_BACKEND=fake)."""

import asyncio
from typing import Any

from app.domain.sandbox import CodeMetrics, RunResult, TestCaseResult


class FakeSandbox:
    """2 of 3 tests pass (verdict "failed"); code with `while True` gives "timeout" after `timeout_delay_s`."""

    def __init__(self, *, timeout_delay_s: float = 1.0) -> None:
        self.timeout_delay_s = timeout_delay_s

    async def run(
        self,
        code: str,
        entry: str,
        tests: list[dict[str, Any]],
        limits: dict[str, Any],
    ) -> RunResult:
        metrics = CodeMetrics(lines=len([line for line in code.splitlines() if line.strip()]), functions=1)
        if "while True" in code:
            await asyncio.sleep(self.timeout_delay_s)
            return RunResult(
                verdict="timeout",
                passed=0,
                total=3,
                tests=[
                    TestCaseResult(
                        name="t1",
                        passed=False,
                        input="[1, 2, 3], 4",
                        expected="True",
                        time_ms=int(self.timeout_delay_s * 1000),
                        error="Превышен лимит времени",
                    )
                ],
                stderr="Превышен лимит времени",
                metrics=metrics.model_copy(update={"loops": 1, "max_loop_depth": 1}),
            )
        return RunResult(
            verdict="failed",
            passed=2,
            total=3,
            tests=[
                TestCaseResult(name="t1", passed=True, input="[1, 2, 3], 4", expected="True", actual="True", time_ms=3),
                TestCaseResult(name="t2", passed=True, input="[5], 5", expected="False", actual="False", time_ms=2),
                TestCaseResult(name="t3", passed=False, input="[], 1", expected="False", actual="None", time_ms=2),
            ],
            stdout="debug: nums=[]\n",
            metrics=metrics,
        )
