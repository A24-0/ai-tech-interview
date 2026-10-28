# Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
# Proprietary and confidential. See LICENSE in the project root.
"""What the interview API needs from the AI layer (contract, section 7).

decide_next_step and interviewer_turn live in app.infrastructure.ai.interviewer. While that
module is not in the codebase, StandInInterviewer drives the interview by the same step
rules with canned wording and no model.
"""

import asyncio
import importlib
import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from functools import cache
from typing import Literal, Protocol

logger = logging.getLogger(__name__)

NextStep = Literal["clarify", "next_question", "assign_task", "finish"]

QUESTION_LIMITS = {"junior": 3, "middle": 4, "senior": 5}
_AI_LAYER_MODULES = {"app.domain.ai", "app.infrastructure.ai", "app.infrastructure.ai.interviewer"}


@dataclass(frozen=True)
class QuestionRef:
    id: int
    text: str
    expected_answer: str


@dataclass(frozen=True)
class Turn:
    """What the API knows about the session when the interviewer speaks."""

    session_id: str
    topic_title: str
    level: str
    current_question: QuestionRef | None = None
    questions_asked: int = 0
    clarified_current: bool = False
    task_assigned: bool = False
    history: list[tuple[str, str]] = field(default_factory=list)  # (role, content), oldest first
    tokens_used: int = 0


class Interviewer(Protocol):
    async def decide_next_step(self, turn: Turn) -> NextStep: ...

    def reply(self, turn: Turn, step: NextStep, next_question: QuestionRef | None = None) -> AsyncIterator[str]: ...


class AILayerInterviewer:
    """Adapter to the AI layer: its interviewer, its chat provider (LLM_PROVIDER)."""

    def __init__(self) -> None:
        # import_module raises ModuleNotFoundError naming the missing module, which
        # get_interviewer tells apart from a broken installation
        self._ai = importlib.import_module("app.domain.ai")
        self._interviewer = importlib.import_module("app.infrastructure.ai.interviewer")
        self._provider = importlib.import_module("app.infrastructure.ai").get_chat_provider()

    def _question(self, question: QuestionRef | None):  # -> ai.QuestionDTO | None
        if question is None:
            return None
        return self._ai.QuestionDTO(id=question.id, text=question.text, expected_answer=question.expected_answer)

    def _context(self, turn: Turn):  # -> ai.InterviewContext
        return self._ai.InterviewContext(
            session_id=turn.session_id,
            topic_title=turn.topic_title,
            level=turn.level,
            current_question=self._question(turn.current_question),
            questions_asked=turn.questions_asked,
            clarified_current=turn.clarified_current,
            task_assigned=turn.task_assigned,
            history=[self._ai.ChatMessage(role=role, content=content) for role, content in turn.history],
            tokens_used=turn.tokens_used,
        )

    async def decide_next_step(self, turn: Turn) -> NextStep:
        return await self._interviewer.decide_next_step(self._context(turn), self._provider)

    async def reply(
        self, turn: Turn, step: NextStep, next_question: QuestionRef | None = None
    ) -> AsyncIterator[str]:
        stream = self._interviewer.interviewer_turn(
            self._context(turn), step, self._provider, self._question(next_question)
        )
        async for chunk in stream:
            yield chunk


class StandInInterviewer:
    """The AI layer's step rules without a model: questions up to the level's limit,
    then the task, then finish. Streams in chunks of four words like the fake provider."""

    def __init__(self, delay_s: float = 0.05) -> None:
        self.delay_s = delay_s

    async def decide_next_step(self, turn: Turn) -> NextStep:
        if turn.task_assigned:
            return "finish"
        return "assign_task" if turn.questions_asked >= QUESTION_LIMITS[turn.level] else "next_question"

    async def reply(
        self, turn: Turn, step: NextStep, next_question: QuestionRef | None = None
    ) -> AsyncIterator[str]:
        words = self._wording(turn, step, next_question).split(" ")
        for start in range(0, len(words), 4):
            await asyncio.sleep(self.delay_s)
            chunk = " ".join(words[start : start + 4])
            yield chunk + " " if start + 4 < len(words) else chunk

    @staticmethod
    def _wording(turn: Turn, step: NextStep, next_question: QuestionRef | None) -> str:
        if step == "next_question" and next_question is not None:
            lead = "Здравствуйте! Начнём." if turn.questions_asked == 0 else "Спасибо, принято."
            return f"{lead} Вопрос: {next_question.text}"
        if step == "clarify":
            return "Уточните, пожалуйста, ответ и приведите пример."
        if step == "assign_task":
            return "Спасибо за ответы. Перейдём к практике: решите задачу в редакторе и запустите тесты."
        return "Спасибо, на этом интервью завершено."


@cache
def get_interviewer() -> Interviewer:
    """FastAPI dependency: the AI layer when it is installed, otherwise the stand-in."""
    try:
        return AILayerInterviewer()
    except ModuleNotFoundError as exc:
        if exc.name not in _AI_LAYER_MODULES:
            raise
        logger.warning("AI layer is not installed (%s): the interview runs on the stand-in", exc.name)
        return StandInInterviewer()
