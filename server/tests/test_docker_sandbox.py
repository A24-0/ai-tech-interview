# Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
# Proprietary and confidential. See LICENSE in the project root.

import json
from typing import Any

import pytest
import requests
from docker.errors import APIError

from app.domain.sandbox import SandboxError
from app.infrastructure.sandbox.docker_sandbox import CONTAINER_LABEL, DockerSandbox
from app.infrastructure.sandbox.runner_io import MEMORY_EXCEEDED, SandboxSettings

LIMITS = {"perTestTimeoutMs": 2000, "maxOutputBytes": 65536}
TESTS = [{"name": "t1", "args": [1], "expected": 1}]
PASSED = {"verdict": "passed", "passed": 1, "total": 1}


class StubSocket:
    def __init__(self) -> None:
        self.sent = b""
        self.closed = False

    def sendall(self, data: bytes) -> None:
        self.sent += data

    def close(self) -> None:
        self.closed = True


class StubContainer:
    id = "c0ffee"

    def __init__(self, sock: StubSocket, *, wait: Any, stdout: Any = None, oom: bool = False) -> None:
        self.sock = sock
        self._wait = wait
        self._stdout = stdout
        self.attrs = {"State": {"OOMKilled": oom}}
        self.started = self.killed = self.removed = False

    def start(self) -> None:
        self.started = True

    def wait(self, timeout: float) -> dict[str, int]:
        self.wait_timeout = timeout
        if isinstance(self._wait, Exception):
            raise self._wait
        return {"StatusCode": self._wait}

    def logs(self, stdout: bool, stderr: bool) -> bytes:
        if not stdout:
            return b"runner stderr"
        nonce = json.loads(self.sock.sent)["nonce"]
        if self._stdout is None:
            return b"user output\n"
        return f"user output\n{nonce}{json.dumps(self._stdout)}\n".encode()

    def reload(self) -> None:
        pass

    def kill(self) -> None:
        self.killed = True

    def remove(self, force: bool) -> None:
        assert force
        self.removed = True


class StubClient:
    def __init__(self, *, create_error: Exception | None = None, **container: Any) -> None:
        self.sock = StubSocket()
        self.container = StubContainer(self.sock, **container)
        self.create_error = create_error
        self.create_kwargs: dict[str, Any] = {}
        self.containers = self
        self.api = self

    def create(self, **kwargs: Any) -> StubContainer:
        if self.create_error:
            raise self.create_error
        self.create_kwargs = kwargs
        return self.container

    def attach_socket(self, container_id: str, params: dict[str, int]) -> StubSocket:
        assert container_id == self.container.id
        assert params == {"stdin": 1, "stream": 1}
        return self.sock


def make(client: StubClient, **settings: Any) -> DockerSandbox:
    return DockerSandbox(SandboxSettings(**settings), client=client)  # type: ignore[arg-type]


async def test_success_parses_result_and_removes_container() -> None:
    client = StubClient(wait=0, stdout=PASSED)

    result = await make(client).run("def solve(x):\n    return x\n", "solve", TESTS, LIMITS)

    assert result.verdict == "passed"
    payload = json.loads(client.sock.sent)
    assert payload["code"].startswith("def solve") and payload["limits"] == LIMITS
    assert client.sock.closed and client.container.started and client.container.removed


async def test_container_options_follow_adr_002() -> None:
    client = StubClient(wait=0, stdout=PASSED)

    await make(client, image="img:1", memory_mb=128, cpus=0.5, pids=32).run("x = 1", "solve", TESTS, LIMITS)

    assert client.create_kwargs == {
        "image": "img:1",
        "stdin_open": True,
        "network_disabled": True,
        "mem_limit": "128m",
        "memswap_limit": "128m",
        "nano_cpus": 500_000_000,
        "pids_limit": 32,
        "read_only": True,
        "tmpfs": {"/tmp": "size=16m,mode=1777"},
        "cap_drop": ["ALL"],
        "security_opt": ["no-new-privileges"],
        "environment": {},
        "labels": {CONTAINER_LABEL: "1"},
    }


async def test_wait_timeout_kills_and_removes() -> None:
    client = StubClient(wait=requests.exceptions.ReadTimeout())

    result = await make(client, timeout_s=5).run("while True: pass", "solve", TESTS, LIMITS)

    assert result.verdict == "timeout"
    assert client.container.wait_timeout == 6
    assert client.container.killed and client.container.removed


async def test_oom_without_result_is_memory_error() -> None:
    client = StubClient(wait=137)

    result = await make(client).run("x = 'a' * 10**10", "solve", TESTS, LIMITS)

    assert (result.verdict, result.stderr) == ("error", MEMORY_EXCEEDED)
    assert client.container.removed


async def test_oom_flag_without_137_is_memory_error() -> None:
    client = StubClient(wait=1, oom=True)

    result = await make(client).run("x = 1", "solve", TESTS, LIMITS)

    assert result.stderr == MEMORY_EXCEEDED


async def test_no_result_line_is_sandbox_error_and_removes() -> None:
    client = StubClient(wait=1)

    with pytest.raises(SandboxError, match="code 1"):
        await make(client).run("x = 1", "solve", TESTS, LIMITS)
    assert client.container.removed


async def test_docker_failure_is_sandbox_error() -> None:
    client = StubClient(wait=0, create_error=APIError("no such image"))

    with pytest.raises(SandboxError, match="docker error"):
        await make(client).run("x = 1", "solve", TESTS, LIMITS)
