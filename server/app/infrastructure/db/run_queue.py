# Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
# Proprietary and confidential. See LICENSE in the project root.
"""Queue of code runs in PostgreSQL.

Workers claim runs with SELECT ... FOR UPDATE SKIP LOCKED, so parallel workers never get
the same run. Every later transition is fenced by the claim (status, locked_by, attempts):
a run that was cancelled or handed to another worker in the meantime is left alone.
"""

import uuid
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.infrastructure.db.code_runs import CodeRunModel, code_tasks


@dataclass(frozen=True, slots=True)
class ClaimedRun:
    id: uuid.UUID
    session_id: uuid.UUID
    code_task_id: int
    code: str
    attempts: int
    worker_id: str


@dataclass(frozen=True, slots=True)
class CodeTaskSpec:
    id: int
    title: str
    statement: str
    entry: str
    tests: list[dict[str, Any]]
    limits: dict[str, Any]


class PgCodeRunQueue:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def _execute(self, statement: sa.Executable) -> sa.CursorResult[Any]:
        async with self._session_factory() as db, db.begin():
            return await db.execute(statement, execution_options={"synchronize_session": False})

    async def dequeue(self, worker_id: str) -> ClaimedRun | None:
        """Claim the oldest queued run in one statement, or return None if the queue is empty."""
        oldest_queued = (
            sa.select(CodeRunModel.id)
            .where(CodeRunModel.status == "queued")
            .order_by(CodeRunModel.created_at, CodeRunModel.id)
            .limit(1)
            .with_for_update(skip_locked=True)
            .scalar_subquery()
        )
        claim = (
            sa.update(CodeRunModel)
            .where(CodeRunModel.id == oldest_queued)
            .values(
                status="running",
                started_at=sa.func.now(),
                attempts=CodeRunModel.attempts + 1,
                locked_by=worker_id,
            )
            .returning(
                CodeRunModel.id,
                CodeRunModel.session_id,
                CodeRunModel.code_task_id,
                CodeRunModel.code,
                CodeRunModel.attempts,
            )
        )
        row = (await self._execute(claim)).one_or_none()
        return None if row is None else ClaimedRun(*row, worker_id=worker_id)

    async def load_task(self, code_task_id: int) -> CodeTaskSpec:
        async with self._session_factory() as db:
            row = (await db.execute(sa.select(code_tasks).where(code_tasks.c.id == code_task_id))).one()
        return CodeTaskSpec(**row._mapping)

    async def renew(self, run: ClaimedRun) -> bool:
        """Restart the stale-run clock before slow work; False if the run was cancelled or reclaimed."""
        return await self._transition(run, started_at=sa.func.now())

    async def mark_done(self, run: ClaimedRun, result: dict[str, Any]) -> bool:
        return await self._transition(run, status="done", result=result, error=None, finished_at=sa.func.now())

    async def mark_failed(self, run: ClaimedRun, error: str) -> bool:
        return await self._transition(run, status="failed", error=error, finished_at=sa.func.now())

    async def requeue(self, run: ClaimedRun, error: str) -> bool:
        """Give the run back to the queue after a system failure; `error` keeps the last cause."""
        return await self._transition(run, status="queued", error=error, locked_by=None, started_at=None)

    async def save_review(self, run_id: uuid.UUID, review: dict[str, Any]) -> None:
        await self._execute(
            sa.update(CodeRunModel)
            .where(CodeRunModel.id == run_id, CodeRunModel.status == "done")
            .values(ai_review=review)
        )

    async def requeue_stale(self, older_than: timedelta, max_attempts: int) -> tuple[int, int]:
        """Return runs stuck in `running` (worker died) to the queue; fail those out of attempts.

        Returns (requeued, failed).
        """
        stale = (CodeRunModel.status == "running", CodeRunModel.started_at < sa.func.now() - older_than)
        requeued = await self._execute(
            sa.update(CodeRunModel)
            .where(*stale, CodeRunModel.attempts < max_attempts)
            .values(status="queued", locked_by=None, started_at=None, error="stale")
        )
        failed = await self._execute(
            sa.update(CodeRunModel)
            .where(*stale, CodeRunModel.attempts >= max_attempts)
            .values(status="failed", error="stale", finished_at=sa.func.now())
        )
        return requeued.rowcount, failed.rowcount

    async def _transition(self, run: ClaimedRun, **values: Any) -> bool:
        updated = await self._execute(sa.update(CodeRunModel).where(_claimed_by(run)).values(**values))
        return updated.rowcount == 1


def _claimed_by(run: ClaimedRun) -> sa.ColumnElement[bool]:
    return sa.and_(
        CodeRunModel.id == run.id,
        CodeRunModel.status == "running",
        CodeRunModel.locked_by == run.worker_id,
        CodeRunModel.attempts == run.attempts,
    )


async def cancel_runs_for_session(db: AsyncSession, session_id: uuid.UUID) -> int:
    """Cancel queued and running runs of a finished interview. Runs in the caller's transaction.

    Called from POST /api/interviews/{id}/finish; returns how many runs were cancelled.
    """
    cancelled = await db.execute(
        sa.update(CodeRunModel)
        .where(CodeRunModel.session_id == session_id, CodeRunModel.status.in_(("queued", "running")))
        .values(status="cancelled", finished_at=sa.func.now())
    )
    return cancelled.rowcount
