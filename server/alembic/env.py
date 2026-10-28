# Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
# Proprietary and confidential. See LICENSE in the project root.
"""Alembic environment: async engine, URL from DATABASE_URL."""

import asyncio

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from app.infrastructure.db import models  # noqa: F401  (registers tables on Base.metadata)
from app.infrastructure.db.base import Base
from app.infrastructure.db.session import database_url

target_metadata = Base.metadata


def run_offline() -> None:
    context.configure(url=database_url(), target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def _do_run(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_online() -> None:
    engine = create_async_engine(database_url())
    async with engine.connect() as connection:
        await connection.run_sync(_do_run)
    await engine.dispose()


if context.is_offline_mode():
    run_offline()
else:
    asyncio.run(run_online())
