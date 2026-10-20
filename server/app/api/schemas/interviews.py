# Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
# Proprietary and confidential. See LICENSE in the project root.
"""Interview schemas, contract section 6.1."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import Field

from app.domain.base import CamelModel

Level = Literal["junior", "middle", "senior"]


class TaskOut(CamelModel):
    id: int
    title: str
    statement: str
    starter_code: str
    language: str = "python"


class MessageOut(CamelModel):
    id: int
    role: Literal["user", "assistant", "system"]
    content: str
    created_at: datetime


class InterviewOut(CamelModel):
    id: uuid.UUID
    status: Literal["active", "finished", "abandoned"]
    topic_id: int
    level: Level
    messages: list[MessageOut]
    task: TaskOut | None = None


class StartInterviewIn(CamelModel):
    topic_id: int
    level: Level


class SendMessageIn(CamelModel):
    content: str = Field(min_length=1, max_length=10000)
    client_message_id: uuid.UUID


class FinishOut(CamelModel):
    id: uuid.UUID
    status: Literal["finished"]
