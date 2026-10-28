# Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
# Proprietary and confidential. See LICENSE in the project root.

import os
from functools import cache

from app.domain.ai import ChatProvider
from app.infrastructure.ai.fake import FakeChatProvider
from app.infrastructure.ai.openai_compatible import OpenAICompatibleChatProvider
from app.infrastructure.ai.settings import LLMSettings


@cache
def get_chat_provider() -> ChatProvider:
    backend = os.environ.get("LLM_PROVIDER", "fake").strip().lower()
    if backend == "fake":
        return FakeChatProvider()
    if backend == "openai_compatible":
        settings = LLMSettings.from_env()
        if not settings.base_url or not settings.model:
            raise ValueError("LLM_PROVIDER=openai_compatible needs LLM_BASE_URL and LLM_MODEL")
        return OpenAICompatibleChatProvider(settings)
    raise ValueError(f"Unknown LLM_PROVIDER={backend!r}; expected fake or openai_compatible")
