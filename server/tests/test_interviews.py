# Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
# Proprietary and confidential. See LICENSE in the project root.
"""Interview API on the database: start, streamed answers, idempotency, task, finish."""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from app.api import interviews
from app.api.interview_ai import Turn
from app.infrastructure.db.models import InterviewSession, Message
from tests.conftest import auth, parse_sse, seed_bank, send, start


async def _session(factory, session_id: str) -> InterviewSession:
    async with factory() as db:
        return await db.get(InterviewSession, uuid.UUID(session_id))


async def _messages(factory, session_id: str) -> list[Message]:
    async with factory() as db:
        query = select(Message).where(Message.session_id == uuid.UUID(session_id)).order_by(Message.id)
        return list(await db.scalars(query))


async def test_start_asks_a_question_from_the_bank(client, factory):
    topic_id = await seed_bank(factory)

    data = await start(client, topic_id)

    assert data["status"] == "active" and data["topicId"] == topic_id and data["level"] == "junior"
    assert data["task"] is None
    [first] = data["messages"]
    assert first["role"] == "assistant" and "createdAt" in first
    session = await _session(factory, data["id"])
    [message] = await _messages(factory, data["id"])
    assert session.questions_asked == 1
    assert message.question_id == session.current_question_id
    assert f"Вопрос {session.current_question_id}?" in first["content"]
    assert session.tokens_used > 0


async def test_start_requires_auth(client):
    resp = await client.post("/api/interviews", json={"topicId": 1, "level": "junior"})
    assert resp.status_code == 401
    assert resp.headers["content-type"].startswith("application/problem+json")


async def test_unknown_topic_and_empty_bank(client, factory):
    topic_id = await seed_bank(factory, level="junior")

    missing = await client.post("/api/interviews", json={"topicId": 999, "level": "junior"}, headers=auth())
    empty = await client.post("/api/interviews", json={"topicId": topic_id, "level": "senior"}, headers=auth())

    assert (missing.status_code, missing.json()["code"]) == (404, "topic_not_found")
    assert (empty.status_code, empty.json()["code"]) == (409, "no_questions")


async def test_second_active_session_conflicts(client, factory):
    topic_id = await seed_bank(factory)
    first = await start(client, topic_id)

    resp = await client.post("/api/interviews", json={"topicId": topic_id, "level": "junior"}, headers=auth())

    assert resp.status_code == 409
    assert resp.json()["code"] == "active_session_exists"
    assert resp.json()["detail"] == first["id"]
    assert (await start(client, topic_id, user="bob"))["id"] != first["id"]


async def test_model_failure_on_start_creates_nothing(client, factory, interviewer):
    topic_id = await seed_bank(factory)
    interviewer.fail_times = 1

    resp = await client.post("/api/interviews", json={"topicId": topic_id, "level": "junior"}, headers=auth())

    assert (resp.status_code, resp.json()["code"]) == (503, "ai_unavailable")
    assert (await client.get("/api/interviews/active", headers=auth())).status_code == 404


async def test_answer_streams_tokens_then_done_and_is_saved(client, factory):
    topic_id = await seed_bank(factory)
    data = await start(client, topic_id)
    before = await _session(factory, data["id"])

    resp = await send(client, data["id"], content="Список изменяемый, кортеж нет")

    assert resp.headers["content-type"].startswith("text/event-stream")
    assert resp.headers["x-accel-buffering"] == "no" and resp.headers["cache-control"] == "no-cache"
    events = parse_sse(resp.text)
    assert [name for name, _ in events] == ["token"] * (len(events) - 1) + ["done"]
    assert len(events) > 2
    done = events[-1][1]
    assert done["taskAssigned"] is None and done["finished"] is False

    user, reply = (await _messages(factory, data["id"]))[1:]
    assert (done["userMessageId"], done["messageId"]) == (user.id, reply.id)
    assert reply.reply_to_id == user.id
    assert reply.content == "".join(payload["text"] for name, payload in events if name == "token")
    assert reply.tokens_in > 0 and reply.tokens_out > 0 and reply.duration_ms >= 0
    after = await _session(factory, data["id"])
    assert after.tokens_used == before.tokens_used + reply.tokens_in + reply.tokens_out
    assert after.last_activity_at >= before.last_activity_at


async def test_next_question_is_new_and_counted(client, factory):
    topic_id = await seed_bank(factory, questions=4)
    data = await start(client, topic_id)

    await send(client, data["id"])
    await send(client, data["id"])

    session = await _session(factory, data["id"])
    asked = [m.question_id for m in await _messages(factory, data["id"]) if m.question_id is not None]
    assert session.questions_asked == 3
    assert len(asked) == len(set(asked)) == 3
    assert session.current_question_id == asked[-1]


