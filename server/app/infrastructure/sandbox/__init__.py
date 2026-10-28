# Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
# Proprietary and confidential. See LICENSE in the project root.
"""Sandbox factory. Call sites use get_sandbox(), never a concrete sandbox."""

import os
from functools import cache

from app.domain.sandbox import Sandbox
from app.infrastructure.sandbox.fake import FakeSandbox
from app.infrastructure.sandbox.runner_io import SandboxSettings


@cache
def get_sandbox() -> Sandbox:
    """SANDBOX_BACKEND=fake|docker|subprocess (default: fake). Cached singleton."""
    backend = os.environ.get("SANDBOX_BACKEND", "fake").strip().lower()
    if backend == "fake":
        return FakeSandbox()
    if backend == "docker":
        from app.infrastructure.sandbox.docker_sandbox import DockerSandbox

        return DockerSandbox(SandboxSettings.from_env())
    if backend == "subprocess":
        from app.infrastructure.sandbox.subprocess_sandbox import SubprocessSandbox

        return SubprocessSandbox(SandboxSettings.from_env())
    raise ValueError(f"Unknown SANDBOX_BACKEND={backend!r}; expected fake, docker or subprocess")
