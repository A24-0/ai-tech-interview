# Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
# Proprietary and confidential. See LICENSE in the project root.
"""code_runs table: code submissions waiting for or processed by the sandbox worker."""

import uuid
from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.code_runs import RUN_STATUSES
from app.infrastructure.db.base import Base

# Tables of the interview zone, referenced as lightweight Core constructs: this module
# needs a few of their columns but must not own or redefine their ORM models.
interview_sessions = sa.table(
    "interview_sessions",
    sa.column("id", UUID(as_uuid=True)),
    sa.column("user_id", UUID(as_uuid=True)),
    sa.column("status", sa.Text),
    sa.column("code_task_id", sa.Integer),
)
code_tasks = sa.table(
    "code_tasks",
    sa.column("id", sa.Integer),
    sa.column("title", sa.Text),
    sa.column("statement", sa.Text),
    sa.column("entry", sa.Text),
    sa.column("tests", JSONB),
    sa.column("limits", JSONB),
)


class CodeRunModel(Base):
    __tablename__ = "code_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("interview_sessions.id", ondelete="CASCADE")
    )
    code_task_id: Mapped[int] = mapped_column(sa.ForeignKey("code_tasks.id"))
    client_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    code: Mapped[str] = mapped_column(sa.Text)
    code_hash: Mapped[str] = mapped_column(sa.Text)
    status: Mapped[str] = mapped_column(sa.Text, default="queued", server_default="queued")
    attempts: Mapped[int] = mapped_column(default=0, server_default="0")
    result: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    ai_review: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    error: Mapped[str | None] = mapped_column(sa.Text)
    locked_by: Mapped[str | None] = mapped_column(sa.Text)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), server_default=sa.func.now())
    started_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))

    __table_args__ = (
        sa.CheckConstraint(sa.column("status").in_(RUN_STATUSES), name="status"),
        sa.UniqueConstraint("session_id", "client_run_id", name="ux_runs_idem"),
        sa.Index("ix_runs_queue", "created_at", postgresql_where=sa.text("status = 'queued'")),
        sa.Index("ix_runs_stale", "started_at", postgresql_where=sa.text("status = 'running'")),
        sa.Index("ix_runs_dedupe", "session_id", "code_task_id", "code_hash"),
    )
