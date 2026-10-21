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

import jwt
import pytest
import sqlalchemy as sa
from httpx import ASGITransport, AsyncClient
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

os.environ.setdefault("JWT_SECRET", "test-secret-at-least-32-bytes-long!")

from app.infrastructure.db.base import Base  # noqa: E402
from app.infrastructure.db.code_runs import code_tasks, interview_sessions  # noqa: E402

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+asyncpg://app:app@localhost:55432/interview_test"
)


def _ensure_interview_zone_tables() -> None:
    """Minimal stand-ins for tables of the interview zone while its models are not in main."""
    metadata = Base.metadata
    if "code_tasks" not in metadata.tables:
        sa.Table(
            "code_tasks",
            metadata,
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("title", sa.Text, nullable=False),
            sa.Column("statement", sa.Text, nullable=False),
            sa.Column("entry", sa.Text, nullable=False),
            sa.Column("tests", JSONB, nullable=False),
            sa.Column("limits", JSONB, nullable=False),
        )
    if "interview_sessions" not in metadata.tables:
        sa.Table(
            "interview_sessions",
            metadata,
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("user_id", UUID(as_uuid=True), nullable=False),
            sa.Column("status", sa.Text, nullable=False, server_default="active"),
            sa.Column("code_task_id", sa.ForeignKey("code_tasks.id")),
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
    _ensure_interview_zone_tables()
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
    from app.infrastructure.db.session import get_session

    async def override_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    app = FastAPI()
    app.include_router(runs.router)
    app.dependency_overrides[get_session] = override_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        yield http


def auth(user_id: uuid.UUID) -> dict[str, str]:
    token = jwt.encode({"sub": str(user_id)}, os.environ["JWT_SECRET"], algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


DEFAULT_TESTS: list[dict[str, Any]] = [
    {"name": "t1", "args": [[1, 2, 3], 4], "expected": True},
    {"name": "t2", "args": [[], 1], "expected": False},
    {"name": "t3", "assert": "assert solve([5], 10) is False"},
]


async def create_task(factory: async_sessionmaker[AsyncSession], *, title: str = "Сумма пар") -> int:
    async with factory() as db, db.begin():
        return await db.scalar(
            sa.insert(code_tasks)
            .values(
                title=title,
                statement="Есть ли в списке два числа с суммой k?",
                entry="solve",
                tests=DEFAULT_TESTS,
                limits={"perTestTimeoutMs": 2000, "maxOutputBytes": 65536},
            )
            .returning(code_tasks.c.id)
        )


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
    session_id = uuid.uuid4()
    async with factory() as db, db.begin():
        await db.execute(
            sa.insert(interview_sessions).values(
                id=session_id, user_id=user_id, status=status, code_task_id=code_task_id
            )
        )
    return session_id
