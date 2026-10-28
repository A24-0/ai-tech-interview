# Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
# Proprietary and confidential. See LICENSE in the project root.
"""Worker loop: up to `concurrency` runs at once, periodic recovery of stale runs, graceful stop."""

import asyncio
import contextlib
import logging
from datetime import timedelta

from app.infrastructure.db.run_queue import ClaimedRun, PgCodeRunQueue
from app.worker.processor import RunProcessor
from app.worker.settings import WorkerSettings

logger = logging.getLogger("app.worker")


class Worker:
    def __init__(
        self, queue: PgCodeRunQueue, processor: RunProcessor, settings: WorkerSettings, worker_id: str
    ) -> None:
        self._queue = queue
        self._processor = processor
        self._settings = settings
        self.worker_id = worker_id

    async def run(self, stop: asyncio.Event) -> None:
        """Process runs until `stop` is set, then let the runs already taken finish."""
        slots = asyncio.Semaphore(self._settings.concurrency)
        in_flight: set[asyncio.Task[None]] = set()
        stale_watch = asyncio.create_task(self._watch_stale(stop))
        try:
            while not stop.is_set():
                await slots.acquire()
                run = None if stop.is_set() else await self._dequeue()
                if run is None:
                    slots.release()
                    await _sleep_unless(stop, self._settings.poll_interval_s)
                    continue
                task = asyncio.create_task(self._process(run, slots))
                in_flight.add(task)
                task.add_done_callback(in_flight.discard)

            logger.info(
                "worker_stopping", extra={"fields": {"worker_id": self.worker_id, "in_flight": len(in_flight)}}
            )
            await asyncio.gather(*in_flight)
        finally:
            # Reached with tasks still pending only when run() itself is cancelled: take them down too.
            children = [stale_watch, *in_flight]
            for child in children:
                child.cancel()
            await asyncio.gather(*children, return_exceptions=True)

    async def _dequeue(self) -> ClaimedRun | None:
        try:
            return await self._queue.dequeue(self.worker_id)
        except Exception:
            logger.exception("dequeue_failed", extra={"fields": {"worker_id": self.worker_id}})
            return None

    async def _process(self, run: ClaimedRun, slots: asyncio.Semaphore) -> None:
        try:
            await self._processor.process(run)
        except Exception:
            # Before mark_done the run stays `running` and requeue_stale returns it to the queue;
            # after mark_done it stays `done` without aiReview (the contract allows a missing review).
            logger.exception("run_crashed", extra={"fields": {"run_id": run.id, "attempts": run.attempts}})
        finally:
            slots.release()

    async def _watch_stale(self, stop: asyncio.Event) -> None:
        older_than = timedelta(seconds=self._settings.stale_after_s)
        while not stop.is_set():
            try:
                requeued, failed = await self._queue.requeue_stale(older_than, self._settings.max_attempts)
                if requeued or failed:
                    logger.warning("stale_runs", extra={"fields": {"requeued": requeued, "failed": failed}})
            except Exception:
                logger.exception("requeue_stale_failed")
            await _sleep_unless(stop, self._settings.stale_check_interval_s)


async def _sleep_unless(stop: asyncio.Event, seconds: float) -> None:
    with contextlib.suppress(TimeoutError):
        await asyncio.wait_for(stop.wait(), timeout=seconds)
