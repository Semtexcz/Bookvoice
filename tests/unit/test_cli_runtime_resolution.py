"""Unit tests for CLI provider runtime resolution helpers."""

from __future__ import annotations

import pytest

from bookvoice.cli_runtime import resolve_provider_runtime_sources
from bookvoice.errors import PipelineStageError


class InMemoryCredentialStore:
    """In-memory credential store implementation for runtime-resolution tests."""

    def __init__(self, initial_api_key: str | None = None) -> None:
        """Initialize the store with an optional initial API key."""

        self._api_key = initial_api_key
        self.stored_values: list[str] = []

    def get_api_key(self) -> str | None:
        """Return currently stored API key value."""

        return self._api_key

    def set_api_key(self, api_key: str) -> None:
        """Persist API key value and keep a history for assertions."""

        self._api_key = api_key
        self.stored_values.append(api_key)


class FailingCredentialStore:
    """Credential store that raises when persisting API key values."""

    def get_api_key(self) -> str | None:
        """Return no pre-existing secure API key."""

        return None

    def set_api_key(self, api_key: str) -> None:
        """Raise deterministic storage failure used for error-path assertions."""

        raise RuntimeError("no keyring backend")


def test_resolve_provider_runtime_sources_collects_cli_and_secure_values() -> None:
    """Resolver should normalize CLI overrides and include secure API key fallback."""

    store = InMemoryCredentialStore(initial_api_key="secure-api-key")
    runtime_cli_values, runtime_secure_values = resolve_provider_runtime_sources(
        provider_translator=" openai ",
        provider_rewriter=None,
        provider_tts=None,
        model_translate=" cli-model-t ",
        model_rewrite=None,
        model_tts=None,
        tts_voice=None,
        api_key=None,
        interactive_provider_setup=False,
        prompt_api_key=False,
        store_api_key=True,
        credential_store_factory=lambda: store,
    )

    assert runtime_cli_values == {
        "provider_translator": "openai",
        "model_translate": "cli-model-t",
    }
    assert runtime_secure_values == {"api_key": "secure-api-key"}
    assert store.stored_values == []


def test_resolve_provider_runtime_sources_interactive_prompts_and_stores_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Interactive resolver path should collect prompted values and store entered API key."""

    prompt_values = iter(
        [
            "openai",
            "openai",
            "openai",
            "model-t",
            "model-r",
            "model-tts",
            "alloy",
            "prompted-api-key",
        ]
    )

    def _fake_prompt(*args: object, **kwargs: object) -> str:
        """Return deterministic values for each sequential prompt call."""

        del args, kwargs
        return next(prompt_values)

    monkeypatch.setattr("bookvoice.cli_runtime.typer.prompt", _fake_prompt)

    store = InMemoryCredentialStore()
    runtime_cli_values, runtime_secure_values = resolve_provider_runtime_sources(
        provider_translator=None,
        provider_rewriter=None,
        provider_tts=None,
        model_translate=None,
        model_rewrite=None,
        model_tts=None,
        tts_voice=None,
        api_key=None,
        interactive_provider_setup=True,
        prompt_api_key=False,
        store_api_key=True,
        credential_store_factory=lambda: store,
    )

    assert runtime_cli_values["provider_translator"] == "openai"
    assert runtime_cli_values["provider_rewriter"] == "openai"
    assert runtime_cli_values["provider_tts"] == "openai"
    assert runtime_cli_values["model_translate"] == "model-t"
    assert runtime_cli_values["model_rewrite"] == "model-r"
    assert runtime_cli_values["model_tts"] == "model-tts"
    assert runtime_cli_values["tts_voice"] == "alloy"
    assert runtime_cli_values["api_key"] == "prompted-api-key"
    assert runtime_secure_values == {}
    assert store.stored_values == ["prompted-api-key"]


def test_resolve_provider_runtime_sources_prompt_api_key_blank_skips_storage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Blank prompted API key should not be added to CLI runtime values nor stored."""

    def _fake_prompt(*args: object, **kwargs: object) -> str:
        """Return blank input for one-off API-key prompt invocation."""

        del args, kwargs
        return "   "

    monkeypatch.setattr("bookvoice.cli_runtime.typer.prompt", _fake_prompt)

    store = InMemoryCredentialStore()
    runtime_cli_values, runtime_secure_values = resolve_provider_runtime_sources(
        provider_translator=None,
        provider_rewriter=None,
        provider_tts=None,
        model_translate=None,
        model_rewrite=None,
        model_tts=None,
        tts_voice=None,
        api_key=None,
        interactive_provider_setup=False,
        prompt_api_key=True,
        store_api_key=True,
        credential_store_factory=lambda: store,
    )

    assert "api_key" not in runtime_cli_values
    assert runtime_secure_values == {}
    assert store.stored_values == []


def test_resolve_provider_runtime_sources_storage_failure_raises_stage_error() -> None:
    """Credential-store persistence errors should map to credentials stage diagnostics."""

    with pytest.raises(PipelineStageError) as exc_info:
        resolve_provider_runtime_sources(
            provider_translator=None,
            provider_rewriter=None,
            provider_tts=None,
            model_translate=None,
            model_rewrite=None,
            model_tts=None,
            tts_voice=None,
            api_key="explicit-api-key",
            interactive_provider_setup=False,
            prompt_api_key=False,
            store_api_key=True,
            credential_store_factory=FailingCredentialStore,
        )

    assert exc_info.value.stage == "credentials"
    assert "Failed to store API key securely:" in exc_info.value.detail
    assert "--no-store-api-key" in (exc_info.value.hint or "")
