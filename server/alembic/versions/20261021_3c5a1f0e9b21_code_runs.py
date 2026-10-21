"""code_runs: code submissions queue

Revision ID: 3c5a1f0e9b21
Revises: (interview_sessions/messages migration, S2-Y1)
Create Date: 2026-10-21 04:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "3c5a1f0e9b21"
# TODO(S2-Y1): set to the revision that creates interview_sessions and code_tasks,
# otherwise Alembic sees two heads and the foreign keys below have nothing to point to.
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "code_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code_task_id", sa.Integer(), nullable=False),
        sa.Column("client_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("code_hash", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), server_default="queued", nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("result", postgresql.JSONB(), nullable=True),
        sa.Column("ai_review", postgresql.JSONB(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("locked_by", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'done', 'failed', 'cancelled')", name=op.f("ck_code_runs_status")
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["interview_sessions.id"],
            name=op.f("fk_code_runs_session_id_interview_sessions"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["code_task_id"], ["code_tasks.id"], name=op.f("fk_code_runs_code_task_id_code_tasks")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_code_runs")),
        sa.UniqueConstraint("session_id", "client_run_id", name="ux_runs_idem"),
    )
    op.create_index(
        "ix_runs_queue", "code_runs", ["created_at"], postgresql_where=sa.text("status = 'queued'")
    )
    op.create_index(
        "ix_runs_stale", "code_runs", ["started_at"], postgresql_where=sa.text("status = 'running'")
    )
    op.create_index("ix_runs_dedupe", "code_runs", ["session_id", "code_task_id", "code_hash"])


def downgrade() -> None:
    op.drop_index("ix_runs_dedupe", table_name="code_runs")
    op.drop_index("ix_runs_stale", table_name="code_runs")
    op.drop_index("ix_runs_queue", table_name="code_runs")
    op.drop_table("code_runs")
