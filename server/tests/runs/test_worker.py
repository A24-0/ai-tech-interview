# Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
# Proprietary and confidential. See LICENSE in the project root.
"""Worker: a run goes queued -> running -> done with result and review; failures and stop."""

import asyncio
import uuid
from typing import Any

import pytest
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.infrastructure.db.code_runs import CodeRunModel
from app.infrastructure.db.run_queue import (
    CodeTaskSpec,
    PgCodeRunQueue,
    cancel_runs_for_session,
)
from app.worker.loop import Worker
from app.worker.processor import RunProcessor
from app.worker.settings import WorkerSettings
from tests.runs.conftest import DEFAULT_TESTS, create_run, create_session, create_task

pytestmark = pytest.mark.db

Factory = async_sessionmaker[AsyncSession]
SETTINGS = WorkerSettings(poll_interval_s=0.05, stale_check_interval_s=0.2, review_timeout_s=2)


class _Camel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class FakeRunResult(_Camel):
    verdict: str = "failed"
    passed: int = 2
    total: int = 3
    tests: list[dict[str, Any]] = []
    stdout: str = ""
    stderr: str = ""
    truncated: bool = False
    metrics: dict[str, Any] = {"maxLoopDepth": 1}


class FakeReview(_Camel):
    summary: str = "Не обработан пустой список"
    issues: list[dict[str, Any]] = [{"line": 1, "severity": "warning", "text": "Нет проверки"}]
    suggestions: list[str] = []


class RecordingSandbox:
    def __init__(self, delay: float = 0.0, fail: bool = False) -> None:
        self.calls: list[tuple[str, str, list, dict]] = []
        self.delay = delay
        self.fail = fail
        self.on_run = None

    async def run(self, code: str, entry: str, tests: list[dict[str, Any]], limits: dict[str, Any]) -> FakeRunResult:
        self.calls.append((code, entry, tests, limits))
        if self.on_run is not None:
            await self.on_run()
        await asyncio.sleep(self.delay)
        if self.fail:
            raise RuntimeError("docker is unavailable")
        return FakeRunResult()


async def ok_review(task: CodeTaskSpec, code: str, result: Any) -> FakeReview:
    assert task.statement and code and result.verdict == "failed"
    return FakeReview()


async def broken_review(task: CodeTaskSpec, code: str, result: Any) -> FakeReview:
    raise RuntimeError("model is down")


async def _setup(factory: Factory, runs: int = 1) -> tuple[uuid.UUID, list[uuid.UUID]]:
    task_id = await create_task(factory)
    session_id = await create_session(factory, uuid.uuid4(), code_task_id=task_id)
    return session_id, [await create_run(factory, session_id, task_id, code="def solve(nums, k):\n    pass") for _ in range(runs)]


async def _get(factory: Factory, run_id: uuid.UUID) -> CodeRunModel:
    async with factory() as db:
        return await db.get(CodeRunModel, run_id)


async def _process_next(factory: Factory, sandbox: RecordingSandbox, review=ok_review) -> None:
    queue = PgCodeRunQueue(factory)
    run = await queue.dequeue("w1")
    assert run is not None
    await RunProcessor(queue, sandbox, review, SETTINGS).process(run)


async def test_run_reaches_done_with_result_and_review(session_factory: Factory) -> None:
    _, (run_id,) = await _setup(session_factory)
    sandbox = RecordingSandbox()

    await _process_next(session_factory, sandbox)

    run = await _get(session_factory, run_id)
    assert run.status == "done"
    assert run.result["verdict"] == "failed"
    assert run.result["metrics"] == {"maxLoopDepth": 1}  # camelCase as the contract requires
    assert run.ai_review["issues"][0]["line"] == 1
    assert run.finished_at is not None and run.error is None
    _code, entry, tests, limits = sandbox.calls[0]
    assert (entry, tests, limits["perTestTimeoutMs"]) == ("solve", DEFAULT_TESTS, 2000)


async def test_failed_review_keeps_run_done(session_factory: Factory) -> None:
    _, (run_id,) = await _setup(session_factory)

    await _process_next(session_factory, RecordingSandbox(), review=broken_review)

    run = await _get(session_factory, run_id)
    assert run.status == "done"
    assert run.result is not None
    assert run.ai_review is None


async def test_slow_review_does_not_block_the_run(session_factory: Factory) -> None:
    _, (run_id,) = await _setup(session_factory)

    async def hanging_review(task: CodeTaskSpec, code: str, result: Any) -> FakeReview:
        await asyncio.sleep(10)
        return FakeReview()

    settings = WorkerSettings(review_timeout_s=0.2)
    queue = PgCodeRunQueue(session_factory)
    await RunProcessor(queue, RecordingSandbox(), hanging_review, settings).process(await queue.dequeue("w1"))

    run = await _get(session_factory, run_id)
    assert (run.status, run.ai_review) == ("done", None)


