# Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
# Proprietary and confidential. See LICENSE in the project root.
"""Async engine and session factory configured from DATABASE_URL (contract, section 8)."""

import os
from collections.abc import AsyncIterator
from functools import cache

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine


@cache
def get_engine() -> AsyncEngine:
    return create_async_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)


@cache
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(get_engine(), expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: one session per request."""
    async with get_session_factory()() as session:
        yield session
