# Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
# Proprietary and confidential. See LICENSE in the project root.
"""Runs stubs over real interview sessions (replaced by the runs queue)."""

import uuid
from datetime import timedelta

from app.api.stub_store import store
from tests.conftest import auth, seed_bank, send, start


async def _session_with_task(client, factory) -> dict:
    topic_id = await seed_bank(factory, questions=1)
    session = await start(client, topic_id)
    await send(client, session["id"])  # the bank is used up: the task is assigned
    return session


async def test_run_requires_task(client, factory):
    topic_id = await seed_bank(factory)
    session = await start(client, topic_id)

    resp = await client.post(
        f"/api/interviews/{session['id']}/runs",
        json={"code": "x = 1", "clientRunId": str(uuid.uuid4())},
        headers=auth(),
    )

    assert resp.status_code == 409
    assert resp.json()["code"] == "no_task"


async def test_run_lifecycle_and_idempotency(client, factory):
    session = await _session_with_task(client, factory)
    rid = str(uuid.uuid4())
    body = {"code": "def solve(nums, k):\n    pass\n", "clientRunId": rid}

    first = await client.post(f"/api/interviews/{session['id']}/runs", json=body, headers=auth())
    again = await client.post(f"/api/interviews/{session['id']}/runs", json=body, headers=auth())

    assert first.status_code == 202 and first.json()["status"] == "queued"
    assert again.json()["runId"] == first.json()["runId"]
    run_id = first.json()["runId"]
    running = (await client.get(f"/api/runs/{run_id}", headers=auth())).json()
    assert running["status"] == "running" and running["result"] is None

    store.runs[uuid.UUID(run_id)].created_at -= timedelta(seconds=3)
    done = (await client.get(f"/api/runs/{run_id}", headers=auth())).json()
    assert done["status"] == "done"
    assert done["result"]["passed"] == 2 and done["result"]["total"] == 3
    assert done["aiReview"]["issues"][0]["line"] == 1

    assert (await client.get(f"/api/runs/{run_id}", headers=auth("bob"))).status_code == 404
    foreign = await client.post(f"/api/interviews/{session['id']}/runs", json=body, headers=auth("bob"))
    assert foreign.status_code == 404


async def test_finish_cancels_runs(client, factory):
    session = await _session_with_task(client, factory)
    body = {"code": "def solve(nums, k):\n    pass\n", "clientRunId": str(uuid.uuid4())}
    run_id = (await client.post(f"/api/interviews/{session['id']}/runs", json=body, headers=auth())).json()["runId"]

    await client.post(f"/api/interviews/{session['id']}/finish", headers=auth())

    assert store.runs[uuid.UUID(run_id)].cancelled is True
    late = await client.post(
        f"/api/interviews/{session['id']}/runs",
        json={**body, "clientRunId": str(uuid.uuid4())},
        headers=auth(),
    )
    assert late.json()["code"] == "session_not_active"
