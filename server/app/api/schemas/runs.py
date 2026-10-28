# Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
# Proprietary and confidential. See LICENSE in the project root.
"""Run schemas, contract sections 6.2-6.4."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import Field

from app.domain.base import CamelModel


class RunIn(CamelModel):
    code: str = Field(min_length=1, max_length=100_000)
    client_run_id: uuid.UUID


class RunCreatedOut(CamelModel):
    run_id: uuid.UUID
    status: Literal["queued"]


class TestCaseResultOut(CamelModel):
    name: str
    passed: bool
    input: str
    expected: str
    actual: str
    time_ms: int
    error: str | None = None


class CodeMetricsOut(CamelModel):
    lines: int
    functions: int
    loops: int
    max_loop_depth: int
    recursion: bool
    uses_builtins_sort: bool


class RunResultOut(CamelModel):
    verdict: Literal["passed", "failed", "error", "timeout"]
    passed: int
    total: int
    tests: list[TestCaseResultOut]
    stdout: str
    stderr: str
    truncated: bool
    metrics: CodeMetricsOut


class CodeIssueOut(CamelModel):
    line: int
    severity: Literal["error", "warning", "info"]
    text: str


class CodeReviewOut(CamelModel):
    summary: str
    issues: list[CodeIssueOut]
    suggestions: list[str]


class RunOut(CamelModel):
    run_id: uuid.UUID
    status: Literal["queued", "running", "done", "failed", "cancelled"]
    code_hash: str
    created_at: datetime
    finished_at: datetime | None = None
    result: RunResultOut | None = None
    ai_review: CodeReviewOut | None = None
    error: str | None = None