async def test_repeated_client_message_id_replays_without_duplicates(client, factory):
    topic_id = await seed_bank(factory)
    data = await start(client, topic_id)
    cid = uuid.uuid4()

    first = parse_sse((await send(client, data["id"], client_message_id=cid)).text)
    replay = parse_sse((await send(client, data["id"], content="другой текст", client_message_id=cid)).text)

    assert [name for name, _ in replay] == ["token", "done"]
    assert replay[0][1]["text"] == "".join(p["text"] for name, p in first if name == "token")
    assert replay[1][1]["messageId"] == first[-1][1]["messageId"]
    state = (await client.get(f"/api/interviews/{data['id']}", headers=auth())).json()
    assert [m["role"] for m in state["messages"]] == ["assistant", "user", "assistant"]
    assert (await _session(factory, data["id"])).questions_asked == 2


async def test_retry_after_model_failure_answers_the_same_message(client, factory, interviewer):
    topic_id = await seed_bank(factory)
    data = await start(client, topic_id)
    cid = uuid.uuid4()
    interviewer.fail_times = 1

    broken = parse_sse((await send(client, data["id"], client_message_id=cid)).text)
    retried = parse_sse((await send(client, data["id"], client_message_id=cid)).text)

    assert broken[-1] == (
        "error",
        {"code": "ai_unavailable", "message": "Модель временно недоступна", "retryable": True},
    )
    assert retried[-1][0] == "done"
    roles = [m.role for m in await _messages(factory, data["id"])]
    assert roles == ["assistant", "user", "assistant"]
    assert (await _session(factory, data["id"])).questions_asked == 2


async def test_task_after_question_limit_then_finish(client, factory):
    topic_id = await seed_bank(factory, questions=5)
    data = await start(client, topic_id)
    await send(client, data["id"])
    await send(client, data["id"])  # junior: 3 questions asked

    assigned = parse_sse((await send(client, data["id"])).text)[-1][1]

    assert assigned["taskAssigned"]["title"] == "Сумма пар"
    assert assigned["taskAssigned"]["starterCode"].startswith("def solve")
    assert assigned["taskAssigned"]["language"] == "python"
    assert assigned["finished"] is False
    state = (await client.get(f"/api/interviews/{data['id']}", headers=auth())).json()
    assert state["task"]["id"] == assigned["taskAssigned"]["id"]

    closing = parse_sse((await send(client, data["id"])).text)[-1][1]
    assert closing["finished"] is True and closing["taskAssigned"] is None
    session = await _session(factory, data["id"])
    assert session.status == "finished" and session.finished_at is not None
    late = await send(client, data["id"])
    assert (late.status_code, late.json()["code"]) == (409, "session_not_active")


async def test_used_up_bank_moves_to_the_task(client, factory):
    topic_id = await seed_bank(factory, questions=1)
    data = await start(client, topic_id)

    done = parse_sse((await send(client, data["id"])).text)[-1][1]

    assert done["taskAssigned"]["title"] == "Сумма пар"


async def test_no_task_in_bank_finishes_the_interview(client, factory):
    topic_id = await seed_bank(factory, questions=1, task=False)
    data = await start(client, topic_id)

    done = parse_sse((await send(client, data["id"])).text)[-1][1]

    assert done["taskAssigned"] is None and done["finished"] is True


async def test_replay_of_the_latest_answer_repeats_the_task(client, factory):
    topic_id = await seed_bank(factory, questions=1)
    data = await start(client, topic_id)
    cid = uuid.uuid4()
    await send(client, data["id"], client_message_id=cid)

    replay = parse_sse((await send(client, data["id"], client_message_id=cid)).text)[-1][1]

    assert replay["taskAssigned"]["title"] == "Сумма пар"


async def test_get_active_and_finish(client, factory):
    topic_id = await seed_bank(factory)
    data = await start(client, topic_id)
    cid = uuid.uuid4()
    await send(client, data["id"], client_message_id=cid)

    active = (await client.get("/api/interviews/active", headers=auth())).json()
    finished = await client.post(f"/api/interviews/{data['id']}/finish", headers=auth())
    again = await client.post(f"/api/interviews/{data['id']}/finish", headers=auth())

    assert active["id"] == data["id"] and len(active["messages"]) == 3
    assert finished.json() == {"id": data["id"], "status": "finished"}
    assert again.status_code == 200
    assert (await client.get("/api/interviews/active", headers=auth())).status_code == 404
    late = await send(client, data["id"])
    assert (late.status_code, late.json()["code"]) == (409, "session_not_active")
    replay = parse_sse((await send(client, data["id"], client_message_id=cid)).text)
    assert [name for name, _ in replay] == ["token", "done"]
    assert (await start(client, topic_id))["id"] != data["id"]


