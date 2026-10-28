# Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
# Proprietary and confidential. See LICENSE in the project root.

import json
import logging
from collections.abc import Callable

import httpx
import pytest

from app.domain.ai import AIUnavailable, AnswerCompleteness, ChatMessage
from app.infrastructure.ai.openai_compatible import OpenAICompatibleChatProvider, extract_json
from app.infrastructure.ai.settings import LLMSettings

SETTINGS = LLMSettings(base_url="https://llm.example/v1", api_key="k", model="m", timeout_s=1, max_retries=2)
MESSAGES = [ChatMessage(role="user", content="Привет")]


def sse(*chunks: dict[str, object]) -> bytes:
    lines = [f"data: {json.dumps(c, ensure_ascii=False)}\n\n" for c in chunks] + ["data: [DONE]\n\n"]
    return "".join(lines).encode()


def delta(text: str) -> dict[str, object]:
    return {"choices": [{"delta": {"content": text}}]}


def completion(content: str) -> httpx.Response:
    body = {"choices": [{"message": {"content": content}}], "usage": {"prompt_tokens": 7, "completion_tokens": 3}}
    return httpx.Response(200, json=body)


class Sleeps:
    def __init__(self) -> None:
        self.delays: list[float] = []

    async def __call__(self, delay: float) -> None:
        self.delays.append(delay)


def make(handler: Callable[[httpx.Request], httpx.Response], sleeps: Sleeps | None = None) -> OpenAICompatibleChatProvider:
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return OpenAICompatibleChatProvider(SETTINGS, client, sleeps or Sleeps())


async def test_stream_yields_deltas_and_logs_call(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO, logger="app.llm")
    usage: dict[str, object] = {"usage": {"prompt_tokens": 12, "completion_tokens": 4}, "choices": []}

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["stream"] is True
        assert body["stream_options"] == {"include_usage": True}
        assert request.headers["authorization"] == "Bearer k"
        return httpx.Response(200, content=sse(delta("При"), delta("вет"), usage))

    chunks = [c async for c in make(handler).stream(MESSAGES, session_id="s1", purpose="interviewer")]

    assert chunks == ["При", "вет"]
    logged = caplog.records[-1].llm_call  # type: ignore[attr-defined]
    assert logged["session_id"] == "s1"
    assert logged["purpose"] == "interviewer"
    assert logged["tokens_in"] == 12
    assert logged["tokens_out"] == 4
    assert logged["estimated"] is False
    assert logged["first_token_ms"] is not None
    assert "Привет" not in json.dumps(logged, ensure_ascii=False)


async def test_stream_estimates_tokens_without_usage(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO, logger="app.llm")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=sse(delta("a" * 40)))

    _ = [c async for c in make(handler).stream(MESSAGES)]

    logged = caplog.records[-1].llm_call  # type: ignore[attr-defined]
    assert logged["estimated"] is True
    assert logged["tokens_out"] == 10


async def test_429_then_success_retries_with_backoff() -> None:
    answers = [httpx.Response(429), httpx.Response(200, content=sse(delta("ok")))]
    sleeps = Sleeps()

    chunks = [c async for c in make(lambda request: answers.pop(0), sleeps).stream(MESSAGES)]

    assert chunks == ["ok"]
    assert len(sleeps.delays) == 1
    assert 0.3 < sleeps.delays[0] < 0.7


async def test_stream_gives_up_after_max_retries() -> None:
    sleeps = Sleeps()

    with pytest.raises(AIUnavailable) as caught:
        _ = [c async for c in make(lambda request: httpx.Response(503), sleeps).stream(MESSAGES)]

    assert caught.value.retryable is True
    assert len(sleeps.delays) == SETTINGS.max_retries


async def test_timeout_becomes_ai_unavailable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    with pytest.raises(AIUnavailable):
        _ = [c async for c in make(handler).stream(MESSAGES)]


async def test_client_error_is_not_retried() -> None:
    sleeps = Sleeps()

    with pytest.raises(AIUnavailable) as caught:
        _ = [c async for c in make(lambda request: httpx.Response(401), sleeps).stream(MESSAGES)]

    assert caught.value.retryable is False
    assert sleeps.delays == []


async def test_complete_json_parses_schema() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert json.loads(request.content)["response_format"] == {"type": "json_object"}
        return completion('{"complete": false, "missing": "про GIL"}')

    result = await make(handler).complete_json(MESSAGES, AnswerCompleteness)

    assert result == AnswerCompleteness(complete=False, missing="про GIL")


async def test_invalid_json_is_retried_once_with_validation_error() -> None:
    bodies: list[dict[str, object]] = []
    answers = [completion("не json"), completion('{"complete": true}')]

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        return answers.pop(0)

    result = await make(handler).complete_json(MESSAGES, AnswerCompleteness)

    assert result.complete is True
    assert len(bodies) == 2
    assert "проверку схемы" in bodies[1]["messages"][-1]["content"]  # type: ignore[index]


async def test_two_invalid_answers_raise_ai_unavailable() -> None:
    with pytest.raises(AIUnavailable):
        await make(lambda request: completion("снова не json")).complete_json(MESSAGES, AnswerCompleteness)


async def test_json_mode_rejected_falls_back_to_plain_request() -> None:
    formats: list[bool] = []

    def handler(request: httpx.Request) -> httpx.Response:
        has_format = "response_format" in json.loads(request.content)
        formats.append(has_format)
        return httpx.Response(400) if has_format else completion('Вот ответ: {"complete": true}')

    result = await make(handler).complete_json(MESSAGES, AnswerCompleteness)

    assert result.complete is True
    assert formats == [True, False]


def test_extract_json_cuts_text_around_object() -> None:
    assert extract_json('Ответ: {"a": 1} спасибо') == '{"a": 1}'
    assert extract_json("без объекта") == "без объекта"
