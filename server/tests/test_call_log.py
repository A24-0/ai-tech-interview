# Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
# Proprietary and confidential. See LICENSE in the project root.

import json
import logging

import pytest

from app.infrastructure.ai.call_log import JsonLogFormatter, LLMCall, estimate_tokens, log_call


def test_log_call_emits_one_json_line_with_required_fields(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO, logger="app.llm")

    log_call(LLMCall(purpose="chat", model="m", session_id="s1", tokens_in=10, tokens_out=5, duration_ms=120))

    record = caplog.records[0]
    payload = json.loads(JsonLogFormatter().format(record))
    assert payload["event"] == "llm_call"
    assert payload["session_id"] == "s1"
    assert payload["model"] == "m"
    assert payload["tokens_in"] == 10
    assert payload["tokens_out"] == 5
    assert payload["duration_ms"] == 120
    assert payload["ok"] is True


def test_failed_call_is_logged_as_warning(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO, logger="app.llm")

    log_call(LLMCall(purpose="chat", model="m", ok=False, error="timeout"))

    assert caplog.records[0].levelno == logging.WARNING


def test_estimate_tokens_is_len_over_four() -> None:
    assert estimate_tokens("a" * 40) == 10
    assert estimate_tokens("") == 1
