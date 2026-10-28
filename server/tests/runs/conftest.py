# Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
# Proprietary and confidential. See LICENSE in the project root.
"""Fixtures for tests against a real PostgreSQL (TEST_DATABASE_URL).

Start one locally:
    docker run -d --name interview-test-db -e POSTGRES_USER=app -e POSTGRES_PASSWORD=app \
        -e POSTGRES_DB=interview_test -p 55432:5432 postgres:16
"""

import asyncio
import os
import uuid
from collections.abc import AsyncIterator
from typing import Any

import pytest
import sqlalchemy as sa
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.infrastructure.db.base import Base  # noqa: E402
from app.infrastructure.db import code_runs, models  # noqa: E402,F401

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+asyncpg://app:app@localhost:55432/interview_test"
)


async def _create_schema() -> None:
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
    finally:
        await engine.dispose()


@pytest.fixture(scope="session")
def database_url() -> str:
    try:
        asyncio.run(_create_schema())
    except (OSError, sa.exc.OperationalError, sa.exc.InterfaceError) as exc:
        pytest.skip(f"PostgreSQL is unreachable at TEST_DATABASE_URL: {exc}")
    return TEST_DATABASE_URL


@pytest.fixture
async def session_factory(database_url: str) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(database_url, poolclass=NullPool)
    yield async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        tables = ", ".join(table.name for table in Base.metadata.sorted_tables)
        await conn.execute(sa.text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
    await engine.dispose()


@pytest.fixture
async def client(session_factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[AsyncClient]:
    from fastapi import FastAPI

    from app.api import runs
    from app.api.errors import install_error_handlers
    from app.infrastructure.db.session import get_session

    async def override_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    app = FastAPI()
    install_error_handlers(app)
    app.include_router(runs.router)
    app.dependency_overrides[get_session] = override_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        yield http


def auth(user_id: uuid.UUID) -> dict[str, str]:
    return {"Authorization": f"Bearer {user_id}"}


DEFAULT_TESTS: list[dict[str, Any]] = [
    {"name": "t1", "args": [[1, 2, 3], 4], "expected": True},
    {"name": "t2", "args": [[], 1], "expected": False},
    {"name": "t3", "assert": "assert solve([5], 10) is False"},
]


async def _topic_id(db: AsyncSession) -> int:
    from app.infrastructure.db.models import Topic

    topic = await db.scalar(sa.select(Topic).limit(1))
    if topic is None:
        topic = Topic(code="python-basics", title="Python: основы")
        db.add(topic)
        await db.flush()
    return topic.id


async def create_task(factory: async_sessionmaker[AsyncSession], *, title: str = "Сумма пар") -> int:
    from app.infrastructure.db.models import CodeTask

    async with factory() as db, db.begin():
        task = CodeTask(
            topic_id=await _topic_id(db),
            level="junior",
            title=title,
            statement="Есть ли в списке два числа с суммой k?",
            entry="solve",
            starter_code="def solve(nums, k):\n    pass\n",
            tests=DEFAULT_TESTS,
            limits={"perTestTimeoutMs": 2000, "maxOutputBytes": 65536},
            reference_solution="",
        )
        db.add(task)
        await db.flush()
        return task.id


async def create_run(
    factory: async_sessionmaker[AsyncSession], session_id: uuid.UUID, code_task_id: int, *, code: str = "pass"
) -> uuid.UUID:
    from app.domain.code_runs import code_hash
    from app.infrastructure.db.code_runs import CodeRunModel

    run = CodeRunModel(
        session_id=session_id, code_task_id=code_task_id, client_run_id=uuid.uuid4(), code=code, code_hash=code_hash(code)
    )
    async with factory() as db, db.begin():
        db.add(run)
    return run.id


async def create_session(
    factory: async_sessionmaker[AsyncSession],
    user_id: uuid.UUID,
    *,
    status: str = "active",
    code_task_id: int | None = None,
) -> uuid.UUID:
    from app.infrastructure.db.models import InterviewSession

    session_id = uuid.uuid4()
    async with factory() as db, db.begin():
        db.add(
            InterviewSession(
                id=session_id,
                user_id=user_id,
                topic_id=await _topic_id(db),
                level="junior",
                status=status,
                code_task_id=code_task_id,
            )
        )
    return session_id
