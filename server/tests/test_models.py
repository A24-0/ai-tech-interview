# Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
# Proprietary and confidential. See LICENSE in the project root.
import uuid

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine

from app.infrastructure.db.base import Base
from app.infrastructure.db.models import InterviewSession, Message
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
