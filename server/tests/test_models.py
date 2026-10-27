# Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
# Proprietary and confidential. See LICENSE in the project root.
import uuid

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine

from app.infrastructure.db.base import Base
from app.infrastructure.db.models import InterviewSession, Message, Question, Topic
from app.infrastructure.db.session import make_session_factory


@pytest.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield make_session_factory(engine)
    await engine.dispose()


def new_session(user: uuid.UUID, status: str = "active") -> InterviewSession:
    return InterviewSession(user_id=user, topic_id=1, level="junior", status=status)


async def test_one_active_session_per_user(db):
    user = uuid.uuid4()
    async with db() as s:
        s.add(new_session(user))
        await s.commit()
        s.add(new_session(user))
        with pytest.raises(IntegrityError):
            await s.commit()


async def test_finished_session_does_not_block_new_one(db):
    user = uuid.uuid4()
    async with db() as s:
        s.add_all([new_session(user, "finished"), new_session(user, "finished"), new_session(user)])
        await s.commit()


async def test_other_user_can_have_active_session(db):
    async with db() as s:
        s.add_all([new_session(uuid.uuid4()), new_session(uuid.uuid4())])
        await s.commit()


async def test_message_client_id_unique_per_session(db):
    async with db() as s:
        session = new_session(uuid.uuid4())
        s.add(session)
        await s.flush()
        cid = uuid.uuid4()
        s.add(Message(session_id=session.id, role="user", content="a", client_message_id=cid))
        await s.commit()
        s.add(Message(session_id=session.id, role="user", content="b", client_message_id=cid))
        with pytest.raises(IntegrityError):
            await s.commit()


async def test_invalid_level_rejected(db):
    async with db() as s:
        s.add(InterviewSession(user_id=uuid.uuid4(), topic_id=1, level="expert"))
        with pytest.raises(IntegrityError):
            await s.commit()


async def test_one_answer_per_user_message(db):
    async with db() as s:
        session = new_session(uuid.uuid4())
        s.add(session)
        await s.flush()
        question = Message(session_id=session.id, role="user", content="ответ", client_message_id=uuid.uuid4())
        s.add(question)
        await s.flush()
        s.add(Message(session_id=session.id, role="assistant", content="a", reply_to_id=question.id))
        await s.commit()
        s.add(Message(session_id=session.id, role="assistant", content="b", reply_to_id=question.id))
        with pytest.raises(IntegrityError):
            await s.commit()


async def test_bank_keys_are_unique_per_topic(db):
    async with db() as s:
        python, go = Topic(code="python_basics", title="Python"), Topic(code="go_basics", title="Go")
        s.add_all([python, go])
        await s.flush()
        s.add_all(
            Question(topic_id=t.id, level="junior", text="Что такое срез?", expected_answer="...") for t in (python, go)
        )
        await s.commit()
        s.add(Question(topic_id=python.id, level="middle", text="Что такое срез?", expected_answer="..."))
        with pytest.raises(IntegrityError):
            await s.commit()


async def test_new_session_counters_start_at_zero(db):
    async with db() as s:
        session = new_session(uuid.uuid4())
        s.add(session)
        await s.commit()
        assert (session.questions_asked, session.tokens_used, session.code_task_id) == (0, 0, None)
        assert session.last_activity_at is not None
