# Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
# Proprietary and confidential. See LICENSE in the project root.
"""Worker settings from environment variables (contract, section 8)."""

import os
from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class WorkerSettings:
    concurrency: int = 2
    poll_interval_s: float = 0.5
    # A run stuck in `running` this long belongs to a dead worker and goes back to the queue.
    stale_after_s: float = 60.0
    stale_check_interval_s: float = 30.0
    max_attempts: int = 3
    # Outer bound on Sandbox.run, which enforces SANDBOX_TIMEOUT_S itself; this only guards
    # against a hung Docker call. Must stay below stale_after_s, or a slow run is processed twice.
    sandbox_guard_s: float = 30.0
    review_timeout_s: float = 60.0

    def __post_init__(self) -> None:
        if self.concurrency < 1:
            raise ValueError("WORKER_CONCURRENCY must be at least 1")
        if self.sandbox_guard_s + 10 > self.stale_after_s:
            raise ValueError(
                f"WORKER_STALE_AFTER_S ({self.stale_after_s}) must exceed the sandbox guard "
                f"({self.sandbox_guard_s} s) by at least 10 s"
            )

    @classmethod
    def from_env(cls, env: Mapping[str, str] = os.environ) -> "WorkerSettings":
        sandbox_timeout_s = float(env.get("SANDBOX_TIMEOUT_S", "5"))
        return cls(
            concurrency=int(env.get("WORKER_CONCURRENCY", "2")),
            poll_interval_s=int(env.get("WORKER_POLL_MS", "500")) / 1000,
            stale_after_s=float(env.get("WORKER_STALE_AFTER_S", "60")),
            max_attempts=int(env.get("WORKER_MAX_ATTEMPTS", "3")),
            sandbox_guard_s=sandbox_timeout_s + 25,
            review_timeout_s=float(env.get("WORKER_REVIEW_TIMEOUT_S", "60")),
        )
