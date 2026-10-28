# Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
# Proprietary and confidential. See LICENSE in the project root.
"""Queries of the interview API (S2-Y2…Y4, S3-Y2). The caller owns the transaction."""

import uuid
from collections.abc import Collection

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models import CodeTask, InterviewSession, Message, Question, Topic


class SqlAlchemyInterviewRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(
        self, session_id: uuid.UUID, user_id: uuid.UUID, *, for_update: bool = False
    ) -> InterviewSession | None:
        """Only the owner sees a session: someone else's id behaves as a missing one."""
        query = select(InterviewSession).where(InterviewSession.id == session_id, InterviewSession.user_id == user_id)
        if for_update:
            query = query.with_for_update()
        return await self.db.scalar(query)

    async def get_active_for_user(self, user_id: uuid.UUID) -> InterviewSession | None:
        return await self.db.scalar(
            select(InterviewSession).where(InterviewSession.user_id == user_id, InterviewSession.status == "active")
        )

    def add(self, session: InterviewSession) -> None:
        self.db.add(session)

    def add_message(self, message: Message) -> None:
        self.db.add(message)

    async def find_message_by_client_id(self, session_id: uuid.UUID, client_message_id: uuid.UUID) -> Message | None:
        return await self.db.scalar(
            select(Message).where(Message.session_id == session_id, Message.client_message_id == client_message_id)
        )

    async def find_reply(self, message_id: int) -> Message | None:
        return await self.db.scalar(select(Message).where(Message.reply_to_id == message_id))

    async def latest_user_message_id(self, session_id: uuid.UUID) -> int | None:
        return await self.db.scalar(
            select(func.max(Message.id)).where(Message.session_id == session_id, Message.role == "user")
        )

    async def list_messages(self, session_id: uuid.UUID) -> list[Message]:
        result = await self.db.scalars(select(Message).where(Message.session_id == session_id).order_by(Message.id))
        return list(result)

    async def get_topic(self, topic_id: int) -> Topic | None:
        return await self.db.get(Topic, topic_id)

    async def get_question(self, question_id: int | None) -> Question | None:
        return None if question_id is None else await self.db.get(Question, question_id)

    async def get_task(self, task_id: int | None) -> CodeTask | None:
        return None if task_id is None else await self.db.get(CodeTask, task_id)

    async def pick_question(self, topic_id: int, level: str, asked: Collection[int] = ()) -> Question | None:
        """A random active question of the topic and level that was not asked in this session."""
        query = select(Question).where(
            Question.topic_id == topic_id, Question.level == level, Question.is_active.is_(True)
        )
        if asked:
            query = query.where(Question.id.not_in(asked))
        return await self.db.scalar(query.order_by(func.random()).limit(1))

    async def pick_task(self, topic_id: int, level: str) -> CodeTask | None:
        """The first active task of the topic and level."""
        return await self.db.scalar(
            select(CodeTask)
            .where(CodeTask.topic_id == topic_id, CodeTask.level == level, CodeTask.is_active.is_(True))
            .order_by(CodeTask.id)
            .limit(1)
        )
