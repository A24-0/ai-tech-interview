# Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
# Proprietary and confidential. See LICENSE in the project root.
"""Shared by sandbox backends: settings, runner.py stdin payload and stdout parsing (contract 6.5)."""

import json
import os
import secrets
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from app.domain.sandbox import RunResult, SandboxError, TestCaseResult

MEMORY_EXCEEDED = "Превышен лимит памяти"
TIME_EXCEEDED = "Превышен общий лимит времени"
OOM_EXIT_CODE = 137

_DEFAULT_RUNNER = Path(__file__).resolve().parents[4] / "sandbox" / "runner.py"


@dataclass(frozen=True)
class SandboxSettings:
    image: str = "interview-sandbox:latest"
    timeout_s: float = 5.0
    memory_mb: int = 256
    cpus: float = 1.0
    pids: int = 64
    docker_host: str | None = None
    runner_path: Path = _DEFAULT_RUNNER

    @property
    def hard_timeout_s(self) -> float:
        """Overall wall-clock budget before the run is killed: SANDBOX_TIMEOUT_S + 1 s."""
        return self.timeout_s + 1

    @classmethod
    def from_env(cls) -> "SandboxSettings":
        env = os.environ
        return cls(
            image=env.get("SANDBOX_IMAGE", cls.image),
            timeout_s=float(env.get("SANDBOX_TIMEOUT_S", cls.timeout_s)),
            memory_mb=int(env.get("SANDBOX_MEMORY_MB", cls.memory_mb)),
            cpus=float(env.get("SANDBOX_CPUS", cls.cpus)),
            pids=int(env.get("SANDBOX_PIDS", cls.pids)),
            docker_host=env.get("DOCKER_HOST") or None,
            runner_path=Path(env.get("SANDBOX_RUNNER_PATH", str(_DEFAULT_RUNNER))),
        )


def new_nonce() -> str:
    return secrets.token_hex(16)


def build_payload(code: str, entry: str, tests: list[dict[str, Any]], limits: dict[str, Any], nonce: str) -> bytes:
    return json.dumps(
        {"code": code, "entry": entry, "tests": tests, "limits": limits, "nonce": nonce},
        ensure_ascii=False,
    ).encode()


def find_result(stdout: bytes, nonce: str) -> RunResult | None:
    """RunResult from the last stdout line starting with nonce; None if there is no such line."""
    for line in reversed(stdout.decode("utf-8", errors="replace").splitlines()):
        if line.startswith(nonce):
            try:
                return RunResult.model_validate_json(line[len(nonce):])
            except ValidationError as exc:
                raise SandboxError(f"runner returned a malformed result: {exc.error_count()} errors") from exc
    return None


def timeout_result(tests: list[dict[str, Any]], timeout_s: float) -> RunResult:
    return RunResult(
        verdict="timeout",
        total=len(tests),
        tests=[
            TestCaseResult(
                name=str(test.get("name") or f"t{index + 1}"),
                passed=False,
                error=TIME_EXCEEDED,
                time_ms=int(timeout_s * 1000) if index == 0 else 0,
            )
            for index, test in enumerate(tests)
        ],
        stderr=f"{TIME_EXCEEDED} ({timeout_s:g} с)",
    )


def memory_result(tests: list[dict[str, Any]]) -> RunResult:
    return RunResult(verdict="error", total=len(tests), stderr=MEMORY_EXCEEDED)
