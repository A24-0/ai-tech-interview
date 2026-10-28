# Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
# Proprietary and confidential. See LICENSE in the project root.
"""Entry point: python -m app.worker. Stops gracefully on SIGTERM / SIGINT."""

import asyncio
import logging
import os
import signal
import socket

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.infrastructure.db.run_queue import PgCodeRunQueue
from app.worker.deps import build_reviewer, build_sandbox
from app.worker.log import configure_logging
from app.worker.loop import Worker
from app.worker.processor import RunProcessor
from app.worker.settings import WorkerSettings

logger = logging.getLogger("app.worker")

# A stuck lock or query must not freeze the worker: the queue statements are short.
_DB_TIMEOUTS = {"lock_timeout": "5s", "statement_timeout": "15s"}


def _stop_on_signals(stop: asyncio.Event) -> None:
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, stop.set)
        except NotImplementedError:  # Windows event loop: no add_signal_handler
            signal.signal(sig, lambda *_: loop.call_soon_threadsafe(stop.set))


async def serve(settings: WorkerSettings) -> None:
    stop = asyncio.Event()
    _stop_on_signals(stop)

    engine = create_async_engine(
        os.environ["DATABASE_URL"], pool_pre_ping=True, connect_args={"server_settings": _DB_TIMEOUTS}
    )
    queue = PgCodeRunQueue(async_sessionmaker(engine, expire_on_commit=False))
    processor = RunProcessor(queue, build_sandbox(), build_reviewer(), settings)
    worker = Worker(queue, processor, settings, worker_id=f"{socket.gethostname()}:{os.getpid()}")
    logger.info("worker_started", extra={"fields": {"worker_id": worker.worker_id, "concurrency": settings.concurrency}})
    try:
        await worker.run(stop)
    finally:
        await engine.dispose()
    logger.info("worker_stopped", extra={"fields": {"worker_id": worker.worker_id}})


def main() -> None:
    configure_logging()
    asyncio.run(serve(WorkerSettings.from_env()))


if __name__ == "__main__":
    main()
