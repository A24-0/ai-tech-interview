# Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
# Proprietary and confidential. See LICENSE in the project root.
"""Idempotent bank import (FR-16): the same file twice creates nothing new.

Runs inside the caller's transaction and does not commit: either the whole file lands or
nothing does.
"""

from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.bank import Bank, ImportCounts, ImportResult, UnknownTopicError
from app.infrastructure.db.models import CodeTask, Question, Topic


def _apply(row: Any, fields: dict[str, Any]) -> bool:
    """Copies the changed fields onto the row; True when something changed."""
    changed = {name: value for name, value in fields.items() if getattr(row, name) != value}
    for name, value in changed.items():
        setattr(row, name, value)
    return bool(changed)


def _upsert(db: AsyncSession, existing: Any | None, model: type, fields: dict[str, Any], counts: ImportCounts) -> None:
    if existing is None:
        db.add(model(**fields))
        counts.created += 1
    elif _apply(existing, fields):
        counts.updated += 1


async def import_bank(db: AsyncSession, bank: Bank) -> ImportResult:
    if db.get_bind().dialect.name == "postgresql":
        # two imports at once would both read "no such topic" and collide on insert: run them in turn
        await db.execute(text("SELECT pg_advisory_xact_lock(hashtext('bank_import'))"))
    result = ImportResult()

    topics = {topic.code: topic for topic in await db.scalars(select(Topic))}
    for item in {item.code: item for item in bank.topics}.values():  # a later duplicate wins
        if item.code not in topics:
            topics[item.code] = Topic(code=item.code, title=item.title)
            db.add(topics[item.code])
            result.topics.created += 1
        elif _apply(topics[item.code], {"title": item.title}):
            result.topics.updated += 1
    await db.flush()

    def topic_id(code: str) -> int:
        if code not in topics:
            raise UnknownTopicError(code)
        return topics[code].id

    questions = {(q.topic_id, q.text): q for q in await db.scalars(select(Question))}
    incoming_questions = {(topic_id(q.topic_code), q.text): q for q in bank.questions}
    for (tid, question_text), item in incoming_questions.items():
        fields = {
            "topic_id": tid,
            "level": item.level,
            "kind": item.kind,
            "text": question_text,
            "expected_answer": item.expected_answer,
            "is_active": True,
        }
        _upsert(db, questions.get((tid, question_text)), Question, fields, result.questions)

    tasks = {(t.topic_id, t.title): t for t in await db.scalars(select(CodeTask))}
    incoming_tasks = {(topic_id(t.topic_code), t.title): t for t in bank.tasks}
    for (tid, title), item in incoming_tasks.items():
        fields = {
            "topic_id": tid,
            "level": item.level,
            "title": title,
            "statement": item.statement,
            "entry": item.entry,
            "starter_code": item.starter_code,
            "tests": item.tests,
            "limits": item.limits,
            "reference_solution": item.reference_solution,
            "is_active": True,
        }
        _upsert(db, tasks.get((tid, title)), CodeTask, fields, result.tasks)

    await db.flush()
    return result
