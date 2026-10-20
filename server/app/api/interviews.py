# Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
# Proprietary and confidential. See LICENSE in the project root.
"""Interview endpoints (stubs on in-memory storage), contract section 6.1."""

import json
import uuid
from collections.abc import AsyncIterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.api.deps import CurrentUserId
from app.api.errors import ApiError
from app.api.schemas.interviews import (
    FinishOut,
    InterviewOut,
    SendMessageIn,
    StartInterviewIn,
)
from app.api.stub_store import STUB_TASK, StubReply, StubSession, store
from app.infrastructure.ai.fake import FakeChatProvider

router = APIRouter(prefix="/interviews", tags=["interviews"])

SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
TASK_AFTER_USER_MESSAGES = 2


def _out(session: StubSession) -> InterviewOut:
    return InterviewOut(
        id=session.id,
        status=session.status,  # type: ignore[arg-type]
        topic_id=session.topic_id,
        level=session.level,
        messages=session.messages,
        task=session.task,
    )


def _own_session(session_id: uuid.UUID, user_id: uuid.UUID) -> StubSession:
    session = store.sessions.get(session_id)
    if session is None or session.user_id != user_id:
        raise ApiError(404, "not_found", "Интервью не найдено")
    return session


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("", status_code=201, response_model=InterviewOut)
async def start_interview(body: StartInterviewIn, user_id: CurrentUserId) -> InterviewOut:
    active = store.active_for_user(user_id)
    if active is not None:
        raise ApiError(
            409,
            "active_session_exists",
            "Уже есть активное интервью",
            detail=str(active.id),
        )
    return _out(store.create_session(user_id, body.topic_id, body.level))


@router.get("/active", response_model=InterviewOut)
async def get_active(user_id: CurrentUserId) -> InterviewOut:
    active = store.active_for_user(user_id)
    if active is None:
        raise ApiError(404, "not_found", "Активного интервью нет")
    return _out(active)


@router.get("/{session_id}", response_model=InterviewOut)
async def get_interview(session_id: uuid.UUID, user_id: CurrentUserId) -> InterviewOut:
    return _out(_own_session(session_id, user_id))


@router.post("/{session_id}/messages")
async def send_message(
    session_id: uuid.UUID, body: SendMessageIn, user_id: CurrentUserId
) -> StreamingResponse:
    session = _own_session(session_id, user_id)
    replay = session.replies.get(body.client_message_id)
    if replay is None and session.status != "active":
        raise ApiError(409, "session_not_active", "Интервью уже завершено")

    async def events() -> AsyncIterator[str]:
        if replay is not None:
            yield _sse("token", {"text": replay.text})
            yield _sse(
                "done",
                {
                    "messageId": replay.reply_message_id,
                    "userMessageId": replay.user_message_id,
                    "taskAssigned": None,
                    "finished": False,
                },
            )
            return

        user_message = session.add_message("user", body.content)
        parts: list[str] = []
        try:
            async for chunk in FakeChatProvider().stream(str(session.id)):
                parts.append(chunk)
                yield _sse("token", {"text": chunk})
        except Exception:
            yield _sse(
                "error",
                {"code": "ai_unavailable", "message": "Модель временно недоступна", "retryable": True},
            )
            return

        reply = session.add_message("assistant", "".join(parts))
        session.replies[body.client_message_id] = StubReply(user_message.id, reply.id, reply.content)
        task_assigned = None
        if session.task is None and session.user_messages_count() >= TASK_AFTER_USER_MESSAGES:
            session.task = STUB_TASK
            task_assigned = STUB_TASK.model_dump(by_alias=True)
        yield _sse(
            "done",
            {
                "messageId": reply.id,
                "userMessageId": user_message.id,
                "taskAssigned": task_assigned,
                "finished": False,
            },
        )

    return StreamingResponse(events(), media_type="text/event-stream", headers=SSE_HEADERS)


@router.post("/{session_id}/finish", response_model=FinishOut)
async def finish_interview(session_id: uuid.UUID, user_id: CurrentUserId) -> FinishOut:
    session = _own_session(session_id, user_id)
    session.status = "finished"
    for run in store.runs_for_session(session.id):
        run.cancelled = True
    return FinishOut(id=session.id, status="finished")
