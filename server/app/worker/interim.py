# Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
# Proprietary and confidential. See LICENSE in the project root.
"""Stand-ins used only while the sandbox and AI layer interfaces are not in main.

Behaviour follows the FakeSandbox / FakeChatProvider described in the contract (section 7).
Delete this module once app.infrastructure.sandbox and app.infrastructure.ai are merged.
"""

import asyncio
from typing import Any

_FAKE_TESTS = [
    {"name": "t1", "passed": True, "input": "[1, 2, 3], 4", "expected": "True", "actual": "True", "timeMs": 3, "error": None},
    {"name": "t2", "passed": True, "input": "[2, 2], 4", "expected": "True", "actual": "True", "timeMs": 2, "error": None},
    {"name": "t3", "passed": False, "input": "[], 1", "expected": "False", "actual": "None", "timeMs": 2, "error": None},
]
_FAKE_METRICS = {"lines": 3, "functions": 1, "loops": 1, "maxLoopDepth": 1, "recursion": False, "usesBuiltinsSort": False}


class InterimFakeSandbox:
    async def run(self, code: str, entry: str, tests: list[dict[str, Any]], limits: dict[str, Any]) -> dict[str, Any]:
        if "while True" in code:
            await asyncio.sleep(1)
            return {"verdict": "timeout", "passed": 0, "total": 3, "tests": [], "stdout": "", "stderr": "",
                    "truncated": False, "metrics": _FAKE_METRICS}
        return {"verdict": "failed", "passed": 2, "total": 3, "tests": _FAKE_TESTS, "stdout": "", "stderr": "",
                "truncated": False, "metrics": _FAKE_METRICS}


async def interim_review(task: Any, code: str, result: Any) -> dict[str, Any]:
    return {
        "summary": "Решение не обрабатывает пустой список.",
        "issues": [{"line": 1, "severity": "warning", "text": "Нет проверки пустого входа"}],
        "suggestions": ["Добавьте проверку пустого списка в начале функции"],
    }
