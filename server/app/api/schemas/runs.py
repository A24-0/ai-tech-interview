# Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
# Proprietary and confidential. See LICENSE in the project root.
"""Request and response bodies of the code run endpoints (contract, section 6.2)."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import Field

from app.domain.base import CamelModel
from app.domain.code_runs import MAX_CODE_CHARS, RunStatus


class RunCreate(CamelModel):
    code: str = Field(min_length=1, max_length=MAX_CODE_CHARS)
    client_run_id: uuid.UUID


class RunAccepted(CamelModel):
    run_id: uuid.UUID
    status: RunStatus


class RunOut(CamelModel):
    run_id: uuid.UUID
    status: RunStatus
    code_hash: str
    created_at: datetime
    finished_at: datetime | None
    result: dict[str, Any] | None = Field(description="RunResult (contract 6.3); null until status is done")
    ai_review: dict[str, Any] | None = Field(description="CodeReview (contract 6.4); null until it is ready")
    error: str | None
