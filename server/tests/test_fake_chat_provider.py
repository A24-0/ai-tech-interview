# Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
# Proprietary and confidential. See LICENSE in the project root.

import pytest
from pydantic import BaseModel

from app.domain.ai import AIUnavailable, AnswerCompleteness, ChatMessage, CodeReview
from app.infrastructure.ai.fake import FakeChatProvider

MESSAGES = [ChatMessage(role="user", content="Привет")]


async def test_stream_yields_full_text_in_chunks_of_3_to_5_words() -> None:
    text = " ".join(f"w{i}" for i in range(17))
    provider = FakeChatProvider(text, delay_s=0)

    chunks = [chunk async for chunk in provider.stream(MESSAGES, session_id="s1", purpose="interviewer")]

    assert "".join(chunks) == text
    assert len(chunks) > 1
    assert all(3 <= len(chunk.split()) <= 5 for chunk in chunks[:-1])
    assert provider.calls[0].purpose == "interviewer"
    assert provider.calls[0].session_id == "s1"


async def test_complete_json_returns_code_review_with_line_1() -> None:
    review = await FakeChatProvider(delay_s=0).complete_json(MESSAGES, CodeReview)

    assert isinstance(review, CodeReview)
    assert [issue.line for issue in review.issues] == [1]


async def test_complete_json_completeness_defaults_to_complete() -> None:
    result = await FakeChatProvider(delay_s=0).complete_json(MESSAGES, AnswerCompleteness)

    assert result.complete is True


async def test_complete_json_preset_overrides_default() -> None:
    provider = FakeChatProvider(
        delay_s=0, json_responses={"AnswerCompleteness": {"complete": False, "missing": "сложность"}}
    )

    result = await provider.complete_json(MESSAGES, AnswerCompleteness)

    assert result == AnswerCompleteness(complete=False, missing="сложность")


async def test_complete_json_unknown_schema_raises() -> None:
    class Unknown(BaseModel):
        x: int

    with pytest.raises(LookupError):
        await FakeChatProvider(delay_s=0).complete_json(MESSAGES, Unknown)


async def test_fail_flag_raises_ai_unavailable() -> None:
    provider = FakeChatProvider(fail=True, delay_s=0)

    with pytest.raises(AIUnavailable) as exc:
        async for _ in provider.stream(MESSAGES):
            pass
    assert exc.value.retryable is True

    with pytest.raises(AIUnavailable):
        await provider.complete_json(MESSAGES, CodeReview)


def test_code_review_serializes_in_camel_case_contract_shape() -> None:
    review = CodeReview.model_validate(
        {"summary": "ok", "issues": [{"line": 4, "severity": "error", "text": "t"}], "suggestions": ["s"]}
    )

    assert review.model_dump(mode="json") == {
        "summary": "ok",
        "issues": [{"line": 4, "severity": "error", "text": "t"}],
        "suggestions": ["s"],
    }
