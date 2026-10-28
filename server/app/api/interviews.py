# Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
# Proprietary and confidential. See LICENSE in the project root.
"""Interview endpoints, contract section 6.1 (S2-Y2, S2-Y3, S2-Y4, S3-Y2).

The streamed answer never holds a database transaction: the user's message is committed
before the model starts, the interviewer's answer is saved by a separate transaction.
"""

import json
import logging
import time
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

import anyio
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.deps import CurrentUserId, SessionFactory
from app.api.errors import ApiError
from app.api.interview_ai import Interviewer, NextStep, QuestionRef, Turn, get_interviewer
from app.api.schemas.interviews import (
    FinishOut,
    InterviewOut,
    MessageOut,
    SendMessageIn,
    StartInterviewIn,
    TaskOut,
)
from app.infrastructure.db.run_queue import cancel_runs_for_session
from app.domain.interview import DomainError, state_of
from app.infrastructure.db.models import CodeTask, InterviewSession, Message, Question
from app.infrastructure.db.repositories import SqlAlchemyInterviewRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/interviews", tags=["interviews"])

SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
AI_ERROR = {"code": "ai_unavailable", "message": "Модель временно недоступна", "retryable": True}
REPLY_IN_PROGRESS = {
    "code": "reply_in_progress",
    "message": "Ответ на предыдущее сообщение ещё готовится",
    "retryable": True,
}
REPLY_LEASE = timedelta(seconds=90)  # longer than a model answer with all its retries

InterviewerDep = Annotated[Interviewer, Depends(get_interviewer)]


