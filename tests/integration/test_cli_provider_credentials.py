"""Integration tests for CLI provider/model and secure credential flows."""

from pathlib import Path

from pytest import MonkeyPatch
from typer.testing import CliRunner

from bookvoice.cli import app
from bookvoice.models.datatypes import BookMeta, RunManifest


class InMemoryCredentialStore:
    """Simple in-memory credential store used for CLI tests."""

    def __init__(self, initial_api_key: str | None = None) -> None:
        """Initialize the store with an optional pre-seeded API key."""

        self._api_key = initial_api_key

    def is_available(self) -> bool:
        """Return availability flag expected by the CLI status command."""

        return True

    def get_api_key(self) -> str | None:
        """Return currently stored API key value."""

        return self._api_key

    def set_api_key(self, api_key: str) -> None:
        """Persist a normalized API key value."""

        self._api_key = api_key.strip()

    def clear_api_key(self) -> bool:
        """Clear API key and return whether one existed."""

        existed = self._api_key is not None
        self._api_key = None
        return existed


def _manifest_stub() -> RunManifest:
    """Return a minimal manifest for CLI command stubs in tests."""

    return RunManifest(
        run_id="run-test",
        config_hash="cfg-test",
        book=BookMeta(
            source_pdf=Path("tests/files/zero_to_one.pdf"),
            title="Zero to One",
            author="Author",
            language="en",
        ),
        merged_audio_path=Path("out/run-test/audio/bookvoice_merged.wav"),
        total_llm_cost_usd=0.0,
        total_tts_cost_usd=0.0,
        total_cost_usd=0.0,
        extra={"manifest_path": "out/run-test/run_manifest.json"},
    )


def test_build_interactive_provider_setup_hides_api_key_and_applies_models(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Build interactive setup should capture provider/model values and hide API key input."""

    captured_sources: dict[str, dict[str, str]] = {}

    def _fake_run(self, config):  # type: ignore[no-untyped-def]
        """Capture runtime source maps and return a deterministic manifest."""

        captured_sources["cli"] = dict(config.runtime_sources.cli)
        captured_sources["secure"] = dict(config.runtime_sources.secure)
        return _manifest_stub()

    monkeypatch.setattr("bookvoice.cli.BookvoicePipeline.run", _fake_run)
    monkeypatch.setattr(
        "bookvoice.cli.create_credential_store",
        lambda: InMemoryCredentialStore(),
    )

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "build",
            str(Path("tests/files/zero_to_one.pdf")),
            "--out",
            str(tmp_path / "out"),
            "--interactive-provider-setup",
            "--no-store-api-key",
        ],
        input="openai\nopenai\nopenai\nmodel-t\nmodel-r\nmodel-tts\nalloy\nsecret-api-key\n",
    )

    assert result.exit_code == 0, result.output
    assert "secret-api-key" not in result.output
    assert captured_sources["cli"]["provider_translator"] == "openai"
    assert captured_sources["cli"]["provider_rewriter"] == "openai"
    assert captured_sources["cli"]["provider_tts"] == "openai"
    assert captured_sources["cli"]["model_translate"] == "model-t"
    assert captured_sources["cli"]["model_rewrite"] == "model-r"
    assert captured_sources["cli"]["model_tts"] == "model-tts"
    assert captured_sources["cli"]["tts_voice"] == "alloy"
    assert captured_sources["cli"]["api_key"] == "secret-api-key"
    assert captured_sources["secure"] == {}


def test_build_non_interactive_runtime_precedence_cli_over_secure_over_env(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Build should apply deterministic runtime precedence for non-interactive options."""

    observed_runtime: dict[str, str] = {}

    def _fake_run(self, config):  # type: ignore[no-untyped-def]
        """Resolve runtime config as pipeline would and capture resolved values."""

        runtime = config.resolved_provider_runtime(config.runtime_sources)
        observed_runtime["translate_model"] = runtime.translate_model
        observed_runtime["rewrite_model"] = runtime.rewrite_model
        observed_runtime["tts_model"] = runtime.tts_model
        observed_runtime["api_key"] = runtime.api_key or ""
        return _manifest_stub()

    monkeypatch.setattr("bookvoice.cli.BookvoicePipeline.run", _fake_run)
    monkeypatch.setattr(
        "bookvoice.cli.create_credential_store",
        lambda: InMemoryCredentialStore(initial_api_key="secure-api-key"),
    )
    monkeypatch.setenv("OPENAI_API_KEY", "env-api-key")

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "build",
            str(Path("tests/files/zero_to_one.pdf")),
            "--out",
            str(tmp_path / "out"),
            "--model-translate",
            "cli-model-t",
            "--model-rewrite",
            "cli-model-r",
            "--model-tts",
            "cli-model-tts",
        ],
    )

    assert result.exit_code == 0, result.output
    assert observed_runtime["translate_model"] == "cli-model-t"
    assert observed_runtime["rewrite_model"] == "cli-model-r"
    assert observed_runtime["tts_model"] == "cli-model-tts"
    assert observed_runtime["api_key"] == "secure-api-key"


