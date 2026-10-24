# Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
# Proprietary and confidential. See LICENSE in the project root.
"""Chat provider factory. Call sites use get_chat_provider(), never a concrete provider."""

import os
from functools import cache

from app.domain.ai import ChatProvider
from app.infrastructure.ai.fake import FakeChatProvider


@cache
def get_chat_provider() -> ChatProvider:
    """LLM_PROVIDER=fake|openai_compatible (default: fake). Cached singleton."""
    backend = os.environ.get("LLM_PROVIDER", "fake").strip().lower()
    if backend == "fake":
        return FakeChatProvider()
    if backend == "openai_compatible":
        raise NotImplementedError(
            "LLM_PROVIDER=openai_compatible is not implemented yet; use LLM_PROVIDER=fake for now"
        )
    raise ValueError(f"Unknown LLM_PROVIDER={backend!r}; expected fake or openai_compatible")
