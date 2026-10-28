# Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
# Proprietary and confidential. See LICENSE in the project root.
"""Async engine and session factory configured from DATABASE_URL."""

import os
from collections.abc import AsyncIterator
from functools import cache

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

DEFAULT_URL = "postgresql+asyncpg://app:app@localhost:5432/interview"


def database_url() -> str:
    return os.environ.get("DATABASE_URL", DEFAULT_URL)


def make_engine(url: str | None = None) -> AsyncEngine:
    return create_async_engine(url or database_url())


def make_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


@cache
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """FastAPI dependency: one engine per process. Endpoints open short sessions from it,
    so a streamed answer never keeps a transaction open while the model is talking."""
    return make_session_factory(make_engine())


async def get_session() -> AsyncIterator[AsyncSession]:
    async with get_session_factory()() as session:
        yield session