async def test_sandbox_failure_is_retried_then_failed(session_factory: Factory) -> None:
    _, (run_id,) = await _setup(session_factory)
    sandbox = RecordingSandbox(fail=True)

    await _process_next(session_factory, sandbox)
    after_first = await _get(session_factory, run_id)
    await _process_next(session_factory, sandbox)
    await _process_next(session_factory, sandbox)

    assert (after_first.status, after_first.attempts) == ("queued", 1)
    assert "docker is unavailable" in after_first.error
    run = await _get(session_factory, run_id)
    assert (run.status, run.attempts) == ("failed", 3)
    assert run.finished_at is not None
    assert len(sandbox.calls) == 3


async def test_run_cancelled_during_sandbox_stays_cancelled(session_factory: Factory) -> None:
    session_id, (run_id,) = await _setup(session_factory)
    sandbox = RecordingSandbox()

    async def finish_interview() -> None:
        async with session_factory() as db, db.begin():
            await cancel_runs_for_session(db, session_id)

    sandbox.on_run = finish_interview
    await _process_next(session_factory, sandbox)

    run = await _get(session_factory, run_id)
    assert (run.status, run.result, run.ai_review) == ("cancelled", None, None)


async def test_worker_processes_queue_and_stops_gracefully(session_factory: Factory) -> None:
    _, run_ids = await _setup(session_factory, runs=5)
    queue = PgCodeRunQueue(session_factory)
    sandbox = RecordingSandbox(delay=0.3)
    worker = Worker(queue, RunProcessor(queue, sandbox, ok_review, SETTINGS), SETTINGS, worker_id="w1")
    stop = asyncio.Event()

    serving = asyncio.create_task(worker.run(stop))
    while len(sandbox.calls) < 1:  # first run is inside the sandbox
        await asyncio.sleep(0.02)
    stop.set()
    await asyncio.wait_for(serving, timeout=5)

    statuses = [(await _get(session_factory, run_id)).status for run_id in run_ids]
    taken = len(sandbox.calls)
    assert 1 <= taken <= SETTINGS.concurrency  # no new runs after stop
    assert statuses[:taken] == ["done"] * taken  # runs already taken were finished, not abandoned
    assert statuses[taken:] == ["queued"] * (5 - taken)


async def test_worker_drains_the_queue_with_limited_concurrency(session_factory: Factory) -> None:
    _, run_ids = await _setup(session_factory, runs=6)
    queue = PgCodeRunQueue(session_factory)
    active = peak = 0

    class CountingSandbox(RecordingSandbox):
        async def run(self, *args: Any) -> FakeRunResult:
            nonlocal active, peak
            active += 1
            peak = max(peak, active)
            try:
                return await super().run(*args)
            finally:
                active -= 1

    sandbox = CountingSandbox(delay=0.1)
    worker = Worker(queue, RunProcessor(queue, sandbox, ok_review, SETTINGS), SETTINGS, worker_id="w1")
    stop = asyncio.Event()
    serving = asyncio.create_task(worker.run(stop))
    for _ in range(100):
        if all([(await _get(session_factory, run_id)).status == "done" for run_id in run_ids]):
            break
        await asyncio.sleep(0.05)
    stop.set()
    await asyncio.wait_for(serving, timeout=5)

    assert all([(await _get(session_factory, run_id)).status == "done" for run_id in run_ids])
    assert peak == SETTINGS.concurrency


async def test_cancelling_worker_cancels_its_tasks(session_factory: Factory) -> None:
    await _setup(session_factory)
    queue = PgCodeRunQueue(session_factory)
    sandbox_cancelled = asyncio.Event()

    class HangingSandbox(RecordingSandbox):
        async def run(self, *args: Any) -> FakeRunResult:
            self.calls.append(args)
            try:
                await asyncio.sleep(60)
            except asyncio.CancelledError:
                sandbox_cancelled.set()
                raise
            return FakeRunResult()

    sandbox = HangingSandbox()
    worker = Worker(queue, RunProcessor(queue, sandbox, ok_review, SETTINGS), SETTINGS, worker_id="w1")
    serving = asyncio.create_task(worker.run(asyncio.Event()))
    while not sandbox.calls:
        await asyncio.sleep(0.02)

    serving.cancel()
    with pytest.raises(asyncio.CancelledError):
        await asyncio.wait_for(serving, timeout=5)

    assert sandbox_cancelled.is_set()
    leftovers = [t for t in asyncio.all_tasks() if t is not asyncio.current_task() and not t.done()]
    assert leftovers == []


def test_settings_reject_stale_threshold_below_sandbox_guard() -> None:
    with pytest.raises(ValueError):
        WorkerSettings(stale_after_s=30, sandbox_guard_s=30)
    settings = WorkerSettings.from_env({"WORKER_CONCURRENCY": "4", "WORKER_POLL_MS": "250", "SANDBOX_TIMEOUT_S": "5"})
    assert (settings.concurrency, settings.poll_interval_s, settings.sandbox_guard_s) == (4, 0.25, 30)
