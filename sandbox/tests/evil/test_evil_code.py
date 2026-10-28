# Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
# Proprietary and confidential. See LICENSE in the project root.

import time

import docker
import pytest

from app.domain.sandbox import RunResult
from app.infrastructure.sandbox.docker_sandbox import CONTAINER_LABEL, DockerSandbox
from app.infrastructure.sandbox.runner_io import SandboxSettings

SETTINGS = SandboxSettings.from_env()
LIMITS = {"perTestTimeoutMs": 2000, "maxOutputBytes": 65536}
TESTS = [{"name": "t1", "args": [1, 2], "expected": 3}]
GOOD = "def solve(a, b):\n    return a + b\n"
MAX_SECONDS = 7


def _docker_unavailable() -> str | None:
    try:
        client = docker.from_env(timeout=5)
        client.ping()
        client.images.get(SETTINGS.image)
    except Exception as exc:  # noqa: BLE001 - any failure means "skip"
        return f"Docker or image {SETTINGS.image} unavailable: {exc}"
    return None


_REASON = _docker_unavailable()
pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.docker,
    pytest.mark.skipif(_REASON is not None, reason=_REASON or ""),
]


def leftover_containers() -> list[str]:
    client = docker.from_env()
    return [str(c.id) for c in client.containers.list(all=True, filters={"label": CONTAINER_LABEL})]


async def run_evil(code: str) -> tuple[RunResult, float]:
    started = time.monotonic()
    result = await DockerSandbox(SETTINGS).run(code, "solve", TESTS, LIMITS)
    return result, time.monotonic() - started


async def assert_contained(elapsed: float) -> None:
    assert elapsed <= MAX_SECONDS
    assert leftover_containers() == []
    after = await DockerSandbox(SETTINGS).run(GOOD, "solve", TESTS, LIMITS)
    assert after.verdict == "passed"


async def test_infinite_loop_times_out() -> None:
    result, elapsed = await run_evil("def solve(a, b):\n    while True:\n        pass\n")

    assert result.verdict == "timeout"
    await assert_contained(elapsed)


async def test_one_gigabyte_allocation_does_not_kill_the_host() -> None:
    result, elapsed = await run_evil("def solve(a, b):\n    return bytearray(1024 * 1024 * 1024)\n")

    assert result.verdict != "passed"
    await assert_contained(elapsed)


async def test_fork_bomb_is_stopped_by_pids_limit() -> None:
    code = (
        "import os\n"
        "def solve(a, b):\n"
        "    while True:\n"
        "        os.fork()\n"
    )

    result, elapsed = await run_evil(code)

    assert result.verdict != "passed"
    await assert_contained(elapsed)


async def test_network_request_fails_without_network() -> None:
    code = (
        "import urllib.request\n"
        "def solve(a, b):\n"
        "    return urllib.request.urlopen('http://example.com', timeout=2).status\n"
    )

    result, elapsed = await run_evil(code)

    assert result.verdict != "passed"
    await assert_contained(elapsed)
