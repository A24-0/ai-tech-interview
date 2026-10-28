# Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
# Proprietary and confidential. See LICENSE in the project root.
"""PgCodeRunQueue: claiming with SKIP LOCKED, fenced transitions, stale recovery, cancellation."""

import asyncio
import uuid
from datetime import timedelta

import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.infrastructure.db.code_runs import CodeRunModel
from app.infrastructure.db.run_queue import PgCodeRunQueue, cancel_runs_for_session
from tests.runs.conftest import create_run, create_session, create_task

pytestmark = pytest.mark.db

Factory = async_sessionmaker[AsyncSession]


async def _session_with_runs(factory: Factory, count: int) -> tuple[uuid.UUID, int, list[uuid.UUID]]:
    task_id = await create_task(factory)
    session_id = await create_session(factory, uuid.uuid4(), code_task_id=task_id)
    run_ids = [await create_run(factory, session_id, task_id, code=f"x = {i}") for i in range(count)]
    return session_id, task_id, run_ids


async def _get(factory: Factory, run_id: uuid.UUID) -> CodeRunModel:
    async with factory() as db:
        return await db.get(CodeRunModel, run_id)


async def test_parallel_workers_never_claim_the_same_run(session_factory: Factory) -> None:
    _, _, run_ids = await _session_with_runs(session_factory, 30)
    queue = PgCodeRunQueue(session_factory)

    async def drain(worker_id: str) -> list[uuid.UUID]:
        claimed = []
        while (run := await queue.dequeue(worker_id)) is not None:
            claimed.append(run.id)
        return claimed

    batches = await asyncio.gather(*(drain(f"w{i}") for i in range(8)))
    claimed = [run_id for batch in batches for run_id in batch]

    assert len(claimed) == len(set(claimed)) == 30
    assert set(claimed) == set(run_ids)


async def test_dequeue_takes_oldest_and_marks_running(session_factory: Factory) -> None:
    session_id, task_id, run_ids = await _session_with_runs(session_factory, 2)
    queue = PgCodeRunQueue(session_factory)

    run = await queue.dequeue("w1")

    assert run is not None
    assert (run.id, run.session_id, run.code_task_id, run.attempts) == (run_ids[0], session_id, task_id, 1)
    stored = await _get(session_factory, run.id)
    assert (stored.status, stored.locked_by, stored.attempts) == ("running", "w1", 1)
    assert stored.started_at is not None


async def test_empty_queue_returns_none(session_factory: Factory) -> None:
    assert await PgCodeRunQueue(session_factory).dequeue("w1") is None


async def test_done_does_not_overwrite_cancelled_run(session_factory: Factory) -> None:
    session_id, _, _ = await _session_with_runs(session_factory, 1)
    queue = PgCodeRunQueue(session_factory)
    run = await queue.dequeue("w1")

    async with session_factory() as db, db.begin():
        assert await cancel_runs_for_session(db, session_id) == 1
    marked = await queue.mark_done(run, {"verdict": "passed"})

    assert marked is False
    stored = await _get(session_factory, run.id)
    assert stored.status == "cancelled"
    assert stored.result is None


async def test_stale_claim_cannot_finish_a_reclaimed_run(session_factory: Factory) -> None:
    await _session_with_runs(session_factory, 1)
    queue = PgCodeRunQueue(session_factory)
    first = await queue.dequeue("w1")
    await queue.requeue(first, "boom")
    second = await queue.dequeue("w1")  # same worker, next attempt

    assert await queue.mark_done(first, {"verdict": "passed"}) is False
    assert await queue.mark_done(second, {"verdict": "failed"}) is True
    assert (await _get(session_factory, second.id)).result == {"verdict": "failed"}


async def test_renew_keeps_live_run_away_from_stale_sweep(session_factory: Factory) -> None:
    await _session_with_runs(session_factory, 1)
    queue = PgCodeRunQueue(session_factory)
    run = await queue.dequeue("w1")
    async with session_factory() as db, db.begin():
        await db.execute(
            sa.update(CodeRunModel)
            .where(CodeRunModel.id == run.id)
            .values(started_at=sa.func.now() - timedelta(seconds=59))
        )

    assert await queue.renew(run) is True
    assert await queue.requeue_stale(timedelta(seconds=10), max_attempts=3) == (0, 0)
    assert (await _get(session_factory, run.id)).status == "running"


async def test_renew_fails_for_cancelled_or_reclaimed_run(session_factory: Factory) -> None:
    session_id, _, _ = await _session_with_runs(session_factory, 2)
    queue = PgCodeRunQueue(session_factory)
    first, second = await queue.dequeue("w1"), await queue.dequeue("w1")
    await queue.requeue(first, "boom")
    reclaimed = await queue.dequeue("w2")
    async with session_factory() as db, db.begin():
        await cancel_runs_for_session(db, session_id)

    assert reclaimed.id == first.id
    assert await queue.renew(first) is False  # handed to w2
    assert await queue.renew(second) is False  # cancelled


async def test_cancel_runs_for_session_touches_only_unfinished_runs(session_factory: Factory) -> None:
    session_id, task_id, run_ids = await _session_with_runs(session_factory, 3)
    other_session = await create_session(session_factory, uuid.uuid4(), code_task_id=task_id)
    other_run = await create_run(session_factory, other_session, task_id)
    queue = PgCodeRunQueue(session_factory)
    done = await queue.dequeue("w1")
    await queue.mark_done(done, {"verdict": "passed"})
    await queue.dequeue("w1")  # second run is running, third stays queued

    async with session_factory() as db, db.begin():
        cancelled = await cancel_runs_for_session(db, session_id)

    assert cancelled == 2
    statuses = [(await _get(session_factory, run_id)).status for run_id in run_ids]
    assert statuses == ["done", "cancelled", "cancelled"]
    assert (await _get(session_factory, run_ids[2])).finished_at is not None
    assert (await _get(session_factory, other_run)).status == "queued"


async def test_requeue_stale_returns_old_running_runs_and_fails_exhausted(session_factory: Factory) -> None:
    _, _, run_ids = await _session_with_runs(session_factory, 3)
    queue = PgCodeRunQueue(session_factory)
    stale, exhausted, fresh = [await queue.dequeue("w1") for _ in run_ids]
    async with session_factory() as db, db.begin():
        await db.execute(
            sa.update(CodeRunModel)
            .where(CodeRunModel.id.in_([stale.id, exhausted.id]))
            .values(started_at=sa.func.now() - timedelta(seconds=61))
        )
        await db.execute(sa.update(CodeRunModel).where(CodeRunModel.id == exhausted.id).values(attempts=3))

    requeued, failed = await queue.requeue_stale(timedelta(seconds=60), max_attempts=3)

    assert (requeued, failed) == (1, 1)
    back = await _get(session_factory, stale.id)
    assert (back.status, back.locked_by, back.started_at, back.error) == ("queued", None, None, "stale")
    gone = await _get(session_factory, exhausted.id)
    assert (gone.status, gone.error) == ("failed", "stale")
    assert (await _get(session_factory, fresh.id)).status == "running"
    assert (await queue.dequeue("w2")).id == stale.id
