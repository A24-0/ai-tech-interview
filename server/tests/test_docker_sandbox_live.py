# Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
# Proprietary and confidential. See LICENSE in the project root.

import time

import docker
import pytest

from app.infrastructure.sandbox.docker_sandbox import CONTAINER_LABEL, DockerSandbox
from app.infrastructure.sandbox.runner_io import SandboxSettings

SETTINGS = SandboxSettings.from_env()
LIMITS = {"perTestTimeoutMs": 2000, "maxOutputBytes": 65536}
TESTS = [
    {"name": "t1", "args": [[1, 2, 3], 4], "expected": True},
    {"name": "t2", "args": [[], 1], "expected": False},
]
CORRECT = "def solve(nums, k):\n    return any(k - x in nums[i + 1:] for i, x in enumerate(nums))\n"


def _docker_unavailable() -> str | None:
    try:
        client = docker.from_env(timeout=5)
        client.ping()
        client.images.get(SETTINGS.image)
    except Exception as exc:  # noqa: BLE001 - any failure means "skip"
        return f"Docker or image {SETTINGS.image} unavailable: {exc}"
    return None


_REASON = _docker_unavailable()
pytestmark = [pytest.mark.docker, pytest.mark.skipif(_REASON is not None, reason=_REASON or "")]


def leftover_containers() -> list[str]:
    client = docker.from_env()
    return [str(c.id) for c in client.containers.list(all=True, filters={"label": CONTAINER_LABEL})]


async def test_correct_solution_passes() -> None:
    result = await DockerSandbox(SETTINGS).run(CORRECT, "solve", TESTS, LIMITS)

    assert result.verdict == "passed"


async def test_while_true_times_out_within_7_seconds() -> None:
    started = time.monotonic()

    result = await DockerSandbox(SETTINGS).run(
        "def solve(nums, k):\n    while True:\n        pass\n", "solve", TESTS, LIMITS
    )

    assert result.verdict == "timeout"
    assert time.monotonic() - started <= 7


async def test_no_containers_left_after_five_runs() -> None:
    sandbox = DockerSandbox(SETTINGS)
    for _ in range(5):
        await sandbox.run(CORRECT, "solve", TESTS, LIMITS)

    assert leftover_containers() == []
