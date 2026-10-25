# Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
# Proprietary and confidential. See LICENSE in the project root.

import asyncio
import json
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.domain.ai import AIUnavailable, ChatMessage
from app.infrastructure.ai.call_log import LLMCall, estimate_tokens, log_call
from app.infrastructure.ai.retry import RetryableError, delay_for, is_retryable_status, with_retries
from app.infrastructure.ai.settings import LLMSettings

T = TypeVar("T", bound=BaseModel)

NETWORK_ERRORS = (RetryableError, httpx.TimeoutException, httpx.TransportError)


def extract_json(text: str) -> str:
    start, end = text.find("{"), text.rfind("}")
    return text[start : end + 1] if start != -1 and end > start else text


def _check_status(response: httpx.Response) -> None:
    if response.status_code == 200:
        return
    if is_retryable_status(response.status_code):
        raise RetryableError(f"LLM returned {response.status_code}")
    raise AIUnavailable(f"LLM returned {response.status_code}", retryable=False)


class OpenAICompatibleChatProvider:
    def __init__(
        self,
        settings: LLMSettings,
        client: httpx.AsyncClient | None = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self.settings = settings
        self._client = client or httpx.AsyncClient(timeout=httpx.Timeout(settings.timeout_s))
        self._sleep = sleep

    @property
    def _url(self) -> str:
        return f"{self.settings.base_url}/chat/completions"

    @property
    def _headers(self) -> dict[str, str]:
        key = self.settings.api_key
        return {"Authorization": f"Bearer {key}"} if key else {}

    def _payload(self, messages: list[ChatMessage], **extra: Any) -> dict[str, Any]:
        return {
            "model": self.settings.model,
            "messages": [m.model_dump() for m in messages],
            **extra,
        }

    async def stream(
        self,
        messages: list[ChatMessage],
        *,
        session_id: str | None = None,
        purpose: str = "chat",
    ) -> AsyncIterator[str]:
        call = LLMCall(purpose=purpose, model=self.settings.model, session_id=session_id)
        started = time.monotonic()
        parts: list[str] = []
        usage: dict[str, Any] | None = None
        payload = self._payload(messages, stream=True, stream_options={"include_usage": True})
        attempt = 0
        try:
            while True:
                try:
                    async with self._client.stream("POST", self._url, json=payload, headers=self._headers) as response:
                        if response.status_code != 200:
                            await response.aread()
                        _check_status(response)
                        async for line in response.aiter_lines():
                            if not line.startswith("data:"):
                                continue
                            data = line[5:].strip()
                            if data == "[DONE]":
                                break
                            chunk = json.loads(data)
                            usage = chunk.get("usage") or usage
                            for choice in chunk.get("choices", []):
                                text = (choice.get("delta") or {}).get("content")
                                if text:
                                    if not parts:
                                        call.first_token_ms = int((time.monotonic() - started) * 1000)
                                    parts.append(text)
                                    yield text
                    return
                except NETWORK_ERRORS as exc:
                    if parts or attempt >= self.settings.max_retries:
                        raise AIUnavailable(f"LLM stream failed: {exc}") from exc
                    await self._sleep(delay_for(attempt))
                    attempt += 1
        except AIUnavailable as exc:
            call.ok = False
            call.error = str(exc)
            raise
        finally:
            self._fill_usage(call, messages, "".join(parts), usage)
            call.duration_ms = int((time.monotonic() - started) * 1000)
            log_call(call)

    async def complete_json(
        self,
        messages: list[ChatMessage],
        schema: type[T],
        *,
        session_id: str | None = None,
        purpose: str = "json",
    ) -> T:
        call = LLMCall(purpose=purpose, model=self.settings.model, session_id=session_id)
        started = time.monotonic()
        history = list(messages)
        json_mode = True
        tokens_in = tokens_out = 0
        try:
            for attempt in range(2):
                try:
                    data = await self._post(history, json_mode)
                except AIUnavailable as exc:
                    if exc.retryable or not (json_mode and attempt == 0):
                        raise
                    json_mode = False
                    data = await self._post(history, json_mode)
                text = data["choices"][0]["message"]["content"] or ""
                usage = data.get("usage") or {}
                tokens_in += usage.get("prompt_tokens") or sum(estimate_tokens(m.content) for m in history)
                tokens_out += usage.get("completion_tokens") or estimate_tokens(text)
                try:
                    return schema.model_validate_json(extract_json(text))
                except ValidationError as exc:
                    history = [
                        *history,
                        ChatMessage(role="assistant", content=text),
                        ChatMessage(
                            role="user",
                            content=f"Ответ не прошёл проверку схемы: {exc.errors(include_url=False)}. Верни только корректный JSON.",
                        ),
                    ]
            raise AIUnavailable("LLM returned invalid JSON twice", retryable=False)
        except AIUnavailable as exc:
            call.ok = False
            call.error = str(exc)
            raise
        finally:
            call.tokens_in, call.tokens_out = tokens_in, tokens_out
            call.duration_ms = int((time.monotonic() - started) * 1000)
            log_call(call)

    async def _post(self, messages: list[ChatMessage], json_mode: bool) -> dict[str, Any]:
        extra: dict[str, Any] = {"response_format": {"type": "json_object"}} if json_mode else {}
        payload = self._payload(messages, **extra)

        async def once() -> dict[str, Any]:
            response = await self._client.post(self._url, json=payload, headers=self._headers)
            _check_status(response)
            result: dict[str, Any] = response.json()
            return result

        try:
            return await with_retries(once, self.settings.max_retries, self._sleep)
        except NETWORK_ERRORS as exc:
            raise AIUnavailable(f"LLM request failed: {exc}") from exc

    @staticmethod
    def _fill_usage(call: LLMCall, messages: list[ChatMessage], text: str, usage: dict[str, Any] | None) -> None:
        if usage:
            call.tokens_in = usage.get("prompt_tokens", 0)
            call.tokens_out = usage.get("completion_tokens", 0)
        else:
            call.tokens_in = sum(estimate_tokens(m.content) for m in messages)
            call.tokens_out = estimate_tokens(text) if text else 0
            call.estimated = True
