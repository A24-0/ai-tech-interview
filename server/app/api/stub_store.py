# Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
# Proprietary and confidential. See LICENSE in the project root.
"""In-memory storage for the API stubs. Replaced by the database layer."""

import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.api.schemas.interviews import Level, MessageOut, TaskOut

STUB_TASK = TaskOut(
    id=7,
    title="Сумма пар",
    statement=(
        "Дан список целых чисел `nums` и число `k`. Верните `True`, если в списке есть "
        "два разных элемента с суммой `k`, иначе `False`.\n\n"
        "Пример: `solve([1, 2, 3], 5)` → `True`."
    ),
    starter_code="def solve(nums, k):\n    pass\n",
)

FIRST_QUESTION = "Здравствуйте! Первый вопрос: чем список в Python отличается от кортежа?"


@dataclass
class StubReply:
    user_message_id: int
    reply_message_id: int
    text: str


@dataclass
class StubSession:
    id: uuid.UUID
    user_id: uuid.UUID
    topic_id: int
    level: Level
    status: str = "active"
    messages: list[MessageOut] = field(default_factory=list)
    task: TaskOut | None = None
    replies: dict[uuid.UUID, StubReply] = field(default_factory=dict)
    next_message_id: int = 1

    def add_message(self, role: str, content: str) -> MessageOut:
        message = MessageOut(
            id=self.next_message_id,
            role=role,  # type: ignore[arg-type]
            content=content,
            created_at=datetime.now(UTC),
        )
        self.next_message_id += 1
        self.messages.append(message)
        return message

    def user_messages_count(self) -> int:
        return sum(1 for m in self.messages if m.role == "user")


@dataclass
class StubRun:
    id: uuid.UUID
    session_id: uuid.UUID
    client_run_id: uuid.UUID
    code_hash: str
    created_at: datetime
    cancelled: bool = False


class StubStore:
    def __init__(self) -> None:
        self.sessions: dict[uuid.UUID, StubSession] = {}
        self.runs: dict[uuid.UUID, StubRun] = {}

    def active_for_user(self, user_id: uuid.UUID) -> StubSession | None:
        return next(
            (s for s in self.sessions.values() if s.user_id == user_id and s.status == "active"),
            None,
        )

    def create_session(self, user_id: uuid.UUID, topic_id: int, level: Level) -> StubSession:
        session = StubSession(id=uuid.uuid4(), user_id=user_id, topic_id=topic_id, level=level)
        session.add_message("assistant", FIRST_QUESTION)
        self.sessions[session.id] = session
        return session

    def runs_for_session(self, session_id: uuid.UUID) -> list[StubRun]:
        return [r for r in self.runs.values() if r.session_id == session_id]


store = StubStore()


def code_hash(code: str) -> str:
    normalized = code.replace("\r\n", "\n").replace("\r", "\n")
    normalized = "\n".join(line.rstrip() for line in normalized.split("\n")).rstrip()
    return hashlib.sha256(normalized.encode()).hexdigest()
