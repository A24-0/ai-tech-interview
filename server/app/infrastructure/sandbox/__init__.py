# Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
# Proprietary and confidential. See LICENSE in the project root.
"""Sandbox factory. Call sites use get_sandbox(), never a concrete sandbox."""

import os
from functools import cache

from app.domain.sandbox import Sandbox
from app.infrastructure.sandbox.fake import FakeSandbox


@cache
def get_sandbox() -> Sandbox:
    """SANDBOX_BACKEND=fake|docker|subprocess (default: fake). Cached singleton."""
    backend = os.environ.get("SANDBOX_BACKEND", "fake").strip().lower()
    if backend == "fake":
        return FakeSandbox()
    if backend in ("docker", "subprocess"):
        raise NotImplementedError(
            f"SANDBOX_BACKEND={backend} is not implemented yet; use SANDBOX_BACKEND=fake for now"
        )
    raise ValueError(f"Unknown SANDBOX_BACKEND={backend!r}; expected fake, docker or subprocess")
