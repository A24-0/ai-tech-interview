# Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
# Proprietary and confidential. See LICENSE in the project root.
"""The interview API's side of the AI layer: stand-in rules and the dependency choice."""

import importlib

import pytest

from app.api import interview_ai
from app.api.interview_ai import AILayerInterviewer, QuestionRef, StandInInterviewer, Turn, get_interviewer


def _turn(level: str = "junior", asked: int = 1, task: bool = False) -> Turn:
    return Turn(session_id="s", topic_title="Python: основы", level=level, questions_asked=asked, task_assigned=task)


@pytest.mark.parametrize(("level", "limit"), [("junior", 3), ("middle", 4), ("senior", 5)])
async def test_questions_up_to_the_level_limit_then_task(level, limit):
    stand_in = StandInInterviewer(delay_s=0)
    assert await stand_in.decide_next_step(_turn(level, asked=limit - 1)) == "next_question"
    assert await stand_in.decide_next_step(_turn(level, asked=limit)) == "assign_task"
    assert await stand_in.decide_next_step(_turn(level, asked=limit, task=True)) == "finish"


async def test_reply_streams_the_bank_question_in_small_chunks():
    question = QuestionRef(id=7, text="Чем список отличается от кортежа?", expected_answer="...")
    chunks = [c async for c in StandInInterviewer(delay_s=0).reply(_turn(asked=0), "next_question", question)]

    assert len(chunks) > 1
    assert all(len(chunk.split()) <= 4 for chunk in chunks)
    assert "".join(chunks) == "Здравствуйте! Начнём. Вопрос: Чем список отличается от кортежа?"


def _ai_layer_installed() -> bool:
    try:
        importlib.import_module("app.infrastructure.ai.interviewer")
    except ModuleNotFoundError:
        return False
    return True


def test_dependency_uses_the_ai_layer_when_installed():
    get_interviewer.cache_clear()
    expected = AILayerInterviewer if _ai_layer_installed() else StandInInterviewer
    assert isinstance(get_interviewer(), expected)
    get_interviewer.cache_clear()


def test_unrelated_missing_module_is_not_hidden(monkeypatch):
    def broken(self):
        raise ModuleNotFoundError("No module named 'httpx_sse'", name="httpx_sse")

    monkeypatch.setattr(interview_ai.AILayerInterviewer, "__init__", broken)
    get_interviewer.cache_clear()
    with pytest.raises(ModuleNotFoundError):
        get_interviewer()
    get_interviewer.cache_clear()
