# Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
# Proprietary and confidential. See LICENSE in the project root.
"""In-memory runs for the runs stubs. Replaced by the runs queue (code_runs)."""

import hashlib
import uuid
from dataclasses import dataclass
from datetime import datetime


@dataclass
class StubRun:
    id: uuid.UUID
    session_id: uuid.UUID
    client_run_id: uuid.UUID
    code_hash: str
    created_at: datetime
    cancelled: bool = False


class StubStore:
    def __init__(self) -> None:
        self.runs: dict[uuid.UUID, StubRun] = {}

    def runs_for_session(self, session_id: uuid.UUID) -> list[StubRun]:
        return [r for r in self.runs.values() if r.session_id == session_id]


store = StubStore()


def code_hash(code: str) -> str:
    normalized = code.replace("\r\n", "\n").replace("\r", "\n")
    normalized = "\n".join(line.rstrip() for line in normalized.split("\n")).rstrip()
    return hashlib.sha256(normalized.encode()).hexdigest()
