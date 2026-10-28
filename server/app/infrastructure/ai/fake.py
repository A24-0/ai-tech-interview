# Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
# Proprietary and confidential. See LICENSE in the project root.
"""FakeChatProvider: deterministic ChatProvider for development and tests (LLM_PROVIDER=fake)."""

import asyncio
import itertools
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any, TypeVar

from pydantic import BaseModel

from app.domain.ai import AIUnavailable, ChatMessage

T = TypeVar("T", bound=BaseModel)

DEFAULT_TEXT = (
    "Здравствуйте! Давайте начнём с теории. "
    "Расскажите, чем список в Python отличается от кортежа и когда вы выберете каждый из них?"
)

DEFAULT_JSON: dict[str, dict[str, Any]] = {
    "CodeReview": {
        "summary": "Решение проходит часть тестов, стоит проверить граничные случаи.",
        "issues": [{"line": 1, "severity": "warning", "text": "Проверьте обработку пустого входа."}],
        "suggestions": ["Добавьте проверку пустого входа в начале функции."],
    },
    "AnswerCompleteness": {"complete": True, "missing": None},
}

_CHUNK_SIZES = (3, 4, 5)


@dataclass(frozen=True)
class FakeCall:
    method: str
    purpose: str
    session_id: str | None
    messages: list[ChatMessage]


class FakeChatProvider:
    """`stream` yields `text` in chunks of 3–5 words; `complete_json` returns a preset dict by schema name."""

    def __init__(
        self,
        text: str = DEFAULT_TEXT,
        *,
        json_responses: dict[str, dict[str, Any]] | None = None,
        fail: bool = False,
        delay_s: float = 0.05,
    ) -> None:
        self.text = text
        self.json_responses = {**DEFAULT_JSON, **(json_responses or {})}
        self.fail = fail
        self.delay_s = delay_s
        self.calls: list[FakeCall] = []

    async def stream(
        self,
        messages: list[ChatMessage],
        *,
        session_id: str | None = None,
        purpose: str = "chat",
    ) -> AsyncIterator[str]:
        self.calls.append(FakeCall("stream", purpose, session_id, list(messages)))
        if self.fail:
            raise AIUnavailable()
        words = self.text.split(" ")
        start = 0
        for size in itertools.cycle(_CHUNK_SIZES):
            if start >= len(words):
                break
            end = start + size
            chunk = " ".join(words[start:end])
            yield chunk + " " if end < len(words) else chunk
            start = end
            await asyncio.sleep(self.delay_s)

    async def complete_json(
        self,
        messages: list[ChatMessage],
        schema: type[T],
        *,
        session_id: str | None = None,
        purpose: str = "json",
    ) -> T:
        self.calls.append(FakeCall("complete_json", purpose, session_id, list(messages)))
        if self.fail:
            raise AIUnavailable()
        try:
            data = self.json_responses[schema.__name__]
        except KeyError:
            raise LookupError(
                f"FakeChatProvider has no preset response for schema {schema.__name__}; "
                "pass it via json_responses"
            ) from None
        return schema.model_validate(data)
