# Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
# Proprietary and confidential. See LICENSE in the project root.
"""Shared fixtures: in-memory SQLite, the app with a controllable stand-in interviewer."""

import json
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.interview_ai import NextStep, QuestionRef, StandInInterviewer, Turn, get_interviewer
from app.api.stub_store import store
from app.infrastructure.db.base import Base
from app.infrastructure.db.models import CodeTask, Question, Topic
from app.infrastructure.db.session import get_session_factory, make_session_factory
from app.main import create_app

Factory = async_sessionmaker[AsyncSession]

TASK_TESTS = [{"name": "пример", "args": [[1, 2, 3], 5], "expected": True}]


class FlakyInterviewer(StandInInterviewer):
    """The stand-in that can break: fail_times replies stop after the first chunk;
    during_reply runs after the first chunk (something else happening mid-stream)."""

    def __init__(self) -> None:
        super().__init__(delay_s=0)
        self.fail_times = 0
        self.during_reply: Callable[[], Awaitable[None]] | None = None

    async def reply(self, turn: Turn, step: NextStep, next_question: QuestionRef | None = None) -> AsyncIterator[str]:
        first = True
        async for chunk in super().reply(turn, step, next_question):
            yield chunk
            if first and self.during_reply is not None:
                await self.during_reply()
            first = False
            if self.fail_times:
                self.fail_times -= 1
                raise RuntimeError("provider is down")


@pytest.fixture
async def factory() -> AsyncIterator[Factory]:
    engine = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield make_session_factory(engine)
    await engine.dispose()


@pytest.fixture
def interviewer() -> FlakyInterviewer:
    return FlakyInterviewer()


@pytest.fixture
async def client(factory: Factory, interviewer: FlakyInterviewer) -> AsyncIterator[httpx.AsyncClient]:
    store.runs.clear()
    app = create_app()
    app.dependency_overrides[get_session_factory] = lambda: factory
    app.dependency_overrides[get_interviewer] = lambda: interviewer
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def seed_bank(factory: Factory, questions: int = 4, level: str = "junior", task: bool = True) -> int:
    async with factory() as db:
        topic = Topic(code="python_basics", title="Python: основы")
        db.add(topic)
        await db.flush()
        db.add_all(
            Question(topic_id=topic.id, level=level, text=f"Вопрос {i}?", expected_answer=f"Ответ {i}")
            for i in range(1, questions + 1)
        )
        if task:
            db.add(
                CodeTask(
                    topic_id=topic.id,
                    level=level,
                    title="Сумма пар",
                    statement="Верните True, если есть два числа с суммой k.",
                    entry="solve",
                    starter_code="def solve(nums, k):\n    pass\n",
                    tests=TASK_TESTS,
                    limits={"perTestTimeoutMs": 2000, "maxOutputBytes": 65536},
                    reference_solution="def solve(nums, k):\n    return False\n",
                )
            )
        await db.commit()
        return topic.id


def auth(user: str = "alice") -> dict[str, str]:
    return {"Authorization": f"Bearer {user}"}


def parse_sse(text: str) -> list[tuple[str, dict]]:
    events = []
    for block in text.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.split("\n"))
        events.append((lines["event"], json.loads(lines["data"])))
    return events


async def start(client: httpx.AsyncClient, topic_id: int, user: str = "alice", level: str = "junior") -> dict:
    resp = await client.post("/api/interviews", json={"topicId": topic_id, "level": level}, headers=auth(user))
    assert resp.status_code == 201, resp.text
    return resp.json()


async def send(
    client: httpx.AsyncClient,
    session_id: str,
    content: str = "ответ",
    client_message_id: uuid.UUID | None = None,
    user: str = "alice",
) -> httpx.Response:
    return await client.post(
        f"/api/interviews/{session_id}/messages",
        json={"content": content, "clientMessageId": str(client_message_id or uuid.uuid4())},
        headers=auth(user),
    )
