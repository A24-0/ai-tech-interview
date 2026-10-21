# Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
# Proprietary and confidential. See LICENSE in the project root.
"""POST /api/interviews/{id}/runs and GET /api/runs/{id} (contract, section 6.2)."""

import uuid

import pytest
import sqlalchemy as sa
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.code_runs import code_hash
from app.infrastructure.db.code_runs import CodeRunModel
from tests.conftest import auth, create_session, create_task

pytestmark = pytest.mark.db

Factory = async_sessionmaker[AsyncSession]
CODE = "def solve(nums, k):\n    return False\n"


async def _session_with_task(factory: Factory, user_id: uuid.UUID) -> uuid.UUID:
    return await create_session(factory, user_id, code_task_id=await create_task(factory))


def _submit(client: AsyncClient, session_id: uuid.UUID, user_id: uuid.UUID, client_run_id: uuid.UUID | None = None):
    body = {"code": CODE, "clientRunId": str(client_run_id or uuid.uuid4())}
    return client.post(f"/api/interviews/{session_id}/runs", json=body, headers=auth(user_id))


async def test_create_run_returns_202_and_queued(client: AsyncClient, session_factory: Factory) -> None:
    user_id = uuid.uuid4()
    session_id = await _session_with_task(session_factory, user_id)

    response = await _submit(client, session_id, user_id)

    assert response.status_code == 202
    body = response.json()
    assert set(body) == {"runId", "status"}
    assert body["status"] == "queued"
    async with session_factory() as db:
        run = await db.get(CodeRunModel, uuid.UUID(body["runId"]))
    assert run is not None
    assert run.code_hash == code_hash(CODE)
    assert run.attempts == 0


async def test_repeated_client_run_id_returns_same_run(client: AsyncClient, session_factory: Factory) -> None:
    user_id = uuid.uuid4()
    session_id = await _session_with_task(session_factory, user_id)
    client_run_id = uuid.uuid4()

    first = await _submit(client, session_id, user_id, client_run_id)
    second = await _submit(client, session_id, user_id, client_run_id)

    assert first.status_code == second.status_code == 202
    assert first.json()["runId"] == second.json()["runId"]
    async with session_factory() as db:
        assert await db.scalar(sa.select(sa.func.count()).select_from(CodeRunModel)) == 1


async def test_limit_per_task_returns_429(
    client: AsyncClient, session_factory: Factory, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("RUNS_PER_TASK_LIMIT", "2")
    user_id = uuid.uuid4()
    session_id = await _session_with_task(session_factory, user_id)

    statuses = [(await _submit(client, session_id, user_id)).status_code for _ in range(3)]

    assert statuses == [202, 202, 429]
    problem = (await _submit(client, session_id, user_id)).json()
    assert problem["code"] == "runs_limit"
    assert problem["status"] == 429


async def test_retry_after_limit_still_returns_existing_run(
    client: AsyncClient, session_factory: Factory, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("RUNS_PER_TASK_LIMIT", "1")
    user_id = uuid.uuid4()
    session_id = await _session_with_task(session_factory, user_id)
    client_run_id = uuid.uuid4()

    first = await _submit(client, session_id, user_id, client_run_id)
    retry = await _submit(client, session_id, user_id, client_run_id)

    assert retry.status_code == 202
    assert retry.json()["runId"] == first.json()["runId"]


async def test_without_task_returns_409_no_task(client: AsyncClient, session_factory: Factory) -> None:
    user_id = uuid.uuid4()
    session_id = await create_session(session_factory, user_id)

    response = await _submit(client, session_id, user_id)

    assert response.status_code == 409
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == "no_task"


async def test_finished_session_returns_409_session_not_active(
    client: AsyncClient, session_factory: Factory
) -> None:
    user_id = uuid.uuid4()
    task_id = await create_task(session_factory)
    session_id = await create_session(session_factory, user_id, status="finished", code_task_id=task_id)

    response = await _submit(client, session_id, user_id)

    assert response.status_code == 409
    assert response.json()["code"] == "session_not_active"


async def test_foreign_or_missing_session_returns_404(client: AsyncClient, session_factory: Factory) -> None:
    owner, stranger = uuid.uuid4(), uuid.uuid4()
    session_id = await _session_with_task(session_factory, owner)

    foreign = await _submit(client, session_id, stranger)
    missing = await _submit(client, uuid.uuid4(), owner)

    assert foreign.status_code == missing.status_code == 404
    assert foreign.json()["code"] == "session_not_found"


async def test_get_run_returns_contract_shape(client: AsyncClient, session_factory: Factory) -> None:
    user_id = uuid.uuid4()
    session_id = await _session_with_task(session_factory, user_id)
    run_id = (await _submit(client, session_id, user_id)).json()["runId"]

    response = await client.get(f"/api/runs/{run_id}", headers=auth(user_id))

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"runId", "status", "codeHash", "createdAt", "finishedAt", "result", "aiReview", "error"}
    assert body["runId"] == run_id
    assert body["status"] == "queued"
    assert body["codeHash"] == code_hash(CODE)
    assert body["result"] is None and body["aiReview"] is None and body["error"] is None


async def test_get_run_passes_result_through_only_when_done(client: AsyncClient, session_factory: Factory) -> None:
    user_id = uuid.uuid4()
    session_id = await _session_with_task(session_factory, user_id)
    run_id = uuid.UUID((await _submit(client, session_id, user_id)).json()["runId"])
    result = {"verdict": "failed", "passed": 2, "total": 3, "tests": [], "stdout": "", "stderr": "",
              "truncated": False, "metrics": {"lines": 2, "maxLoopDepth": 0}}
    review = {"summary": "ok", "issues": [{"line": 1, "severity": "info", "text": "x"}], "suggestions": []}

    async with session_factory() as db, db.begin():
        await db.execute(sa.update(CodeRunModel).where(CodeRunModel.id == run_id).values(status="running", result=result))
    running = (await client.get(f"/api/runs/{run_id}", headers=auth(user_id))).json()

    async with session_factory() as db, db.begin():
        await db.execute(
            sa.update(CodeRunModel)
            .where(CodeRunModel.id == run_id)
            .values(status="done", ai_review=review, finished_at=sa.func.now())
        )
    done = (await client.get(f"/api/runs/{run_id}", headers=auth(user_id))).json()

    assert running["result"] is None
    assert done["status"] == "done"
    assert done["result"] == result  # camelCase keys from the runner are passed through untouched
    assert done["aiReview"] == review
    assert done["finishedAt"] is not None


async def test_foreign_run_returns_404(client: AsyncClient, session_factory: Factory) -> None:
    owner = uuid.uuid4()
    session_id = await _session_with_task(session_factory, owner)
    run_id = (await _submit(client, session_id, owner)).json()["runId"]

    response = await client.get(f"/api/runs/{run_id}", headers=auth(uuid.uuid4()))

    assert response.status_code == 404
    assert response.json()["code"] == "run_not_found"


async def test_requests_without_token_return_401(client: AsyncClient, session_factory: Factory) -> None:
    response = await client.get(f"/api/runs/{uuid.uuid4()}")
    assert response.status_code == 401


async def test_empty_code_is_rejected(client: AsyncClient, session_factory: Factory) -> None:
    user_id = uuid.uuid4()
    session_id = await _session_with_task(session_factory, user_id)

    response = await client.post(
        f"/api/interviews/{session_id}/runs", json={"code": "", "clientRunId": str(uuid.uuid4())}, headers=auth(user_id)
    )

    assert response.status_code == 422
