# Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
# Proprietary and confidential. See LICENSE in the project root.
"""Code run endpoints: queue a solution and poll its result (contract, section 6.2)."""

import os
import uuid
from http import HTTPStatus

import sqlalchemy as sa
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.api.deps import CurrentUserId, DbSession
from app.api.schemas.runs import RunAccepted, RunCreate, RunOut
from app.domain.code_runs import code_hash
from app.infrastructure.db.code_runs import CodeRunModel, interview_sessions

router = APIRouter(prefix="/api", tags=["runs"])

_PROBLEM_RESPONSES = {code: {"content": {"application/problem+json": {}}} for code in (401, 404, 409, 429)}


def _problem(status_code: int, code: str, detail: str) -> JSONResponse:
    return JSONResponse(
        {"type": "about:blank", "title": HTTPStatus(status_code).phrase, "status": status_code, "detail": detail, "code": code},
        status_code=status_code,
        media_type="application/problem+json",
    )


def _runs_per_task_limit() -> int:
    return int(os.environ.get("RUNS_PER_TASK_LIMIT", "20"))


async def _find_run(db: DbSession, session_id: uuid.UUID, client_run_id: uuid.UUID) -> CodeRunModel | None:
    return await db.scalar(
        sa.select(CodeRunModel).where(
            CodeRunModel.session_id == session_id, CodeRunModel.client_run_id == client_run_id
        )
    )


@router.post(
    "/interviews/{session_id}/runs",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=RunAccepted,
    responses=_PROBLEM_RESPONSES,
)
async def create_run(
    session_id: uuid.UUID, body: RunCreate, user_id: CurrentUserId, db: DbSession
) -> RunAccepted | JSONResponse:
    # The row lock serialises submissions within one session, so the idempotency lookup
    # and the limit check below cannot race with a parallel request.
    session = (
        await db.execute(
            sa.select(interview_sessions.c.status, interview_sessions.c.code_task_id)
            .where(interview_sessions.c.id == session_id, interview_sessions.c.user_id == user_id)
            .with_for_update()
        )
    ).one_or_none()
    if session is None:
        return _problem(404, "session_not_found", "Интервью не найдено")

    existing = await _find_run(db, session_id, body.client_run_id)
    if existing is not None:
        return RunAccepted(run_id=existing.id, status=existing.status)

    if session.status != "active":
        return _problem(409, "session_not_active", "Интервью уже завершено")
    if session.code_task_id is None:
        return _problem(409, "no_task", "Задача ещё не выдана")

    runs_for_task = await db.scalar(
        sa.select(sa.func.count()).where(
            CodeRunModel.session_id == session_id, CodeRunModel.code_task_id == session.code_task_id
        )
    )
    limit = _runs_per_task_limit()
    if runs_for_task >= limit:
        return _problem(429, "runs_limit", f"Лимит запусков для этой задачи: {limit}")

    run = CodeRunModel(
        session_id=session_id,
        code_task_id=session.code_task_id,
        client_run_id=body.client_run_id,
        code=body.code,
        code_hash=code_hash(body.code),
    )
    db.add(run)
    await db.commit()
    return RunAccepted(run_id=run.id, status=run.status)


@router.get("/runs/{run_id}", response_model=RunOut, responses=_PROBLEM_RESPONSES)
async def get_run(run_id: uuid.UUID, user_id: CurrentUserId, db: DbSession) -> RunOut | JSONResponse:
    run = await db.scalar(
        sa.select(CodeRunModel)
        .join(interview_sessions, interview_sessions.c.id == CodeRunModel.session_id)
        .where(CodeRunModel.id == run_id, interview_sessions.c.user_id == user_id)
    )
    if run is None:
        return _problem(404, "run_not_found", "Запуск не найден")
    return RunOut(
        run_id=run.id,
        status=run.status,
        code_hash=run.code_hash,
        created_at=run.created_at,
        finished_at=run.finished_at,
        result=run.result if run.status == "done" else None,
        ai_review=run.ai_review,
        error=run.error,
    )
