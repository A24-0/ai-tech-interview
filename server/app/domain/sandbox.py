# Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
# Proprietary and confidential. See LICENSE in the project root.
"""Sandbox contracts: RunResult produced by runner.py (contract 6.3, 6.5) and the Sandbox protocol (7)."""

from typing import Any, ClassVar, Literal, Protocol

from pydantic import Field

from app.domain.base import CamelModel

Verdict = Literal["passed", "failed", "error", "timeout"]


class TestCaseResult(CamelModel):
    __test__: ClassVar[bool] = False  # not a pytest test class

    name: str
    passed: bool
    input: str = ""
    expected: str | None = None
    actual: str | None = None
    time_ms: int = 0
    error: str | None = None


class CodeMetrics(CamelModel):
    lines: int = 0
    functions: int = 0
    loops: int = 0
    max_loop_depth: int = 0
    recursion: bool = False
    uses_builtins_sort: bool = False


class RunResult(CamelModel):
    verdict: Verdict
    passed: int = 0
    total: int = 0
    tests: list[TestCaseResult] = Field(default_factory=list)
    stdout: str = ""
    stderr: str = ""
    truncated: bool = False
    metrics: CodeMetrics = Field(default_factory=CodeMetrics)


class SandboxError(Exception):
    """Failure of the sandbox itself, not of the user's code. The run becomes `failed`."""


class Sandbox(Protocol):
    async def run(
        self,
        code: str,
        entry: str,
        tests: list[dict[str, Any]],
        limits: dict[str, Any],
    ) -> RunResult:
        """Run `code` against `tests` (format of code_tasks.tests, contract 6.5).

        Timeouts are reported as verdict "timeout"; only SandboxError is raised.
        """
        ...