def estimate_tokens(text: str) -> int:
    """About four characters per token: the providers do not report usage through stream()."""
    return max(1, len(text) // 4)


def _sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _question_ref(question: Question | None) -> QuestionRef | None:
    if question is None:
        return None
    return QuestionRef(id=question.id, text=question.text, expected_answer=question.expected_answer)


def _task_out(task: CodeTask | None) -> TaskOut | None:
    if task is None:
        return None
    return TaskOut(id=task.id, title=task.title, statement=task.statement, starter_code=task.starter_code)


def _task_json(task: CodeTask | None) -> dict[str, Any] | None:
    out = _task_out(task)
    return None if out is None else out.model_dump(by_alias=True)


def _domain_conflict(exc: DomainError) -> ApiError:
    return ApiError(409, exc.code, exc.message)


async def _own_session(
    repo: SqlAlchemyInterviewRepository, session_id: uuid.UUID, user_id: uuid.UUID, for_update: bool = False
) -> InterviewSession:
    session = await repo.get(session_id, user_id, for_update=for_update)
    if session is None:
        raise ApiError(404, "not_found", "Интервью не найдено")
    return session


async def _interview_out(repo: SqlAlchemyInterviewRepository, session: InterviewSession) -> InterviewOut:
    messages = await repo.list_messages(session.id)
    return InterviewOut(
        id=session.id,
        status=session.status,  # type: ignore[arg-type]
        topic_id=session.topic_id,
        level=session.level,  # type: ignore[arg-type]
        messages=[
            MessageOut(id=m.id, role=m.role, content=m.content, created_at=m.created_at)  # type: ignore[arg-type]
            for m in messages
        ],
        task=_task_out(await repo.get_task(session.code_task_id)),
    )


def _clarified(messages: list[Message], question_id: int | None) -> bool:
    """The candidate already answered the current question twice, so it was clarified once."""
    asked_at = max((m.id for m in messages if m.role == "assistant" and m.question_id == question_id), default=None)
    if question_id is None or asked_at is None:
        return False
    return sum(1 for m in messages if m.role == "user" and m.id > asked_at) >= 2


@router.post("", status_code=201, response_model=InterviewOut)
async def start_interview(
    body: StartInterviewIn, user_id: CurrentUserId, factory: SessionFactory, interviewer: InterviewerDep
) -> InterviewOut:
    async with factory() as db:
        repo = SqlAlchemyInterviewRepository(db)
        topic = await repo.get_topic(body.topic_id)
        if topic is None:
            raise ApiError(404, "topic_not_found", "Тема не найдена")
        active = await repo.get_active_for_user(user_id)
        if active is not None:
            raise ApiError(409, "active_session_exists", "Уже есть активное интервью", detail=str(active.id))
        question = await repo.pick_question(topic.id, body.level)
        if question is None:
            raise ApiError(409, "no_questions", "В банке нет вопросов для этой темы и уровня")

    session_id = uuid.uuid4()
    turn = Turn(session_id=str(session_id), topic_title=topic.title, level=body.level)
    started = time.monotonic()
    try:
        text = "".join([chunk async for chunk in interviewer.reply(turn, "next_question", _question_ref(question))])
    except Exception:
        logger.exception("interviewer failed to open session %s", session_id)
        raise ApiError(503, "ai_unavailable", "Модель временно недоступна") from None
    tokens_out = estimate_tokens(text)

    async with factory() as db:
        repo = SqlAlchemyInterviewRepository(db)
        session = InterviewSession(
            id=session_id,
            user_id=user_id,
            topic_id=topic.id,
            level=body.level,
            current_question_id=question.id,
            questions_asked=1,
            tokens_used=tokens_out,
        )
        repo.add(session)
        repo.add_message(
            Message(
                session_id=session_id,
                role="assistant",
                content=text,
                question_id=question.id,
                step="next_question",
                tokens_out=tokens_out,
                duration_ms=int((time.monotonic() - started) * 1000),
            )
        )
        try:
            await db.commit()
        except IntegrityError:  # another start of the same user won the race
            await db.rollback()
            active = await repo.get_active_for_user(user_id)
            raise ApiError(
                409, "active_session_exists", "Уже есть активное интервью", detail=str(active.id) if active else None
            ) from None
        return await _interview_out(repo, session)


@router.get("/active", response_model=InterviewOut)
async def get_active(user_id: CurrentUserId, factory: SessionFactory) -> InterviewOut:
    async with factory() as db:
        repo = SqlAlchemyInterviewRepository(db)
        active = await repo.get_active_for_user(user_id)
        if active is None:
            raise ApiError(404, "not_found", "Активного интервью нет")
        return await _interview_out(repo, active)


@router.get("/{session_id}", response_model=InterviewOut)
async def get_interview(session_id: uuid.UUID, user_id: CurrentUserId, factory: SessionFactory) -> InterviewOut:
    async with factory() as db:
        repo = SqlAlchemyInterviewRepository(db)
        return await _interview_out(repo, await _own_session(repo, session_id, user_id))


@router.post("/{session_id}/messages")
async def send_message(
    session_id: uuid.UUID,
    body: SendMessageIn,
    user_id: CurrentUserId,
    factory: SessionFactory,
    interviewer: InterviewerDep,
) -> StreamingResponse:
    async with factory() as db:
        repo = SqlAlchemyInterviewRepository(db)
        # the row lock makes two requests of one session take their turns one after another
        session = await _own_session(repo, session_id, user_id, for_update=True)
        user_message = await repo.find_message_by_client_id(session.id, body.client_message_id)
        reply = await repo.find_reply(user_message.id) if user_message is not None else None
        if user_message is not None and reply is not None:
            return _stream(await _replay(repo, session, user_message, reply))

        try:
            state_of(session.status).add_message()
        except DomainError as exc:
            raise _domain_conflict(exc) from None

        now = datetime.now(UTC)
        started = session.reply_started_at
        if started is not None and now - _aware(started) < REPLY_LEASE:
            # another message, or this one sent twice, is being answered right now
            return _stream(_events([("error", REPLY_IN_PROGRESS)]))
        if user_message is None:
            user_message = Message(
                session_id=session.id, role="user", content=body.content, client_message_id=body.client_message_id
            )
            repo.add_message(user_message)
        elif user_message.id != await repo.latest_user_message_id(session.id):
            # a failed message retried after the interview moved on: its turn is gone
            raise ApiError(409, "message_superseded", "Интервью уже ушло дальше этого сообщения")
        session.reply_started_at = now
        await db.commit()

        messages = await repo.list_messages(session.id)
        current = await repo.get_question(session.current_question_id)
        topic = await repo.get_topic(session.topic_id)
        turn = Turn(
            session_id=str(session.id),
            topic_title=topic.title if topic else "",
            level=session.level,
            current_question=_question_ref(current),
            questions_asked=session.questions_asked,
            clarified_current=_clarified(messages, session.current_question_id),
            task_assigned=session.code_task_id is not None,
            history=[(m.role, m.content) for m in messages],
            tokens_used=session.tokens_used,
        )
        asked = {m.question_id for m in messages if m.question_id is not None}

    return _stream(_answer(factory, interviewer, session, user_message.id, turn, asked, lease=now))


def _stream(events: AsyncIterator[str]) -> StreamingResponse:
    return StreamingResponse(events, media_type="text/event-stream", headers=SSE_HEADERS)


def _aware(moment: datetime) -> datetime:
    return moment if moment.tzinfo is not None else moment.replace(tzinfo=UTC)  # SQLite drops the zone


async def _replay(
    repo: SqlAlchemyInterviewRepository, session: InterviewSession, user_message: Message, reply: Message
) -> AsyncIterator[str]:
    """A repeated clientMessageId: the saved answer as one token and the same outcome, nothing is created."""
    messages = await repo.list_messages(session.id)
    task = await repo.get_task(session.code_task_id) if reply.step == "assign_task" else None
    closed_after = session.status != "active" and messages[-1].id == reply.id
    done = {
        "messageId": reply.id,
        "userMessageId": user_message.id,
        "taskAssigned": _task_json(task),
        "finished": reply.step == "finish" or closed_after,
    }
    return _events([("token", {"text": reply.content}), ("done", done)])


async def _events(events: list[tuple[str, dict[str, Any]]]) -> AsyncIterator[str]:
    for name, data in events:
        yield _sse(name, data)


async def _release_turn(factory: async_sessionmaker[AsyncSession], session_id: uuid.UUID, lease: datetime) -> None:
    """Lets the next request in after a failed or dropped answer (only our own lease)."""
    async with factory() as db:
        await db.execute(
            update(InterviewSession)
            .where(InterviewSession.id == session_id, InterviewSession.reply_started_at == lease)
            .values(reply_started_at=None)
        )
        await db.commit()


async def _answer(
    factory: async_sessionmaker[AsyncSession],
    interviewer: Interviewer,
    session: InterviewSession,
    user_message_id: int,
    turn: Turn,
    asked: set[int],
    lease: datetime,
) -> AsyncIterator[str]:
    started = time.monotonic()
    saved = False
    try:
        next_question: Question | None = None
        task: CodeTask | None = None
        parts: list[str] = []
        try:
            step: NextStep = await interviewer.decide_next_step(turn)
            async with factory() as db:
                repo = SqlAlchemyInterviewRepository(db)
                if step == "next_question":
                    next_question = await repo.pick_question(session.topic_id, session.level, asked)
                    if next_question is None:  # the bank of this level is used up
                        step = "assign_task"
                if step == "assign_task":
                    task = None if turn.task_assigned else await repo.pick_task(session.topic_id, session.level)
                    if task is None:
                        step = "finish"
            async for chunk in interviewer.reply(turn, step, _question_ref(next_question)):
                parts.append(chunk)
                yield _sse("token", {"text": chunk})
        except Exception:
            logger.exception("interviewer failed in session %s", session.id)
            yield _sse("error", AI_ERROR)  # the user's message stays; the same request retries
            return

        text = "".join(parts)
        tokens_in = estimate_tokens("".join(content for _, content in turn.history))
        tokens_out = estimate_tokens(text)
        changes: dict[str, Any] = {
            "last_activity_at": datetime.now(UTC),
            "tokens_used": InterviewSession.tokens_used + tokens_in + tokens_out,
            "reply_started_at": None,
        }
        if next_question is not None:
            changes["current_question_id"] = next_question.id
            changes["questions_asked"] = InterviewSession.questions_asked + 1
        if task is not None:
            state_of(session.status).assign_task(has_task=False)
            changes["code_task_id"] = task.id
        if step == "finish":
            changes["status"] = state_of(session.status).finish()
            changes["finished_at"] = datetime.now(UTC)
        async with factory() as db:
            repo = SqlAlchemyInterviewRepository(db)
            result = await db.execute(
                update(InterviewSession)
                .where(InterviewSession.id == session.id, InterviewSession.status == "active")
                .values(**changes)
            )
            closed_meanwhile = result.rowcount == 0  # POST /finish came while the interviewer was talking
            if closed_meanwhile:
                task = None
            reply = Message(
                session_id=session.id,
                role="assistant",
                content=text,
                reply_to_id=user_message_id,
                step=None if closed_meanwhile else step,
                question_id=next_question.id if next_question else None,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                duration_ms=int((time.monotonic() - started) * 1000),
            )
            repo.add_message(reply)
            try:
                await db.commit()
            except IntegrityError:  # an answer to this message was saved by a request whose lease expired
                await db.rollback()
                reply = await repo.find_reply(user_message_id)
                if reply is None:
                    raise
                task, closed_meanwhile = None, False
        saved = True
        finished = step == "finish" or closed_meanwhile
        if finished:
            await _cancel_runs(factory, session.id)
        yield _sse(
            "done",
            {
                "messageId": reply.id,
                "userMessageId": user_message_id,
                "taskAssigned": _task_json(task),
                "finished": finished,
            },
        )
    finally:
        if not saved:
            with anyio.CancelScope(shield=True):  # also runs when the client hung up mid-stream
                await _release_turn(factory, session.id, lease)


async def _cancel_runs(factory: async_sessionmaker[AsyncSession], session_id: uuid.UUID) -> None:
    async with factory() as db:
        await cancel_runs_for_session(db, session_id)
        await db.commit()


@router.post("/{session_id}/finish", response_model=FinishOut)
async def finish_interview(session_id: uuid.UUID, user_id: CurrentUserId, factory: SessionFactory) -> FinishOut:
    async with factory() as db:
        repo = SqlAlchemyInterviewRepository(db)
        session = await _own_session(repo, session_id, user_id)
        try:
            status = state_of(session.status).finish()
        except DomainError as exc:
            raise _domain_conflict(exc) from None
        if session.status != status:
            session.status = status
            session.finished_at = datetime.now(UTC)
            await db.commit()
    await _cancel_runs(factory, session_id)
    return FinishOut(id=session_id, status="finished")
