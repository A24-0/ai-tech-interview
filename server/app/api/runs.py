# Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
# Proprietary and confidential. See LICENSE in the project root.
"""Run endpoints (stubs on in-memory storage), contract section 6.2."""

import os
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter

from app.api.deps import CurrentUserId
from app.api.errors import ApiError
from app.api.schemas.runs import (
    CodeIssueOut,
    CodeMetricsOut,
    CodeReviewOut,
    RunCreatedOut,
    RunIn,
    RunOut,
    RunResultOut,
    TestCaseResultOut,
)
from app.api.stub_store import StubRun, code_hash, store

router = APIRouter(tags=["runs"])

STUB_RUN_DURATION = timedelta(seconds=2)


def _runs_limit() -> int:
    return int(os.environ.get("RUNS_PER_TASK_LIMIT", "20"))


def _stub_result() -> RunResultOut:
    return RunResultOut(
        verdict="failed",
        passed=2,
        total=3,
        tests=[
            TestCaseResultOut(name="t1", passed=True, input="[1, 2, 3], 5", expected="True", actual="True", time_ms=3),
            TestCaseResultOut(name="t2", passed=True, input="[1, 2], 10", expected="False", actual="False", time_ms=2),
            TestCaseResultOut(name="t3", passed=False, input="[], 1", expected="False", actual="None", time_ms=2),
        ],
        stdout="",
        stderr="",
        truncated=False,
        metrics=CodeMetricsOut(
            lines=4, functions=1, loops=1, max_loop_depth=1, recursion=False, uses_builtins_sort=False
        ),
    )


def _stub_review() -> CodeReviewOut:
    return CodeReviewOut(
        summary="Решение верное для большинства случаев, но не обрабатывает пустой список.",
        issues=[CodeIssueOut(line=1, severity="error", text="Пустой список возвращает None вместо False")],
        suggestions=["Добавьте проверку пустого входа в начале функции"],
    )


@router.post("/interviews/{session_id}/runs", status_code=202, response_model=RunCreatedOut)
async def create_run(session_id: uuid.UUID, body: RunIn, user_id: CurrentUserId) -> RunCreatedOut:
    session = store.sessions.get(session_id)
    if session is None or session.user_id != user_id:
        raise ApiError(404, "not_found", "Интервью не найдено")
    existing = next(
        (r for r in store.runs_for_session(session.id) if r.client_run_id == body.client_run_id), None
    )
    if existing is not None:
        return RunCreatedOut(run_id=existing.id, status="queued")
    if session.status != "active":
        raise ApiError(409, "session_not_active", "Интервью уже завершено")
    if session.task is None:
        raise ApiError(409, "no_task", "Задача ещё не выдана")
    if len(store.runs_for_session(session.id)) >= _runs_limit():
        raise ApiError(429, "runs_limit", "Превышен лимит запусков для этой задачи")
    run = StubRun(
        id=uuid.uuid4(),
        session_id=session.id,
        client_run_id=body.client_run_id,
        code_hash=code_hash(body.code),
        created_at=datetime.now(UTC),
    )
    store.runs[run.id] = run
    return RunCreatedOut(run_id=run.id, status="queued")


@router.get("/runs/{run_id}", response_model=RunOut)
async def get_run(run_id: uuid.UUID, user_id: CurrentUserId) -> RunOut:
    run = store.runs.get(run_id)
    session = store.sessions.get(run.session_id) if run else None
    if run is None or session is None or session.user_id != user_id:
        raise ApiError(404, "not_found", "Запуск не найден")
    finished_at = run.created_at + STUB_RUN_DURATION
    if datetime.now(UTC) < finished_at:
        status = "cancelled" if run.cancelled else "running"
        return RunOut(run_id=run.id, status=status, code_hash=run.code_hash, created_at=run.created_at)
    return RunOut(
        run_id=run.id,
        status="done",
        code_hash=run.code_hash,
        created_at=run.created_at,
        finished_at=finished_at,
        result=_stub_result(),
        ai_review=_stub_review(),
    )
