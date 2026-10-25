# Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
# Proprietary and confidential. See LICENSE in the project root.

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
        ...

    async def complete_json(
        self,
        messages: list[ChatMessage],
        schema: type[T],
        *,
        session_id: str | None = None,
        purpose: str = "json",
    ) -> T:
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
    complete: bool
    missing: str | None = None


class QuestionDTO(CamelModel):
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
