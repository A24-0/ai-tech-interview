# Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
# Proprietary and confidential. See LICENSE in the project root.
"""Interview sessions, messages and the question/task bank (S2-Y1, FR-16).

user_id has no foreign key yet: users belong to the auth module, which is not in the
Python version yet.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
    true,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.db.base import Base

LEVEL_CHECK = "level IN ('junior', 'middle', 'senior')"
JsonDocument = JSON().with_variant(JSONB(), "postgresql")
MessageId = BigInteger().with_variant(Integer, "sqlite")


def _now() -> datetime:
    return datetime.now(UTC)


class Topic(Base):
    __tablename__ = "topics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(64), unique=True)
    title: Mapped[str] = mapped_column(String(200))


class Question(Base):
    __tablename__ = "questions"
    __table_args__ = (
        CheckConstraint(LEVEL_CHECK, name="level"),
        CheckConstraint("kind IN ('theory', 'practice')", name="kind"),
        # import key: re-importing the same bank does not duplicate questions
        UniqueConstraint("topic_id", "text"),
        Index("ix_questions_pick", "topic_id", "level"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id", ondelete="CASCADE"))
    level: Mapped[str] = mapped_column(String(16))
    kind: Mapped[str] = mapped_column(String(16), default="theory")
    text: Mapped[str] = mapped_column(Text)
    expected_answer: Mapped[str] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())


class CodeTask(Base):
    __tablename__ = "code_tasks"
    __table_args__ = (
        CheckConstraint(LEVEL_CHECK, name="level"),
        UniqueConstraint("topic_id", "title"),
        Index("ix_code_tasks_pick", "topic_id", "level"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id", ondelete="CASCADE"))
    level: Mapped[str] = mapped_column(String(16))
    title: Mapped[str] = mapped_column(String(200))
    statement: Mapped[str] = mapped_column(Text)
    entry: Mapped[str] = mapped_column(String(64))
    starter_code: Mapped[str] = mapped_column(Text)
    tests: Mapped[list[dict[str, Any]]] = mapped_column(JsonDocument)
    limits: Mapped[dict[str, Any]] = mapped_column(JsonDocument)
    reference_solution: Mapped[str] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())


class InterviewSession(Base):
    __tablename__ = "interview_sessions"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'finished', 'abandoned')", name="status"),
        CheckConstraint(LEVEL_CHECK, name="level"),
        # one active session per user
        Index(
            "uq_interview_sessions_active_user",
            "user_id",
            unique=True,
            postgresql_where=text("status = 'active'"),
            sqlite_where=text("status = 'active'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id"))
    level: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16), default="active")
    code_task_id: Mapped[int | None] = mapped_column(ForeignKey("code_tasks.id"), nullable=True)
    current_question_id: Mapped[int | None] = mapped_column(ForeignKey("questions.id"), nullable=True)
    questions_asked: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    tokens_used: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    # set while the interviewer is answering: turns of one session go strictly one at a time
    reply_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, server_default=func.now()
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    messages: Mapped[list["Message"]] = relationship(
        back_populates="session", order_by="Message.id", cascade="all, delete-orphan"
    )


# interview history of a user, newest first (GET /interviews, S5-Y1)
Index(
    "ix_interview_sessions_history",
    InterviewSession.user_id,
    InterviewSession.created_at.desc(),
    InterviewSession.id.desc(),
)


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        CheckConstraint("role IN ('system', 'user', 'assistant')", name="role"),
        # idempotency key for POST /interviews/{id}/messages
        UniqueConstraint("session_id", "client_message_id"),
        CheckConstraint("step IN ('clarify', 'next_question', 'assign_task', 'finish')", name="step"),
    )

    id: Mapped[int] = mapped_column(MessageId, primary_key=True, autoincrement=True)
    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("interview_sessions.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(16))
    content: Mapped[str] = mapped_column(Text)
    client_message_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    question_id: Mapped[int | None] = mapped_column(ForeignKey("questions.id"), nullable=True)
    # the user message this assistant message answers; one answer per user message
    reply_to_id: Mapped[int | None] = mapped_column(
        MessageId, ForeignKey("messages.id", ondelete="CASCADE"), nullable=True, unique=True
    )
    # what the interviewer did with this answer: replaying it repeats the same outcome
    step: Mapped[str | None] = mapped_column(String(16), nullable=True)
    tokens_in: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_out: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    session: Mapped[InterviewSession] = relationship(back_populates="messages")
