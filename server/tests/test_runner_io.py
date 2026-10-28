# Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
# Proprietary and confidential. See LICENSE in the project root.

import json

import pytest

from app.domain.sandbox import SandboxError
from app.infrastructure.sandbox.runner_io import (
    SandboxSettings,
    build_payload,
    find_result,
    new_nonce,
    timeout_result,
)

NONCE = "abc123"
RESULT = {"verdict": "passed", "passed": 1, "total": 1}


def test_find_result_takes_last_nonce_line() -> None:
    stdout = f"user output\n{NONCE}{json.dumps({'verdict': 'failed'})}\n{NONCE}{json.dumps(RESULT)}\n".encode()

    result = find_result(stdout, NONCE)

    assert result is not None and result.verdict == "passed"


def test_find_result_without_nonce_line_is_none() -> None:
    assert find_result(b"hello\n" + json.dumps(RESULT).encode(), NONCE) is None


def test_find_result_malformed_json_raises_sandbox_error() -> None:
    with pytest.raises(SandboxError):
        find_result(f"{NONCE}{{not json".encode(), NONCE)


def test_build_payload_matches_runner_contract() -> None:
    payload = json.loads(build_payload("code", "solve", [{"name": "t1"}], {"perTestTimeoutMs": 1}, NONCE))

    assert payload == {
        "code": "code", "entry": "solve", "tests": [{"name": "t1"}], "limits": {"perTestTimeoutMs": 1}, "nonce": NONCE,
    }


def test_nonce_is_random_hex() -> None:
    first, second = new_nonce(), new_nonce()

    assert first != second
    assert len(first) == 32 and int(first, 16) >= 0


def test_timeout_result_marks_every_test() -> None:
    result = timeout_result([{"name": "a"}, {}], 5)

    assert result.verdict == "timeout"
    assert (result.passed, result.total) == (0, 2)
    assert [t.name for t in result.tests] == ["a", "t2"]
    assert result.tests[0].time_ms == 5000


def test_settings_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SANDBOX_IMAGE", "img:1")
    monkeypatch.setenv("SANDBOX_TIMEOUT_S", "4")
    monkeypatch.setenv("SANDBOX_MEMORY_MB", "128")
    monkeypatch.setenv("SANDBOX_CPUS", "0.5")
    monkeypatch.setenv("SANDBOX_PIDS", "32")
    monkeypatch.setenv("DOCKER_HOST", "tcp://proxy:2375")

    settings = SandboxSettings.from_env()

    assert settings == SandboxSettings(
        image="img:1", timeout_s=4, memory_mb=128, cpus=0.5, pids=32, docker_host="tcp://proxy:2375",
    )
    assert settings.hard_timeout_s == 5


def test_default_runner_path_points_to_repo_runner() -> None:
    assert SandboxSettings().runner_path.is_file()
