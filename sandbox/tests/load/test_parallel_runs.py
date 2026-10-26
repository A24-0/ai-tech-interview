# Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
# Proprietary and confidential. See LICENSE in the project root.

import asyncio
import time

import docker
import pytest

from app.infrastructure.sandbox.docker_sandbox import CONTAINER_LABEL, DockerSandbox
from app.infrastructure.sandbox.runner_io import SandboxSettings

SETTINGS = SandboxSettings.from_env()
LIMITS = {"perTestTimeoutMs": 2000, "maxOutputBytes": 65536}
TESTS = [{"name": "t1", "args": [1, 2], "expected": 3}]
GOOD = "def solve(a, b):\n    return a + b\n"
LOOP = "def solve(a, b):\n    while True:\n        pass\n"
PARALLEL = 20
LOOPING = 5


def _docker_unavailable() -> str | None:
    try:
        client = docker.from_env(timeout=5)
        client.ping()
        client.images.get(SETTINGS.image)
    except Exception as exc:  # noqa: BLE001
        return f"Docker or image {SETTINGS.image} unavailable: {exc}"
    return None


_REASON = _docker_unavailable()
pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.docker,
    pytest.mark.skipif(_REASON is not None, reason=_REASON or ""),
]


async def test_twenty_parallel_runs_are_all_answered_and_cleaned_up() -> None:
    sandbox = DockerSandbox(SETTINGS)
    codes = [LOOP] * LOOPING + [GOOD] * (PARALLEL - LOOPING)
    started = time.monotonic()

    results = await asyncio.gather(*(sandbox.run(code, "solve", TESTS, LIMITS) for code in codes))

    elapsed = time.monotonic() - started
    assert [r.verdict for r in results] == ["timeout"] * LOOPING + ["passed"] * (PARALLEL - LOOPING)
    assert elapsed <= 30
    client = docker.from_env()
    assert client.containers.list(all=True, filters={"label": CONTAINER_LABEL}) == []
