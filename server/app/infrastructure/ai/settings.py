# Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
# Proprietary and confidential. See LICENSE in the project root.

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class LLMSettings:
    base_url: str = ""
    api_key: str = ""
    model: str = ""
    timeout_s: float = 30.0
    max_retries: int = 2

    @classmethod
    def from_env(cls) -> "LLMSettings":
        env = os.environ
        return cls(
            base_url=env.get("LLM_BASE_URL", "").rstrip("/"),
            api_key=env.get("LLM_API_KEY", ""),
            model=env.get("LLM_MODEL", ""),
            timeout_s=float(env.get("LLM_TIMEOUT_S", cls.timeout_s)),
            max_retries=int(env.get("LLM_MAX_RETRIES", cls.max_retries)),
        )