async def test_foreign_session_is_404(client, factory):
    topic_id = await seed_bank(factory)
    data = await start(client, topic_id)

    assert (await client.get(f"/api/interviews/{data['id']}", headers=auth("bob"))).status_code == 404
    assert (await send(client, data["id"], user="bob")).status_code == 404
    assert (await client.post(f"/api/interviews/{data['id']}/finish", headers=auth("bob"))).status_code == 404
    async with factory() as db:
        assert await db.scalar(select(func.count()).select_from(Message)) == 1


async def test_finish_during_the_answer_wins(client, factory, interviewer):
    topic_id = await seed_bank(factory, questions=1)
    data = await start(client, topic_id)

    async def finish() -> None:
        await client.post(f"/api/interviews/{data['id']}/finish", headers=auth())

    interviewer.during_reply = finish
    done = parse_sse((await send(client, data["id"])).text)[-1][1]  # would have assigned the task

    assert done["taskAssigned"] is None and done["finished"] is True
    session = await _session(factory, data["id"])
    assert session.status == "finished" and session.code_task_id is None
    assert (await _messages(factory, data["id"]))[-1].step is None


async def test_one_turn_at_a_time(client, factory):
    topic_id = await seed_bank(factory)
    data = await start(client, topic_id)
    async with factory() as db:
        session = await db.get(InterviewSession, uuid.UUID(data["id"]))
        session.reply_started_at = datetime.now(UTC) - timedelta(seconds=5)  # another answer is being written
        await db.commit()

    busy = parse_sse((await send(client, data["id"])).text)

    assert busy == [
        (
            "error",
            {"code": "reply_in_progress", "message": "Ответ на предыдущее сообщение ещё готовится", "retryable": True},
        )
    ]
    assert len(await _messages(factory, data["id"])) == 1  # the message was not taken
    async with factory() as db:
        session = await db.get(InterviewSession, uuid.UUID(data["id"]))
        session.reply_started_at = datetime.now(UTC) - timedelta(minutes=5)  # that answer died long ago
        await db.commit()
    assert parse_sse((await send(client, data["id"])).text)[-1][0] == "done"
    assert (await _session(factory, data["id"])).reply_started_at is None


async def test_failed_message_cannot_be_answered_after_the_interview_moved_on(client, factory, interviewer):
    topic_id = await seed_bank(factory)
    data = await start(client, topic_id)
    failed = uuid.uuid4()
    interviewer.fail_times = 1
    await send(client, data["id"], client_message_id=failed)
    await send(client, data["id"], content="другой ответ")

    resp = await send(client, data["id"], client_message_id=failed)

    assert (resp.status_code, resp.json()["code"]) == (409, "message_superseded")


async def test_replay_repeats_the_original_outcome(client, factory):
    topic_id = await seed_bank(factory, questions=1)
    data = await start(client, topic_id)
    assigning, closing = uuid.uuid4(), uuid.uuid4()
    await send(client, data["id"], client_message_id=assigning)
    await send(client, data["id"], client_message_id=closing)

    first = parse_sse((await send(client, data["id"], client_message_id=assigning)).text)[-1][1]
    last = parse_sse((await send(client, data["id"], client_message_id=closing)).text)[-1][1]

    assert first["taskAssigned"]["title"] == "Сумма пар" and first["finished"] is False
    assert last["taskAssigned"] is None and last["finished"] is True


async def test_dropped_stream_releases_the_turn(factory, interviewer):
    topic_id = await seed_bank(factory)
    async with factory() as db:
        session = InterviewSession(user_id=uuid.uuid4(), topic_id=topic_id, level="junior", questions_asked=1)
        db.add(session)
        await db.flush()
        user_message = Message(session_id=session.id, role="user", content="ответ", client_message_id=uuid.uuid4())
        db.add(user_message)
        lease = datetime.now(UTC)
        session.reply_started_at = lease
        await db.commit()
    turn = Turn(session_id=str(session.id), topic_title="Python: основы", level="junior", questions_asked=1)

    stream = interviews._answer(factory, interviewer, session, user_message.id, turn, set(), lease=lease)
    assert (await anext(stream)).startswith("event: token")
    await stream.aclose()  # the client hung up

    assert (await _session(factory, str(session.id))).reply_started_at is None
    assert [m.role for m in await _messages(factory, str(session.id))] == ["user"]
