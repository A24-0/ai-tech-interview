# Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
# Proprietary and confidential. See LICENSE in the project root.
"""SubprocessSandbox: runner.py as a local process with rlimits (SANDBOX_BACKEND=subprocess).

Fallback from ADR-002 for development and tests without Docker. It limits time, CPU and
(on Linux) memory, but does NOT isolate network or the filesystem: never use it in production.
RLIMIT_NPROC is not set: it counts every process of the user, not only the run's.
"""

import asyncio
import os
import resource
import signal
import sys
from typing import Any

from app.domain.sandbox import RunResult, SandboxError
from app.infrastructure.sandbox.runner_io import (
    SandboxSettings,
    build_payload,
    find_result,
    memory_result,
    new_nonce,
    timeout_result,
)

RUNNER_ENV = {"PATH": "/usr/local/bin:/usr/bin:/bin", "LANG": "C.UTF-8"}
FILE_SIZE_LIMIT = 16 * 1024 * 1024


class SubprocessSandbox:
    def __init__(self, settings: SandboxSettings) -> None:
        self.settings = settings

    def _limit_resources(self) -> None:
        cpu_s = int(self.settings.hard_timeout_s) + 1
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_s, cpu_s))
        resource.setrlimit(resource.RLIMIT_FSIZE, (FILE_SIZE_LIMIT, FILE_SIZE_LIMIT))
        if sys.platform.startswith("linux"):
            memory = self.settings.memory_mb * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (memory, memory))

    async def run(
        self,
        code: str,
        entry: str,
        tests: list[dict[str, Any]],
        limits: dict[str, Any],
    ) -> RunResult:
        runner = self.settings.runner_path
        if not runner.is_file():
            raise SandboxError(f"runner.py not found at {runner}")
        nonce = new_nonce()
        payload = build_payload(code, entry, tests, limits, nonce)
        try:
            proc = await asyncio.create_subprocess_exec(
                sys.executable, "-I", str(runner),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=RUNNER_ENV,
                start_new_session=True,
                preexec_fn=self._limit_resources,
            )
        except OSError as exc:
            raise SandboxError(f"cannot start runner: {exc}") from exc

        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(payload), self.settings.hard_timeout_s)
        except TimeoutError:
            return timeout_result(tests, self.settings.timeout_s)
        finally:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass
            await proc.wait()

        result = find_result(stdout, nonce)
        if result is not None:
            return result
        if proc.returncode in (-signal.SIGKILL, -signal.SIGSEGV) or b"MemoryError" in stderr:
            return memory_result(tests)
        raise SandboxError(
            f"runner exited with code {proc.returncode} without a result: "
            f"{stderr[-2000:].decode('utf-8', errors='replace')}"
        )
