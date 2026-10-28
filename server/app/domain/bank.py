# Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
# Proprietary and confidential. See LICENSE in the project root.
"""Question and task bank in the import format (FR-16).

{topics: [{code, title}],
 questions: [{topicCode, level, kind, text, expectedAnswer}],
 tasks: [{topicCode, level, title, statement, entry, starterCode, tests, limits, referenceSolution}]}
tests follow contract 6.5. Import keys: topic.code; question topic + text; task topic + title.
"""

from typing import Any, Literal

from pydantic import Field

from app.domain.base import CamelModel

Level = Literal["junior", "middle", "senior"]


class BankTopic(CamelModel):
    code: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=200)


class BankQuestion(CamelModel):
    topic_code: str
    level: Level
    kind: Literal["theory", "practice"] = "theory"
    text: str = Field(min_length=1)
    expected_answer: str = Field(min_length=1)


class BankTask(CamelModel):
    topic_code: str
    level: Level
    title: str = Field(min_length=1, max_length=200)
    statement: str = Field(min_length=1)
    entry: str = Field(min_length=1, max_length=64)
    starter_code: str
    tests: list[dict[str, Any]] = Field(min_length=1)
    limits: dict[str, Any]
    reference_solution: str = Field(min_length=1)


class Bank(CamelModel):
    topics: list[BankTopic] = Field(default_factory=list)
    questions: list[BankQuestion] = Field(default_factory=list)
    tasks: list[BankTask] = Field(default_factory=list)

    def merged(self, other: "Bank") -> "Bank":
        return Bank(
            topics=[*self.topics, *other.topics],
            questions=[*self.questions, *other.questions],
            tasks=[*self.tasks, *other.tasks],
        )


class ImportCounts(CamelModel):
    created: int = 0
    updated: int = 0


class ImportResult(CamelModel):
    topics: ImportCounts = Field(default_factory=ImportCounts)
    questions: ImportCounts = Field(default_factory=ImportCounts)
    tasks: ImportCounts = Field(default_factory=ImportCounts)


class UnknownTopicError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(f"unknown topic code {code!r}")
        self.code = code
