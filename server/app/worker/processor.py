# Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
# Proprietary and confidential. See LICENSE in the project root.
"""Processing of one claimed run: sandbox -> done -> AI review.

The run becomes `done` as soon as the tests have run, so the candidate sees the results
without waiting for the model; aiReview is attached a few seconds later (contract 6.2:
"aiReview: null пока не готов"). A failed or slow review never fails the run.
"""

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any, Protocol

from app.infrastructure.db.run_queue import ClaimedRun, CodeTaskSpec, PgCodeRunQueue
from app.worker.settings import WorkerSettings

logger = logging.getLogger("app.worker")


class Sandbox(Protocol):
    """Structural view of app.domain.sandbox.Sandbox (contract, section 7)."""

    async def run(self, code: str, entry: str, tests: list[dict[str, Any]], limits: dict[str, Any]) -> Any: ...


# review(task, code, run_result) -> CodeReview | None; review_code with the provider bound.
Reviewer = Callable[[CodeTaskSpec, str, Any], Awaitable[Any]]


def to_json(model: Any) -> dict[str, Any]:
    """Pydantic models of the contract (RunResult, CodeReview) as camelCase JSON; dicts as is."""
    if hasattr(model, "model_dump"):
        return model.model_dump(mode="json", by_alias=True)
    return dict(model)


class RunProcessor:
    def __init__(self, queue: PgCodeRunQueue, sandbox: Sandbox, review: Reviewer, settings: WorkerSettings) -> None:
        self._queue = queue
        self._sandbox = sandbox
        self._review = review
        self._settings = settings

    async def process(self, run: ClaimedRun) -> None:
        started = time.monotonic()
        fields: dict[str, Any] = {"run_id": run.id, "session_id": run.session_id, "attempts": run.attempts}

        task = await self._queue.load_task(run.code_task_id)
        # Renewing right before the sandbox keeps "guard < stale_after" true however long the
        # steps above took, so requeue_stale cannot hand a live run to another worker.
        if not await self._queue.renew(run):
            logger.info("run_skipped", extra={"fields": {**fields, "reason": "cancelled"}})
            return

        try:
            result = await asyncio.wait_for(
                self._sandbox.run(run.code, task.entry, task.tests, task.limits),
                timeout=self._settings.sandbox_guard_s,
            )
        except Exception as exc:  # Sandbox.run raises only SandboxError: any failure is ours, not the user's code
            await self._retry_or_fail(run, exc, fields)
            return

        result_json = to_json(result)
        if not await self._queue.mark_done(run, result_json):
            logger.info("run_skipped", extra={"fields": {**fields, "reason": "cancelled during sandbox"}})
            return
        fields |= {"verdict": result_json.get("verdict"), "sandbox_ms": _ms_since(started)}

        review = await self._safe_review(task, run, result, fields)
        if review is not None:
            await self._queue.save_review(run.id, to_json(review))
        logger.info(
            "run_processed", extra={"fields": {**fields, "review": review is not None, "duration_ms": _ms_since(started)}}
        )

    async def _retry_or_fail(self, run: ClaimedRun, exc: Exception, fields: dict[str, Any]) -> None:
        error = f"{type(exc).__name__}: {exc}"[:500]
        if run.attempts < self._settings.max_attempts:
            await self._queue.requeue(run, error)
            logger.warning("run_requeued", extra={"fields": {**fields, "error": error}})
        else:
            await self._queue.mark_failed(run, error)
            logger.error("run_failed", extra={"fields": {**fields, "error": error}})

    async def _safe_review(self, task: CodeTaskSpec, run: ClaimedRun, result: Any, fields: dict[str, Any]) -> Any:
        try:
            return await asyncio.wait_for(self._review(task, run.code, result), timeout=self._settings.review_timeout_s)
        except Exception as exc:
            logger.warning("review_failed", extra={"fields": {**fields, "error": f"{type(exc).__name__}: {exc}"}})
            return None


def _ms_since(started: float) -> int:
    return round((time.monotonic() - started) * 1000)
