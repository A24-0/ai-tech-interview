# Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
# Proprietary and confidential. See LICENSE in the project root.
"""question and task bank, session state and message accounting

Revision ID: 0002
Revises: 0001
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

LEVEL_CHECK = "level IN ('junior', 'middle', 'senior')"
# 0001 passed full names to op.create_table, and the naming convention prefixed them again
DOUBLED_CHECKS = [
    ("interview_sessions", "ck_interview_sessions_ck_interview_sessions_status", "ck_interview_sessions_status"),
    ("interview_sessions", "ck_interview_sessions_ck_interview_sessions_level", "ck_interview_sessions_level"),
    ("messages", "ck_messages_ck_messages_role", "ck_messages_role"),
]
JSON_DOCUMENT = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    for table, doubled, name in DOUBLED_CHECKS:
        op.execute(f"ALTER TABLE {table} RENAME CONSTRAINT {doubled} TO {name}")

    op.create_table(
        "topics",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_topics"),
        sa.UniqueConstraint("code", name="uq_topics_code"),
    )
    op.create_table(
        "questions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("topic_id", sa.Integer(), nullable=False),
        sa.Column("level", sa.String(16), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("expected_answer", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.CheckConstraint(LEVEL_CHECK, name=op.f("ck_questions_level")),
        sa.CheckConstraint("kind IN ('theory', 'practice')", name=op.f("ck_questions_kind")),
        sa.ForeignKeyConstraint(
            ["topic_id"], ["topics.id"], name="fk_questions_topic_id_topics", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_questions"),
        sa.UniqueConstraint("topic_id", "text", name="uq_questions_topic_id"),
    )
    op.create_index("ix_questions_pick", "questions", ["topic_id", "level"])
    op.create_table(
        "code_tasks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("topic_id", sa.Integer(), nullable=False),
        sa.Column("level", sa.String(16), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("entry", sa.String(64), nullable=False),
        sa.Column("starter_code", sa.Text(), nullable=False),
        sa.Column("tests", JSON_DOCUMENT, nullable=False),
        sa.Column("limits", JSON_DOCUMENT, nullable=False),
        sa.Column("reference_solution", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.CheckConstraint(LEVEL_CHECK, name=op.f("ck_code_tasks_level")),
        sa.ForeignKeyConstraint(
            ["topic_id"], ["topics.id"], name="fk_code_tasks_topic_id_topics", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_code_tasks"),
        sa.UniqueConstraint("topic_id", "title", name="uq_code_tasks_topic_id"),
    )
    op.create_index("ix_code_tasks_pick", "code_tasks", ["topic_id", "level"])

    op.add_column("interview_sessions", sa.Column("current_question_id", sa.Integer(), nullable=True))
    op.add_column(
        "interview_sessions", sa.Column("questions_asked", sa.Integer(), server_default="0", nullable=False)
    )
    op.add_column("interview_sessions", sa.Column("tokens_used", sa.Integer(), server_default="0", nullable=False))
    op.add_column(
        "interview_sessions",
        sa.Column("last_activity_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.add_column("interview_sessions", sa.Column("reply_started_at", sa.DateTime(timezone=True), nullable=True))
    # sessions created before the bank existed: keep them valid under the new foreign keys
    op.execute(
        "INSERT INTO topics (id, code, title) "
        "SELECT DISTINCT topic_id, 'topic_' || topic_id, 'Тема ' || topic_id FROM interview_sessions"
    )
    op.execute("SELECT setval(pg_get_serial_sequence('topics', 'id'), COALESCE(MAX(id), 0) + 1, false) FROM topics")
    op.execute("UPDATE interview_sessions SET code_task_id = NULL")
    op.create_foreign_key(
        "fk_interview_sessions_topic_id_topics", "interview_sessions", "topics", ["topic_id"], ["id"]
    )
    op.create_foreign_key(
        "fk_interview_sessions_code_task_id_code_tasks", "interview_sessions", "code_tasks", ["code_task_id"], ["id"]
    )
    op.create_foreign_key(
        "fk_interview_sessions_current_question_id_questions",
        "interview_sessions",
        "questions",
        ["current_question_id"],
        ["id"],
    )
    op.create_index(
        "ix_interview_sessions_history",
        "interview_sessions",
        ["user_id", sa.text("created_at DESC"), sa.text("id DESC")],
    )

    op.add_column("messages", sa.Column("question_id", sa.Integer(), nullable=True))
    op.add_column("messages", sa.Column("reply_to_id", sa.BigInteger(), nullable=True))
    op.add_column("messages", sa.Column("step", sa.String(16), nullable=True))
    op.add_column("messages", sa.Column("tokens_in", sa.Integer(), nullable=True))
    op.add_column("messages", sa.Column("tokens_out", sa.Integer(), nullable=True))
    op.add_column("messages", sa.Column("duration_ms", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_messages_question_id_questions", "messages", "questions", ["question_id"], ["id"])
    op.create_foreign_key(
        "fk_messages_reply_to_id_messages", "messages", "messages", ["reply_to_id"], ["id"], ondelete="CASCADE"
    )
    op.create_unique_constraint("uq_messages_reply_to_id", "messages", ["reply_to_id"])
    op.create_check_constraint(
        op.f("ck_messages_step"), "messages", "step IN ('clarify', 'next_question', 'assign_task', 'finish')"
    )


def downgrade() -> None:
    op.drop_constraint(op.f("ck_messages_step"), "messages", type_="check")
    op.drop_constraint("uq_messages_reply_to_id", "messages", type_="unique")
    op.drop_constraint("fk_messages_reply_to_id_messages", "messages", type_="foreignkey")
    op.drop_constraint("fk_messages_question_id_questions", "messages", type_="foreignkey")
    for column in ("duration_ms", "tokens_out", "tokens_in", "step", "reply_to_id", "question_id"):
        op.drop_column("messages", column)

    op.drop_index("ix_interview_sessions_history", table_name="interview_sessions")
    op.drop_constraint("fk_interview_sessions_current_question_id_questions", "interview_sessions", type_="foreignkey")
    op.drop_constraint("fk_interview_sessions_code_task_id_code_tasks", "interview_sessions", type_="foreignkey")
    op.drop_constraint("fk_interview_sessions_topic_id_topics", "interview_sessions", type_="foreignkey")
    for column in ("reply_started_at", "last_activity_at", "tokens_used", "questions_asked", "current_question_id"):
        op.drop_column("interview_sessions", column)

    op.drop_index("ix_code_tasks_pick", table_name="code_tasks")
    op.drop_table("code_tasks")
    op.drop_index("ix_questions_pick", table_name="questions")
    op.drop_table("questions")
    op.drop_table("topics")

    for table, doubled, name in DOUBLED_CHECKS:
        op.execute(f"ALTER TABLE {table} RENAME CONSTRAINT {name} TO {doubled}")
