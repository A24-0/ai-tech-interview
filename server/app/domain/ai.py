# Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
# Proprietary and confidential. See LICENSE in the project root.
"""AI layer contracts: chat provider protocol, interview context, code review (contract 6.4, 7)."""

from collections.abc import AsyncIterator
from typing import Literal, Protocol, TypeVar

from pydantic import BaseModel, Field

from app.domain.base import CamelModel

T = TypeVar("T", bound=BaseModel)

Level = Literal["junior", "middle", "senior"]
NextStep = Literal["clarify", "next_question", "assign_task", "finish"]
Severity = Literal["error", "warning", "info"]


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class AIUnavailable(Exception):
    """Provider failure after all retries. The API turns it into SSE `error` with code ai_unavailable."""

    def __init__(self, message: str = "Модель временно недоступна", *, retryable: bool = True) -> None:
        super().__init__(message)
        self.retryable = retryable


class ChatProvider(Protocol):
    def stream(
        self,
        messages: list[ChatMessage],
        *,
        session_id: str | None = None,
        purpose: str = "chat",
    ) -> AsyncIterator[str]:
        """Yield text chunks of the model reply. Raises AIUnavailable."""
        ...

    async def complete_json(
        self,
        messages: list[ChatMessage],
        schema: type[T],
        *,
        session_id: str | None = None,
        purpose: str = "json",
    ) -> T:
        """Return the model reply validated against `schema`. Raises AIUnavailable."""
        ...


class CodeIssue(CamelModel):
    line: int
    severity: Severity
    text: str


class CodeReview(CamelModel):
    summary: str
    issues: list[CodeIssue] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)


class AnswerCompleteness(CamelModel):
    """Schema of the short "is the answer complete" check in decide_next_step."""

    complete: bool
    missing: str | None = None


class QuestionDTO(CamelModel):
    """Question from the bank. The API picks it, the model only phrases it."""

    id: int
    text: str
    expected_answer: str


class InterviewContext(CamelModel):
    session_id: str | None = None
    topic_title: str
    level: Level
    current_question: QuestionDTO | None = None
    questions_asked: int = 0
    clarified_current: bool = False
    task_assigned: bool = False
    history: list[ChatMessage] = Field(default_factory=list)
    tokens_used: int = 0
