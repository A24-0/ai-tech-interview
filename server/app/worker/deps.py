# Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
# Proprietary and confidential. See LICENSE in the project root.
"""Sandbox and reviewer for the worker, taken from the factories of the contract (section 7).

Until those modules are merged, SANDBOX_BACKEND=fake / LLM_PROVIDER=fake fall back to the
stand-ins in app.worker.interim. Any other setting fails loudly instead of faking results.
"""

import logging
import os
from typing import Any

from app.infrastructure.db.run_queue import CodeTaskSpec
from app.worker.processor import Reviewer, Sandbox

logger = logging.getLogger("app.worker")


def build_sandbox() -> Sandbox:
    try:
        from app.infrastructure.sandbox import get_sandbox
    except ModuleNotFoundError as exc:
        if exc.name != "app.infrastructure.sandbox" or os.environ.get("SANDBOX_BACKEND") != "fake":
            raise
        from app.worker.interim import InterimFakeSandbox

        logger.warning("interim_sandbox", extra={"fields": {"reason": "app.infrastructure.sandbox is not merged yet"}})
        return InterimFakeSandbox()
    return get_sandbox()


def build_reviewer() -> Reviewer:
    try:
        from app.infrastructure.ai import get_chat_provider
        from app.infrastructure.ai.reviewer import review_code
    except ModuleNotFoundError as exc:
        merged = exc.name not in ("app.infrastructure.ai", "app.infrastructure.ai.reviewer")
        if merged or os.environ.get("LLM_PROVIDER") != "fake":
            raise
        from app.worker.interim import interim_review

        logger.warning("interim_reviewer", extra={"fields": {"reason": "app.infrastructure.ai is not merged yet"}})
        return interim_review

    provider = get_chat_provider()

    async def review(task: CodeTaskSpec, code: str, result: Any) -> Any:
        return await review_code(task, code, result, provider)

    return review
