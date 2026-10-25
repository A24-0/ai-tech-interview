# Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
# Proprietary and confidential. See LICENSE in the project root.

from typing import Any

from app.domain.sandbox import CodeMetrics, CodeTaskDTO, RunResult, TestCaseResult
from app.infrastructure.ai.fake import FakeChatProvider
from app.infrastructure.ai.reviewer import build_facts, number_lines, review_code

TASK = CodeTaskDTO(id=1, title="Сумма пары", statement="Найдите пару с суммой k.", entry="solve")
CODE = "def solve(nums, k):\n    for x in nums:\n        pass\n    return False\n"


def run(verdict: str = "failed", stderr: str = "") -> RunResult:
    failed = TestCaseResult(name="t2", passed=False, input="[], 1", expected="False", actual="True", error=None)
    return RunResult(
        verdict=verdict,  # type: ignore[arg-type]
        passed=1,
        total=2,
        tests=[TestCaseResult(name="t1", passed=True), failed],
        stderr=stderr,
        metrics=CodeMetrics(lines=4, functions=1, loops=1, max_loop_depth=1),
    )


def provider_with(review: dict[str, Any]) -> FakeChatProvider:
    return FakeChatProvider(json_responses={"CodeReview": review})


def issue(line: int, severity: str = "warning", text: str = "замечание") -> dict[str, Any]:
    return {"line": line, "severity": severity, "text": text}


async def test_issue_with_line_out_of_range_is_dropped() -> None:
    provider = provider_with({"summary": "s", "issues": [issue(999), issue(0), issue(2)], "suggestions": []})

    review = await review_code(TASK, CODE, run(), provider)

    assert review is not None
    assert [i.line for i in review.issues] == [2]


async def test_passed_run_downgrades_error_to_warning() -> None:
    provider = provider_with({"summary": "s", "issues": [issue(1, "error"), issue(2, "info")], "suggestions": []})

    review = await review_code(TASK, CODE, run("passed"), provider)

    assert review is not None
    assert [i.severity for i in review.issues] == ["warning", "info"]


async def test_failed_run_keeps_error_severity() -> None:
    provider = provider_with({"summary": "s", "issues": [issue(1, "error")], "suggestions": []})

    review = await review_code(TASK, CODE, run("failed"), provider)

    assert review is not None
    assert review.issues[0].severity == "error"


async def test_issues_are_capped_and_text_truncated() -> None:
    issues = [issue(1, text="x" * 500) for _ in range(8)]
    provider = provider_with({"summary": "s", "issues": issues, "suggestions": []})

    review = await review_code(TASK, CODE, run(), provider)

    assert review is not None
    assert len(review.issues) == 5
    assert len(review.issues[0].text) == 300


async def test_returns_none_when_provider_is_unavailable() -> None:
    assert await review_code(TASK, CODE, run(), FakeChatProvider(fail=True)) is None


async def test_prompt_contains_numbered_code_and_facts() -> None:
    provider = provider_with({"summary": "s", "issues": [], "suggestions": []})

    await review_code(TASK, CODE, run(stderr="Traceback"), provider)

    call = provider.calls[0]
    assert call.purpose == "review"
    user = call.messages[1].content
    assert "  1| def solve(nums, k):" in user
    assert "Упал тест t2" in user
    assert "Traceback" in user
    assert "Сумма пары" in user


def test_number_lines_and_facts_helpers() -> None:
    assert number_lines("a\nb") == "  1| a\n  2| b"
    facts = build_facts(run(stderr="e" * 5000))
    assert "Тесты: 1 из 2" in facts
    assert facts.count("e") < 2100
