# Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
# Proprietary and confidential. See LICENSE in the project root.
"""The code_runs migration creates exactly what CodeRunModel declares, and rolls back cleanly."""

import importlib.util
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from app.infrastructure.db.base import Base

pytestmark = pytest.mark.db

SCHEMA = "migration_check"
MIGRATION = next((Path(__file__).parents[1] / "alembic" / "versions").glob("*_code_runs.py"))


def _load_migration():
    spec = importlib.util.spec_from_file_location("code_runs_migration", MIGRATION)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _ddl(connection: Connection) -> list[str]:
    """Index and constraint definitions as PostgreSQL reports them (autogenerate ignores WHERE of partial indexes)."""
    indexes = connection.execute(
        sa.text("SELECT indexdef FROM pg_indexes WHERE schemaname = :schema AND tablename = 'code_runs'"),
        {"schema": SCHEMA},
    ).scalars()
    constraints = connection.execute(
        sa.text(
            "SELECT conname || ' ' || pg_get_constraintdef(oid) FROM pg_constraint"
            " WHERE conrelid = 'code_runs'::regclass"
        )
    ).scalars()
    return sorted([*indexes, *constraints])


def _check(connection: Connection) -> tuple[list, list[str], list[str], bool]:
    migration = _load_migration()
    code_runs = Base.metadata.tables["code_runs"]
    Base.metadata.create_all(connection, tables=[t for t in Base.metadata.sorted_tables if t is not code_runs])

    context = MigrationContext.configure(connection)
    with Operations.context(context):
        migration.upgrade()
    diffs = compare_metadata(context, Base.metadata)
    migrated_ddl = _ddl(connection)
    with Operations.context(context):
        migration.downgrade()
    dropped = not sa.inspect(connection).has_table("code_runs")

    code_runs.create(connection)
    model_ddl = _ddl(connection)
    return diffs, migrated_ddl, model_ddl, dropped


async def test_migration_matches_model(database_url: str) -> None:
    engine = create_async_engine(
        database_url, poolclass=NullPool, connect_args={"server_settings": {"search_path": SCHEMA}}
    )
    try:
        async with engine.begin() as conn:
            await conn.execute(sa.text(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE"))
            await conn.execute(sa.text(f"CREATE SCHEMA {SCHEMA}"))
        async with engine.begin() as conn:
            diffs, migrated_ddl, model_ddl, dropped = await conn.run_sync(_check)
    finally:
        async with engine.begin() as conn:
            await conn.execute(sa.text(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE"))
        await engine.dispose()

    assert diffs == []
    assert migrated_ddl == model_ddl
    assert any("WHERE (status = 'queued'::text)" in line for line in migrated_ddl)
    assert dropped
