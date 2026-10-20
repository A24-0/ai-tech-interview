# Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
# Proprietary and confidential. See LICENSE in the project root.
"""Minimal fake chat provider for stubs and tests (the real AI layer replaces it)."""

import asyncio
from collections.abc import AsyncIterator

DEFAULT_REPLY = (
    "Хорошо, спасибо за ответ. Давайте разберём это подробнее: "
    "расскажите, чем список отличается от кортежа и когда вы выберете каждый из них."
)


class FakeChatProvider:
    """Streams a canned reply in chunks of 3-5 words with a 50 ms delay."""

    def __init__(self, reply: str = DEFAULT_REPLY, delay_s: float = 0.05, fail: bool = False) -> None:
        self._reply = reply
        self._delay_s = delay_s
        self._fail = fail

    async def stream(self, session_id: str | None = None) -> AsyncIterator[str]:
        if self._fail:
            raise RuntimeError("fake provider failure")
        words = self._reply.split(" ")
        size = 4
        for start in range(0, len(words), size):
            chunk = " ".join(words[start : start + size])
            if start + size < len(words):
                chunk += " "
            await asyncio.sleep(self._delay_s)
            yield chunk