def test_build_non_interactive_runtime_falls_back_to_env_when_cli_and_secure_missing(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Build should resolve provider/model/runtime values from env fallback when needed."""

    observed_runtime: dict[str, str] = {}

    def _fake_run(self, config):  # type: ignore[no-untyped-def]
        """Resolve runtime values and capture environment-sourced selections."""

        runtime = config.resolved_provider_runtime(config.runtime_sources)
        observed_runtime["translator_provider"] = runtime.translator_provider
        observed_runtime["rewriter_provider"] = runtime.rewriter_provider
        observed_runtime["tts_provider"] = runtime.tts_provider
        observed_runtime["translate_model"] = runtime.translate_model
        observed_runtime["rewrite_model"] = runtime.rewrite_model
        observed_runtime["tts_model"] = runtime.tts_model
        observed_runtime["tts_voice"] = runtime.tts_voice
        observed_runtime["api_key"] = runtime.api_key or ""
        return _manifest_stub()

    monkeypatch.setattr("bookvoice.cli.BookvoicePipeline.run", _fake_run)
    monkeypatch.setattr(
        "bookvoice.cli.create_credential_store",
        lambda: InMemoryCredentialStore(),
    )
    monkeypatch.setenv("BOOKVOICE_PROVIDER_TRANSLATOR", "openai")
    monkeypatch.setenv("BOOKVOICE_PROVIDER_REWRITER", "openai")
    monkeypatch.setenv("BOOKVOICE_PROVIDER_TTS", "openai")
    monkeypatch.setenv("BOOKVOICE_MODEL_TRANSLATE", "env-model-t")
    monkeypatch.setenv("BOOKVOICE_MODEL_REWRITE", "env-model-r")
    monkeypatch.setenv("BOOKVOICE_MODEL_TTS", "env-model-tts")
    monkeypatch.setenv("BOOKVOICE_TTS_VOICE", "alloy")
    monkeypatch.setenv("OPENAI_API_KEY", "env-api-key")

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "build",
            str(Path("tests/files/zero_to_one.pdf")),
            "--out",
            str(tmp_path / "out"),
        ],
    )

    assert result.exit_code == 0, result.output
    assert observed_runtime["translator_provider"] == "openai"
    assert observed_runtime["rewriter_provider"] == "openai"
    assert observed_runtime["tts_provider"] == "openai"
    assert observed_runtime["translate_model"] == "env-model-t"
    assert observed_runtime["rewrite_model"] == "env-model-r"
    assert observed_runtime["tts_model"] == "env-model-tts"
    assert observed_runtime["tts_voice"] == "alloy"
    assert observed_runtime["api_key"] == "env-api-key"


def test_credentials_command_supports_set_clear_and_status(
    monkeypatch: MonkeyPatch,
) -> None:
    """Credentials command should support storing, clearing, and reporting API key status."""

    store = InMemoryCredentialStore()
    monkeypatch.setattr("bookvoice.cli.create_credential_store", lambda: store)

    runner = CliRunner()

    set_result = runner.invoke(app, ["credentials", "--set-api-key"], input="key-from-prompt\n")
    assert set_result.exit_code == 0, set_result.output
    assert "API key stored in secure credential storage." in set_result.output
    assert store.get_api_key() == "key-from-prompt"

    status_result = runner.invoke(app, ["credentials"])
    assert status_result.exit_code == 0, status_result.output
    assert "Secure credential storage: available" in status_result.output
    assert "Stored OpenAI API key: present" in status_result.output

    clear_result = runner.invoke(app, ["credentials", "--clear-api-key"])
    assert clear_result.exit_code == 0, clear_result.output
    assert "Stored API key cleared from secure credential storage." in clear_result.output
    assert store.get_api_key() is None
