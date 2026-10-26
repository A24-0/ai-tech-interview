# Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
# Proprietary and confidential. See LICENSE in the project root.

import time
from typing import Any

import pytest

from app.domain.sandbox import RunResult
from app.infrastructure.sandbox.docker_sandbox import DockerSandbox
from test_evil_code import LIMITS, MAX_SECONDS, SETTINGS, assert_contained, pytestmark  # noqa: F401


async def run_with(code: str, expected: Any) -> tuple[RunResult, float]:
    tests = [{"name": "t1", "args": [1, 2], "expected": expected}]
    started = time.monotonic()
    result = await DockerSandbox(SETTINGS).run(code, "solve", tests, LIMITS)
    return result, time.monotonic() - started


async def test_cannot_write_to_root_filesystem() -> None:
    code = "def solve(a, b):\n    open('/pwned', 'w').write('x')\n    return 0\n"

    result, elapsed = await run_with(code, 0)

    assert result.verdict != "passed"
    assert "Read-only" in (result.tests[0].error or "")
    await assert_contained(elapsed)


async def test_tmp_is_writable_but_limited_in_size() -> None:
    code = "def solve(a, b):\n    open('/tmp/f', 'w').write('x' * (64 * 1024 * 1024))\n    return 0\n"

    result, elapsed = await run_with(code, 0)

    assert result.verdict != "passed"
    await assert_contained(elapsed)


async def test_etc_shadow_is_not_readable() -> None:
    code = "def solve(a, b):\n    return open('/etc/shadow').read()\n"

    result, elapsed = await run_with(code, "")

    assert result.verdict != "passed"
    assert "Permission denied" in (result.tests[0].error or "")
    await assert_contained(elapsed)


async def test_ten_megabytes_of_output_is_truncated() -> None:
    code = "def solve(a, b):\n    print('x' * (10 * 1024 * 1024))\n    return 3\n"

    result, elapsed = await run_with(code, 3)

    assert result.truncated is True
    assert len(result.stdout) <= LIMITS["maxOutputBytes"]
    await assert_contained(elapsed)


async def test_host_secrets_are_not_visible_inside(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_API_KEY", "sk-test-not-a-real-key")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@db/app")
    code = (
        "import os\n"
        "def solve(a, b):\n"
        "    return [k for k in ('LLM_API_KEY', 'DATABASE_URL') if k in os.environ]\n"
    )

    result, elapsed = await run_with(code, [])

    assert result.verdict == "passed"
    await assert_contained(elapsed)
