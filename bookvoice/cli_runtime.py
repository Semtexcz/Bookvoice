"""CLI provider runtime resolution helpers.

This module isolates provider/model prompt flow, runtime source assembly,
and secure API-key persistence from the command wiring layer.
"""

from __future__ import annotations

from typing import Callable, Protocol

import typer

from .credentials import create_credential_store
from .errors import PipelineStageError
from .parsing import normalize_optional_string


class CredentialStoreProtocol(Protocol):
    """Protocol for secure credential store operations used by CLI runtime resolution."""

    def get_api_key(self) -> str | None:
        """Return currently stored API key, if available."""

    def set_api_key(self, api_key: str) -> None:
        """Persist API key value in secure storage."""


def _set_runtime_cli_value(
    runtime_cli_values: dict[str, str],
    key: str,
    value: str | None,
) -> None:
    """Set a normalized runtime CLI value when user input is present."""

    normalized = normalize_optional_string(value)
    if normalized is not None:
        runtime_cli_values[key] = normalized


def _prompt_for_provider_runtime_values(
    runtime_cli_values: dict[str, str],
    prompt_api_key: bool,
) -> bool:
    """Prompt for provider/model settings and optionally API key.

    Returns:
        `True` when an API key was entered via prompt in this run.
    """

    runtime_cli_values["provider_translator"] = typer.prompt(
        "Translator provider",
        default=runtime_cli_values.get("provider_translator", "openai"),
    ).strip()
    runtime_cli_values["provider_rewriter"] = typer.prompt(
        "Rewriter provider",
        default=runtime_cli_values.get("provider_rewriter", "openai"),
    ).strip()
    runtime_cli_values["provider_tts"] = typer.prompt(
        "TTS provider",
        default=runtime_cli_values.get("provider_tts", "openai"),
    ).strip()
    runtime_cli_values["model_translate"] = typer.prompt(
        "Translate model",
        default=runtime_cli_values.get("model_translate", "gpt-4.1-mini"),
    ).strip()
    runtime_cli_values["model_rewrite"] = typer.prompt(
        "Rewrite model",
        default=runtime_cli_values.get("model_rewrite", "gpt-4.1-mini"),
    ).strip()
    runtime_cli_values["model_tts"] = typer.prompt(
        "TTS model",
        default=runtime_cli_values.get("model_tts", "gpt-4o-mini-tts"),
    ).strip()
    runtime_cli_values["tts_voice"] = typer.prompt(
        "TTS voice",
        default=runtime_cli_values.get("tts_voice", "echo"),
    ).strip()
    if not prompt_api_key:
        return False

    prompted_api_key = normalize_optional_string(
        typer.prompt(
            "OpenAI API key (hidden; leave blank to skip)",
            default="",
            hide_input=True,
            show_default=False,
        )
    )
    if prompted_api_key is None:
        return False

    runtime_cli_values["api_key"] = prompted_api_key
    return True


def resolve_provider_runtime_sources(
    provider_translator: str | None,
    provider_rewriter: str | None,
    provider_tts: str | None,
    model_translate: str | None,
    model_rewrite: str | None,
    model_tts: str | None,
    tts_voice: str | None,
    api_key: str | None,
    interactive_provider_setup: bool,
    prompt_api_key: bool,
    store_api_key: bool,
    credential_store_factory: Callable[[], CredentialStoreProtocol] = create_credential_store,
) -> tuple[dict[str, str], dict[str, str]]:
    """Resolve CLI and secure runtime source mappings for provider configuration."""

    runtime_cli_values: dict[str, str] = {}
    _set_runtime_cli_value(runtime_cli_values, "provider_translator", provider_translator)
    _set_runtime_cli_value(runtime_cli_values, "provider_rewriter", provider_rewriter)
    _set_runtime_cli_value(runtime_cli_values, "provider_tts", provider_tts)
    _set_runtime_cli_value(runtime_cli_values, "model_translate", model_translate)
    _set_runtime_cli_value(runtime_cli_values, "model_rewrite", model_rewrite)
    _set_runtime_cli_value(runtime_cli_values, "model_tts", model_tts)
    _set_runtime_cli_value(runtime_cli_values, "tts_voice", tts_voice)
    _set_runtime_cli_value(runtime_cli_values, "api_key", api_key)

    api_key_entered_in_run = "api_key" in runtime_cli_values
    if interactive_provider_setup:
        prompted_key_entered = _prompt_for_provider_runtime_values(
            runtime_cli_values=runtime_cli_values,
            prompt_api_key=prompt_api_key or "api_key" not in runtime_cli_values,
        )
        api_key_entered_in_run = api_key_entered_in_run or prompted_key_entered
    elif prompt_api_key and "api_key" not in runtime_cli_values:
        prompted_api_key = normalize_optional_string(
            typer.prompt(
                "OpenAI API key (hidden; leave blank to skip)",
                default="",
                hide_input=True,
                show_default=False,
            )
        )
        if prompted_api_key is not None:
            runtime_cli_values["api_key"] = prompted_api_key
            api_key_entered_in_run = True

    credential_store = credential_store_factory()
    runtime_secure_values: dict[str, str] = {}
    stored_api_key = credential_store.get_api_key()
    if stored_api_key is not None:
        runtime_secure_values["api_key"] = stored_api_key

    if api_key_entered_in_run and "api_key" in runtime_cli_values and store_api_key:
        try:
            credential_store.set_api_key(runtime_cli_values["api_key"])
            typer.echo("Stored API key in secure credential storage.")
        except Exception as exc:
            raise PipelineStageError(
                stage="credentials",
                detail=f"Failed to store API key securely: {exc}",
                hint=(
                    "Install and configure a keyring backend, or rerun with "
                    "`--no-store-api-key` for one-off usage."
                ),
            ) from exc

    return runtime_cli_values, runtime_secure_values
