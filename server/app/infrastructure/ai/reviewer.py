# Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
# Proprietary and confidential. See LICENSE in the project root.

import logging

from app.domain.ai import AIUnavailable, ChatMessage, ChatProvider, CodeIssue, CodeReview
from app.domain.sandbox import CodeTaskDTO, RunResult
from app.infrastructure.ai.prompt_loader import load_prompt

logger = logging.getLogger(__name__)

MAX_ISSUES = 5
MAX_ISSUE_TEXT = 300
MAX_STDERR = 2048


def number_lines(code: str) -> str:
    return "\n".join(f"{i:>3}| {line}" for i, line in enumerate(code.split("\n"), start=1))


def build_facts(result: RunResult) -> str:
    lines = [f"Вердикт: {result.verdict}", f"Тесты: {result.passed} из {result.total}"]
    for case in result.tests:
        if case.passed:
            continue
        details = [f"вход: {case.input}"]
        if case.expected is not None:
            details.append(f"ожидалось: {case.expected}")
        if case.actual is not None:
            details.append(f"получено: {case.actual}")
        if case.error:
            details.append(f"ошибка: {case.error}")
        lines.append(f"Упал тест {case.name}: " + "; ".join(details))
    if result.stderr:
        lines.append(f"stderr: {result.stderr[:MAX_STDERR]}")
    m = result.metrics
    lines.append(
        f"Метрики: строк {m.lines}, функций {m.functions}, циклов {m.loops}, "
        f"вложенность циклов {m.max_loop_depth}, рекурсия {'да' if m.recursion else 'нет'}, "
        f"встроенная сортировка {'да' if m.uses_builtins_sort else 'нет'}"
    )
    return "\n".join(lines)


def clean_review(review: CodeReview, line_count: int, verdict: str) -> CodeReview:
    issues: list[CodeIssue] = []
    for issue in review.issues:
        if not 1 <= issue.line <= line_count:
            continue
        severity = "warning" if verdict == "passed" and issue.severity == "error" else issue.severity
        issues.append(CodeIssue(line=issue.line, severity=severity, text=issue.text[:MAX_ISSUE_TEXT]))
    return CodeReview(summary=review.summary, issues=issues[:MAX_ISSUES], suggestions=review.suggestions)


async def review_code(
    task: CodeTaskDTO,
    code: str,
    result: RunResult,
    provider: ChatProvider,
) -> CodeReview | None:
    user = load_prompt("review_code_user").format(
        title=task.title,
        statement=task.statement,
        code=number_lines(code),
        facts=build_facts(result),
    )
    messages = [
        ChatMessage(role="system", content=load_prompt("review_code_system")),
        ChatMessage(role="user", content=user),
    ]
    try:
        review = await provider.complete_json(messages, CodeReview, purpose="review")
    except AIUnavailable as exc:
        logger.warning("code review failed: %s", exc)
        return None
    return clean_review(review, len(code.split("\n")), result.verdict)
