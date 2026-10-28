# Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
# Proprietary and confidential. See LICENSE in the project root.

import json
import logging
from dataclasses import asdict, dataclass

logger = logging.getLogger("app.llm")


@dataclass
class LLMCall:
    purpose: str
    model: str
    session_id: str | None = None
    tokens_in: int = 0
    tokens_out: int = 0
    estimated: bool = False
    duration_ms: int = 0
    first_token_ms: int | None = None
    ok: bool = True
    error: str | None = None


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = getattr(record, "llm_call", None)
        if payload is None:
            return json.dumps({"event": "log", "level": record.levelname, "message": record.getMessage()}, ensure_ascii=False)
        return json.dumps({"event": "llm_call", **payload}, ensure_ascii=False)


def log_call(call: LLMCall) -> None:
    level = logging.INFO if call.ok else logging.WARNING
    logger.log(level, "llm_call", extra={"llm_call": asdict(call)})


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)
