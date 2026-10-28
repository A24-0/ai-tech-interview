# Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
# Proprietary and confidential. See LICENSE in the project root.
"""Bank import (FR-16): admin endpoint, idempotency, one transaction, command line."""

import asyncio
import copy
import json
from collections import Counter
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import create_async_engine

from app.domain.bank import Bank
from app.infrastructure.db.base import Base
from app.infrastructure.db.models import CodeTask, Question, Topic
from app.scripts import import_bank
from tests.conftest import TASK_TESTS, auth

SEED = Path(__file__).resolve().parents[2] / "content" / "seed" / "python_basics.json"
TASKS = {
    "tasks": [
        {
            "topicCode": "python_basics",
            "level": "junior",
            "title": "Сумма пар",
            "statement": "Верните True, если есть два числа с суммой k.",
            "entry": "solve",
            "starterCode": "def solve(nums, k):\n    pass\n",
            "tests": TASK_TESTS,
            "limits": {"perTestTimeoutMs": 2000, "maxOutputBytes": 65536},
            "referenceSolution": "def solve(nums, k):\n    return False\n",
        }
    ]
}


def _bank() -> dict:
    return {**json.loads(SEED.read_text(encoding="utf-8")), **copy.deepcopy(TASKS)}


async def _count(factory, model) -> int:
    async with factory() as db:
        return await db.scalar(select(func.count()).select_from(model))


async def _create_tables(url: str) -> None:
    engine = create_async_engine(url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()


@pytest.fixture(autouse=True)
def admin_token(monkeypatch):
    monkeypatch.setenv("ADMIN_TOKENS", "root, ops")


def test_seed_has_ten_questions_of_three_levels():
    bank = Bank.model_validate_json(SEED.read_text(encoding="utf-8"))
    assert [t.code for t in bank.topics] == ["python_basics"]
    assert Counter(q.level for q in bank.questions) == {"junior": 4, "middle": 4, "senior": 2}
    assert all(q.expected_answer for q in bank.questions)


async def test_import_creates_and_reimport_does_not_duplicate(client, factory):
    first = await client.post("/api/admin/import", json=_bank(), headers=auth("root"))
    again = await client.post("/api/admin/import", json=_bank(), headers=auth("ops"))

    assert first.status_code == 200, first.text
    assert first.json() == {
        "topics": {"created": 1, "updated": 0},
        "questions": {"created": 10, "updated": 0},
        "tasks": {"created": 1, "updated": 0},
    }
    assert again.json() == {key: {"created": 0, "updated": 0} for key in ("topics", "questions", "tasks")}
    counts = (await _count(factory, Topic), await _count(factory, Question), await _count(factory, CodeTask))
    assert counts == (1, 10, 1)


async def test_changed_entries_are_updated_in_place(client, factory):
    await client.post("/api/admin/import", json=_bank(), headers=auth("root"))
    bank = _bank()
    bank["questions"][0]["expectedAnswer"] = "Новый эталон"
    bank["tasks"][0]["limits"] = {"perTestTimeoutMs": 3000, "maxOutputBytes": 65536}

    resp = await client.post("/api/admin/import", json=bank, headers=auth("root"))

    assert resp.json()["questions"] == {"created": 0, "updated": 1}
    assert resp.json()["tasks"] == {"created": 0, "updated": 1}
    async with factory() as db:
        task = await db.scalar(select(CodeTask))
        assert task.limits["perTestTimeoutMs"] == 3000


async def test_import_needs_admin(client, factory):
    user = await client.post("/api/admin/import", json=_bank(), headers=auth("alice"))
    anonymous = await client.post("/api/admin/import", json=_bank())

    assert (user.status_code, user.json()["code"]) == (403, "forbidden")
    assert anonymous.status_code == 401
    assert await _count(factory, Topic) == 0


async def test_unknown_topic_rolls_back_the_whole_file(client, factory):
    bank = _bank()
    bank["tasks"][0]["topicCode"] = "go_basics"

    resp = await client.post("/api/admin/import", json=bank, headers=auth("root"))

    assert (resp.status_code, resp.json()["code"]) == (422, "unknown_topic")
    assert (await _count(factory, Topic), await _count(factory, Question)) == (0, 0)


def test_command_line_merges_files(tmp_path, capsys, monkeypatch):
    tasks_file = tmp_path / "tasks.json"
    tasks_file.write_text(json.dumps(TASKS, ensure_ascii=False), encoding="utf-8")
    url = f"sqlite+aiosqlite:///{tmp_path / 'bank.db'}"
    monkeypatch.setenv("DATABASE_URL", url)

    asyncio.run(_create_tables(url))
    code = import_bank.main([str(SEED), str(tasks_file)])  # tasks use the topic of the seed file
    again = asyncio.run(import_bank.run([SEED, tasks_file], url))

    assert code == 0
    assert capsys.readouterr().out.splitlines() == [
        "темы: создано 1, обновлено 0",
        "вопросы: создано 10, обновлено 0",
        "задачи: создано 1, обновлено 0",
    ]
    assert (again.topics.created, again.questions.created, again.tasks.created) == (0, 0, 0)
    assert import_bank.main([str(tasks_file)]) == 0  # the topic is already in the database


def test_command_line_reports_unknown_topic(tmp_path, capsys, monkeypatch):
    tasks_file = tmp_path / "tasks.json"
    tasks_file.write_text(json.dumps(TASKS, ensure_ascii=False), encoding="utf-8")
    url = f"sqlite+aiosqlite:///{tmp_path / 'bank.db'}"
    monkeypatch.setenv("DATABASE_URL", url)

    asyncio.run(_create_tables(url))

    assert import_bank.main([str(tasks_file)]) == 1
    assert "python_basics" in capsys.readouterr().err
