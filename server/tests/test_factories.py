# Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
# Proprietary and confidential. See LICENSE in the project root.

from collections.abc import Iterator

import pytest

from app.infrastructure.ai import get_chat_provider
from app.infrastructure.ai.fake import FakeChatProvider
from app.infrastructure.ai.openai_compatible import OpenAICompatibleChatProvider
from app.infrastructure.sandbox import get_sandbox
from app.infrastructure.sandbox.docker_sandbox import DockerSandbox
from app.infrastructure.sandbox.fake import FakeSandbox
from app.infrastructure.sandbox.subprocess_sandbox import SubprocessSandbox


@pytest.fixture(autouse=True)
def clear_factory_cache() -> Iterator[None]:
    get_chat_provider.cache_clear()
    get_sandbox.cache_clear()
    yield
    get_chat_provider.cache_clear()
    get_sandbox.cache_clear()


def test_chat_provider_defaults_to_fake_singleton(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LLM_PROVIDER", raising=False)

    provider = get_chat_provider()

    assert isinstance(provider, FakeChatProvider)
    assert get_chat_provider() is provider


def test_chat_provider_openai_compatible_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "openai_compatible")
    monkeypatch.setenv("LLM_BASE_URL", "https://llm.example/v1/")
    monkeypatch.setenv("LLM_MODEL", "test-model")
    monkeypatch.setenv("LLM_MAX_RETRIES", "1")

    provider = get_chat_provider()

    assert isinstance(provider, OpenAICompatibleChatProvider)
    assert provider.settings.base_url == "https://llm.example/v1"
    assert provider.settings.max_retries == 1


def test_chat_provider_openai_compatible_needs_url_and_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "openai_compatible")
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)

    with pytest.raises(ValueError):
        get_chat_provider()


def test_chat_provider_unknown_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "nope")

    with pytest.raises(ValueError):
        get_chat_provider()


def test_sandbox_defaults_to_fake_singleton(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SANDBOX_BACKEND", raising=False)

    sandbox = get_sandbox()

    assert isinstance(sandbox, FakeSandbox)
    assert get_sandbox() is sandbox


@pytest.mark.parametrize(
    ("backend", "expected"), [("docker", DockerSandbox), ("subprocess", SubprocessSandbox)]
)
def test_sandbox_real_backends(monkeypatch: pytest.MonkeyPatch, backend: str, expected: type) -> None:
    monkeypatch.setenv("SANDBOX_BACKEND", backend)
    monkeypatch.setenv("SANDBOX_TIMEOUT_S", "3")

    sandbox = get_sandbox()

    assert isinstance(sandbox, expected)
    assert sandbox.settings.timeout_s == 3  # type: ignore[attr-defined]


def test_sandbox_unknown_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SANDBOX_BACKEND", "nope")

    with pytest.raises(ValueError):
        get_sandbox()
