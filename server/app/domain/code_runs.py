# Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
# Proprietary and confidential. See LICENSE in the project root.
"""Code run statuses and business rules (contract, section 6.2)."""

import hashlib
from typing import Final, Literal, get_args

RunStatus = Literal["queued", "running", "done", "failed", "cancelled"]
RUN_STATUSES: Final = get_args(RunStatus)

# A run in one of these statuses will not change any more.
FINAL_STATUSES: Final = frozenset({"done", "failed", "cancelled"})

MAX_CODE_CHARS: Final = 65_536


def normalize_code(code: str) -> str:
    """Unify line endings and drop trailing whitespace, so cosmetic edits hash the same."""
    lines = code.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    return "\n".join(line.rstrip() for line in lines).rstrip("\n")


def code_hash(code: str) -> str:
    return hashlib.sha256(normalize_code(code).encode("utf-8")).hexdigest()
