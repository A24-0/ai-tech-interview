# Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
# Proprietary and confidential. See LICENSE in the project root.

import asyncio
import logging
from typing import Any

import docker
import requests
from docker.errors import DockerException, NotFound
from docker.models.containers import Container

from app.domain.sandbox import RunResult, SandboxError
from app.infrastructure.sandbox.runner_io import (
    OOM_EXIT_CODE,
    SandboxSettings,
    build_payload,
    find_result,
    memory_result,
    new_nonce,
    timeout_result,
)

logger = logging.getLogger(__name__)

CONTAINER_LABEL = "ai-tech-interview.sandbox"


class DockerSandbox:
    def __init__(self, settings: SandboxSettings, client: docker.DockerClient | None = None) -> None:
        self.settings = settings
        self._client = client

    @property
    def client(self) -> docker.DockerClient:
        if self._client is None:
            timeout = int(self.settings.hard_timeout_s) + 10
            self._client = (
                docker.DockerClient(base_url=self.settings.docker_host, timeout=timeout)
                if self.settings.docker_host
                else docker.from_env(timeout=timeout)
            )
        return self._client

    async def run(
        self,
        code: str,
        entry: str,
        tests: list[dict[str, Any]],
        limits: dict[str, Any],
    ) -> RunResult:
        return await asyncio.to_thread(self._run_sync, code, entry, tests, limits)

    def container_options(self) -> dict[str, Any]:
        s = self.settings
        return {
            "image": s.image,
            "stdin_open": True,
            "network_disabled": True,
            "mem_limit": f"{s.memory_mb}m",
            "memswap_limit": f"{s.memory_mb}m",
            "nano_cpus": int(s.cpus * 1e9),
            "pids_limit": s.pids,
            "read_only": True,
            "tmpfs": {"/tmp": "size=16m,mode=1777"},
            "cap_drop": ["ALL"],
            "security_opt": ["no-new-privileges"],
            "environment": {},
            "labels": {CONTAINER_LABEL: "1"},
        }

    def _run_sync(self, code: str, entry: str, tests: list[dict[str, Any]], limits: dict[str, Any]) -> RunResult:
        nonce = new_nonce()
        payload = build_payload(code, entry, tests, limits, nonce)
        container: Container | None = None
        try:
            container = self.client.containers.create(**self.container_options())
            self._start_with_stdin(container, payload)
            try:
                status = container.wait(timeout=self.settings.hard_timeout_s)
            except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError):
                self._kill(container)
                return timeout_result(tests, self.settings.timeout_s)

            exit_code = int(status.get("StatusCode", -1))
            stdout = container.logs(stdout=True, stderr=False)
            result = find_result(stdout, nonce)
            if result is not None:
                return result
            if exit_code == OOM_EXIT_CODE or self._oom_killed(container):
                return memory_result(tests)
            stderr = container.logs(stdout=False, stderr=True)[-2000:].decode("utf-8", errors="replace")
            raise SandboxError(f"runner exited with code {exit_code} without a result: {stderr}")
        except DockerException as exc:
            raise SandboxError(f"docker error: {exc}") from exc
        finally:
            if container is not None:
                self._remove(container)

    def _start_with_stdin(self, container: Container, payload: bytes) -> None:
        if container.id is None:
            raise SandboxError("docker returned a container without id")
        sock = self.client.api.attach_socket(container.id, params={"stdin": 1, "stream": 1})
        raw = getattr(sock, "_sock", sock)
        try:
            container.start()
            raw.sendall(payload)
        finally:
            # create() without detach makes the SDK set StdinOnce, so closing this attach gives EOF.
            raw.close()
            if raw is not sock:
                sock.close()

    @staticmethod
    def _oom_killed(container: Container) -> bool:
        try:
            container.reload()
            return bool(container.attrs.get("State", {}).get("OOMKilled"))
        except DockerException:
            return False

    @staticmethod
    def _kill(container: Container) -> None:
        try:
            container.kill()
        except DockerException as exc:
            logger.warning("sandbox container kill failed: %s", exc)

    @staticmethod
    def _remove(container: Container) -> None:
        try:
            container.remove(force=True)
        except NotFound:
            pass
        except DockerException as exc:
            logger.error("sandbox container %s was not removed: %s", container.id, exc)
