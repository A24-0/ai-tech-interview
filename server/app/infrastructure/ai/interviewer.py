# Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
# Proprietary and confidential. See LICENSE in the project root.

import logging
import os
from collections.abc import AsyncIterator

from app.domain.ai import (
    AIUnavailable,
    AnswerCompleteness,
    ChatMessage,
    ChatProvider,
    InterviewContext,
    Level,
    NextStep,
    QuestionDTO,
)
from app.infrastructure.ai.prompt_loader import load_prompt

logger = logging.getLogger(__name__)

QUESTION_LIMITS: dict[Level, int] = {"junior": 3, "middle": 4, "senior": 5}
HISTORY_LIMIT = 10
DEFAULT_TOKEN_LIMIT = 40000
ANSWER_TAG = "candidate_answer"


def token_limit() -> int:
    return int(os.environ.get("SESSION_TOKEN_LIMIT", DEFAULT_TOKEN_LIMIT))


def wrap_answer(text: str) -> str:
    safe = text.replace(f"</{ANSWER_TAG}>", "").replace(f"<{ANSWER_TAG}>", "")
    return f"<{ANSWER_TAG}>\n{safe}\n</{ANSWER_TAG}>"


def last_answer(ctx: InterviewContext) -> str | None:
    if ctx.history and ctx.history[-1].role == "user":
        return ctx.history[-1].content
    return None


async def check_completeness(
    ctx: InterviewContext, answer: str, provider: ChatProvider
) -> AnswerCompleteness | None:
    question = ctx.current_question
    if question is None:
        return None
    user = load_prompt("completeness_user").format(
        question=question.text, expected=question.expected_answer, answer=answer.replace(f"</{ANSWER_TAG}>", "")
    )
    messages = [
        ChatMessage(role="system", content=load_prompt("completeness_system")),
        ChatMessage(role="user", content=user),
    ]
    try:
        return await provider.complete_json(
            messages, AnswerCompleteness, session_id=ctx.session_id, purpose="completeness"
        )
    except AIUnavailable as exc:
        logger.warning("completeness check failed, treating the answer as complete: %s", exc)
        return None


async def decide_next_step(ctx: InterviewContext, provider: ChatProvider) -> NextStep:
    if ctx.task_assigned:
        return "finish"
    if ctx.tokens_used >= token_limit():
        return "assign_task"
    after: NextStep = "assign_task" if ctx.questions_asked >= QUESTION_LIMITS[ctx.level] else "next_question"
    answer = last_answer(ctx)
    if answer is None or ctx.current_question is None or ctx.clarified_current:
        return after
    verdict = await check_completeness(ctx, answer, provider)
    if verdict is not None and not verdict.complete:
        return "clarify"
    return after


def build_messages(
    ctx: InterviewContext,
    step: NextStep,
    next_question: QuestionDTO | None = None,
    missing: str | None = None,
) -> list[ChatMessage]:
    if step == "next_question" and next_question is not None:
        instruction = load_prompt("step_next_question").format(question=next_question.text)
    elif step == "clarify" and ctx.current_question is not None:
        instruction = load_prompt("step_clarify").format(
            question=ctx.current_question.text, missing=missing or "деталей и примеров"
        )
    elif step in ("assign_task", "finish"):
        instruction = load_prompt(f"step_{step}")
    else:
        raise ValueError(f"step {step!r} needs a question")
    system = load_prompt("interviewer_system").format(level=ctx.level, topic=ctx.topic_title, step=instruction)
    history = [
        ChatMessage(role=m.role, content=wrap_answer(m.content) if m.role == "user" else m.content)
        for m in ctx.history
        if m.role != "system"
    ][-HISTORY_LIMIT:]
    return [ChatMessage(role="system", content=system), *history]


async def interviewer_turn(
    ctx: InterviewContext,
    step: NextStep,
    provider: ChatProvider,
    next_question: QuestionDTO | None = None,
) -> AsyncIterator[str]:
    missing: str | None = None
    answer = last_answer(ctx)
    if step == "clarify" and answer is not None:
        verdict = await check_completeness(ctx, answer, provider)
        missing = verdict.missing if verdict else None
    messages = build_messages(ctx, step, next_question, missing)
    async for chunk in provider.stream(messages, session_id=ctx.session_id, purpose="interviewer"):
        yield chunk
