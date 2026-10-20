# Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
# Proprietary and confidential. See LICENSE in the project root.
import uuid

import httpx
import pytest

from app.api.stub_store import store
from app.main import create_app


@pytest.fixture
async def client():
    store.sessions.clear()
    store.runs.clear()
    transport = httpx.ASGITransport(app=create_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


def auth(user: str = "alice") -> dict[str, str]:
    return {"Authorization": f"Bearer {user}"}


async def start(client: httpx.AsyncClient, user: str = "alice") -> dict:
    resp = await client.post("/api/interviews", json={"topicId": 1, "level": "junior"}, headers=auth(user))
    assert resp.status_code == 201, resp.text
    return resp.json()


def parse_sse(text: str) -> list[tuple[str, dict]]:
    import json

    events = []
    for block in text.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.split("\n"))
        events.append((lines["event"], json.loads(lines["data"])))
    return events


async def send(client, session_id, content="ответ", client_message_id=None, user="alice"):
    return await client.post(
        f"/api/interviews/{session_id}/messages",
        json={"content": content, "clientMessageId": str(client_message_id or uuid.uuid4())},
        headers=auth(user),
    )


async def test_start_returns_camel_case_shape(client):
    data = await start(client)
    assert data["status"] == "active"
    assert data["topicId"] == 1
    assert data["task"] is None
    assert data["messages"][0]["role"] == "assistant"
    assert "createdAt" in data["messages"][0]


async def test_requires_auth(client):
    resp = await client.post("/api/interviews", json={"topicId": 1, "level": "junior"})
    assert resp.status_code == 401
    assert resp.headers["content-type"].startswith("application/problem+json")


async def test_second_active_session_conflicts(client):
    first = await start(client)
    resp = await client.post("/api/interviews", json={"topicId": 1, "level": "junior"}, headers=auth())
    assert resp.status_code == 409
    assert resp.json()["code"] == "active_session_exists"
    assert resp.json()["detail"] == first["id"]


async def test_message_streams_tokens_then_done(client):
    session = await start(client)
    resp = await send(client, session["id"])
    assert resp.headers["content-type"].startswith("text/event-stream")
    assert resp.headers["x-accel-buffering"] == "no"
    events = parse_sse(resp.text)
    assert [e for e, _ in events[:-1]] == ["token"] * (len(events) - 1)
    assert len(events) > 2
    name, done = events[-1]
    assert name == "done"
    assert done["finished"] is False and done["taskAssigned"] is None


async def test_repeat_client_message_id_does_not_duplicate(client):
    session = await start(client)
    cid = uuid.uuid4()
    await send(client, session["id"], client_message_id=cid)
    replay = parse_sse((await send(client, session["id"], client_message_id=cid)).text)
    assert [e for e, _ in replay] == ["token", "done"]
    state = (await client.get(f"/api/interviews/{session['id']}", headers=auth())).json()
    assert [m["role"] for m in state["messages"]] == ["assistant", "user", "assistant"]


async def test_task_assigned_after_second_answer(client):
    session = await start(client)
    await send(client, session["id"])
    events = parse_sse((await send(client, session["id"])).text)
    assigned = events[-1][1]["taskAssigned"]
    assert assigned["starterCode"].startswith("def solve")
    state = (await client.get(f"/api/interviews/{session['id']}", headers=auth())).json()
    assert state["task"]["id"] == assigned["id"]


async def test_foreign_session_is_404(client):
    session = await start(client)
    assert (await client.get(f"/api/interviews/{session['id']}", headers=auth("bob"))).status_code == 404
    assert (await send(client, session["id"], user="bob")).status_code == 404


async def test_active_and_finish(client):
    session = await start(client)
    assert (await client.get("/api/interviews/active", headers=auth())).json()["id"] == session["id"]
    resp = await client.post(f"/api/interviews/{session['id']}/finish", headers=auth())
    assert resp.json() == {"id": session["id"], "status": "finished"}
    assert (await client.get("/api/interviews/active", headers=auth())).status_code == 404


async def test_run_requires_task(client):
    session = await start(client)
    resp = await client.post(
        f"/api/interviews/{session['id']}/runs",
        json={"code": "x = 1", "clientRunId": str(uuid.uuid4())},
        headers=auth(),
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "no_task"


async def test_run_lifecycle_and_idempotency(client):
    session = await start(client)
    await send(client, session["id"])
    await send(client, session["id"])
    rid = str(uuid.uuid4())
    body = {"code": "def solve(nums, k):\n    pass\n", "clientRunId": rid}
    first = await client.post(f"/api/interviews/{session['id']}/runs", json=body, headers=auth())
    again = await client.post(f"/api/interviews/{session['id']}/runs", json=body, headers=auth())
    assert first.status_code == 202 and first.json()["status"] == "queued"
    assert again.json()["runId"] == first.json()["runId"]

    run_id = first.json()["runId"]
    running = (await client.get(f"/api/runs/{run_id}", headers=auth())).json()
    assert running["status"] == "running" and running["result"] is None

    store.runs[uuid.UUID(run_id)].created_at -= __import__("datetime").timedelta(seconds=3)
    done = (await client.get(f"/api/runs/{run_id}", headers=auth())).json()
    assert done["status"] == "done"
    assert done["result"]["passed"] == 2 and done["result"]["total"] == 3
    assert done["aiReview"]["issues"][0]["line"] == 1

    assert (await client.get(f"/api/runs/{run_id}", headers=auth("bob"))).status_code == 404
