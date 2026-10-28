# Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
# Proprietary and confidential. See LICENSE in the project root.

import time
from pathlib import Path

import pytest

from app.domain.sandbox import SandboxError
from app.infrastructure.sandbox.runner_io import SandboxSettings
from app.infrastructure.sandbox.subprocess_sandbox import SubprocessSandbox

LIMITS = {"perTestTimeoutMs": 2000, "maxOutputBytes": 65536}
TESTS = [
    {"name": "t1", "args": [[1, 2, 3], 4], "expected": True},
    {"name": "t2", "args": [[], 1], "expected": False},
]
CORRECT = "def solve(nums, k):\n    return any(k - x in nums[i + 1:] for i, x in enumerate(nums))\n"


@pytest.fixture
def sandbox() -> SubprocessSandbox:
    return SubprocessSandbox(SandboxSettings())


async def test_correct_solution_passes(sandbox: SubprocessSandbox) -> None:
    result = await sandbox.run(CORRECT, "solve", TESTS, LIMITS)

    assert result.verdict == "passed"
    assert (result.passed, result.total) == (2, 2)


async def test_wrong_solution_fails(sandbox: SubprocessSandbox) -> None:
    result = await sandbox.run("def solve(nums, k):\n    return True\n", "solve", TESTS, LIMITS)

    assert result.verdict == "failed"
    assert result.tests[1].actual == "True"


async def test_while_true_is_timeout_within_7_seconds(sandbox: SubprocessSandbox) -> None:
    started = time.monotonic()

    result = await sandbox.run("def solve(nums, k):\n    while True:\n        pass\n", "solve", TESTS, LIMITS)

    assert result.verdict == "timeout"
    assert time.monotonic() - started <= 7


async def test_hard_timeout_kills_runner() -> None:
    sandbox = SubprocessSandbox(SandboxSettings(timeout_s=1))
    limits = {**LIMITS, "perTestTimeoutMs": 30_000}

    started = time.monotonic()
    result = await sandbox.run("import time\ndef solve(nums, k):\n    time.sleep(20)\n", "solve", TESTS, limits)

    assert result.verdict == "timeout"
    assert time.monotonic() - started < 5
    assert result.total == 2


async def test_environment_secrets_do_not_reach_user_code(
    sandbox: SubprocessSandbox, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LLM_API_KEY", "secret-key")
    monkeypatch.setenv("DATABASE_URL", "postgresql://secret")
    code = "import os\ndef solve():\n    return sorted(os.environ)\n"

    result = await sandbox.run(code, "solve", [{"name": "env", "args": [], "expected": []}], LIMITS)

    assert result.tests[0].actual is not None
    assert "LLM_API_KEY" not in result.tests[0].actual
    assert "DATABASE_URL" not in result.tests[0].actual


async def test_missing_runner_is_sandbox_error(tmp_path: Path) -> None:
    sandbox = SubprocessSandbox(SandboxSettings(runner_path=tmp_path / "nope.py"))

    with pytest.raises(SandboxError):
        await sandbox.run(CORRECT, "solve", TESTS, LIMITS)


async def test_runner_without_result_line_is_sandbox_error(tmp_path: Path) -> None:
    broken = tmp_path / "runner.py"
    broken.write_text("import sys\nprint('garbage')\nsys.exit(3)\n")
    sandbox = SubprocessSandbox(SandboxSettings(runner_path=broken))

    with pytest.raises(SandboxError, match="code 3"):
        await sandbox.run(CORRECT, "solve", TESTS, LIMITS)
