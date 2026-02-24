"""Tests for provider factories and provider runtime configuration resolution."""

import io
from pathlib import Path

from tests.fixture_paths import canonical_content_pdf_fixture_path
import wave

import pytest

from bookvoice.config import BookvoiceConfig, RuntimeConfigSources
from bookvoice.errors import PipelineStageError
from bookvoice.llm.openai_client import OpenAIChatClient, OpenAISpeechClient
from bookvoice.models.datatypes import Chunk, TranslationResult
from bookvoice.pipeline import BookvoicePipeline
from bookvoice.provider_factory import ProviderFactory
from bookvoice.tts.voices import VoiceProfile


def _mock_wav_bytes(duration_seconds: float = 0.25, sample_rate: int = 24000) -> bytes:
    """Build deterministic mono WAV bytes for provider-factory TTS tests."""

    frame_count = int(duration_seconds * sample_rate)
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(b"\x00\x00" * frame_count)
    return buffer.getvalue()


def test_runtime_config_precedence_cli_over_secure_over_env_over_default() -> None:
    """Runtime config should resolve values using deterministic source precedence."""

    config = BookvoiceConfig(input_pdf=Path("in.pdf"), output_dir=Path("out"))
    runtime = config.resolved_provider_runtime(
        RuntimeConfigSources(
            cli={"model_translate": "cli-translate", "api_key": "cli-key"},
            secure={"model_translate": "secure-translate", "api_key": "secure-key"},
            env={"BOOKVOICE_MODEL_TRANSLATE": "env-translate", "OPENAI_API_KEY": "env-key"},
        )
    )

    assert runtime.translate_model == "cli-translate"
    assert runtime.api_key == "cli-key"


def test_runtime_config_uses_secure_when_cli_missing() -> None:
    """Runtime config should use secure storage values when CLI values are missing."""

    config = BookvoiceConfig(input_pdf=Path("in.pdf"), output_dir=Path("out"), api_key=None)
    runtime = config.resolved_provider_runtime(
        RuntimeConfigSources(
            secure={"api_key": "secure-key"},
            env={"OPENAI_API_KEY": "env-key"},
        )
    )

    assert runtime.api_key == "secure-key"


def test_runtime_config_rejects_unsupported_provider_from_env() -> None:
    """Runtime config should fail validation for unsupported provider identifiers."""

    config = BookvoiceConfig(input_pdf=Path("in.pdf"), output_dir=Path("out"))

    with pytest.raises(ValueError, match="Unsupported `provider_translator`"):
        config.resolved_provider_runtime(
            RuntimeConfigSources(env={"BOOKVOICE_PROVIDER_TRANSLATOR": "azure"})
        )


def test_runtime_config_resolves_rewrite_bypass_from_env() -> None:
    """Runtime config should parse rewrite bypass boolean values from environment."""

    config = BookvoiceConfig(input_pdf=Path("in.pdf"), output_dir=Path("out"))
    runtime = config.resolved_provider_runtime(
        RuntimeConfigSources(env={"BOOKVOICE_REWRITE_BYPASS": "true"})
    )

    assert runtime.rewrite_bypass is True


def test_provider_factory_creates_openai_clients_with_selected_models(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Factory should return openai clients that preserve provider/model metadata."""

    def _mock_chat_completion(self, **kwargs: object) -> str:
        """Return deterministic text for provider factory unit testing."""

        _ = self
        _ = kwargs
        return "mocked output"

    def _mock_synthesize_speech(self, **kwargs: object) -> bytes:
        """Return deterministic WAV bytes for provider factory unit testing."""

        _ = self
        _ = kwargs
        return _mock_wav_bytes()

    monkeypatch.setattr(OpenAIChatClient, "chat_completion_text", _mock_chat_completion)
    monkeypatch.setattr(OpenAISpeechClient, "synthesize_speech", _mock_synthesize_speech)

    chunk = Chunk(chapter_index=1, chunk_index=0, text="Hello", char_start=0, char_end=5)
    translation = TranslationResult(
        chunk=chunk,
        translated_text="Ahoj",
        provider="openai",
        model="gpt-4.1-mini",
    )

    translator = ProviderFactory.create_translator("openai", "translate-model", "test-key")
    translated = translator.translate(chunk, "cs")
    assert translated.provider == "openai"
    assert translated.model == "translate-model"
    assert translated.translated_text == "mocked output"

    rewriter = ProviderFactory.create_rewriter("openai", "rewrite-model", "test-key")
    rewritten = rewriter.rewrite(translation)
    assert rewritten.provider == "openai"
    assert rewritten.model == "rewrite-model"
    assert rewritten.rewritten_text == "mocked output"

    synthesizer = ProviderFactory.create_tts_synthesizer(
        "openai",
        output_root=tmp_path,
        model="tts-model",
        api_key="test-key",
    )
    part = synthesizer.synthesize(
        rewritten,
        VoiceProfile(
            name="alloy",
            provider_voice_id="alloy",
            language="cs",
            speaking_rate=1.0,
        ),
    )
    assert part.path.exists()


def test_provider_factory_rejects_unsupported_provider_ids(tmp_path: Path) -> None:
    """Factory should raise clear errors for unsupported provider identifiers."""

    with pytest.raises(ValueError, match="Unsupported translator provider"):
        ProviderFactory.create_translator("unsupported", "model")

    with pytest.raises(ValueError, match="Unsupported rewriter provider"):
        ProviderFactory.create_rewriter("unsupported", "model")

    with pytest.raises(ValueError, match="Unsupported TTS provider"):
        ProviderFactory.create_tts_synthesizer("unsupported", output_root=tmp_path, model="model")


def test_pipeline_surfaces_config_validation_errors(tmp_path: Path) -> None:
    """Pipeline should map invalid config values to a stage-aware config error."""

    pipeline = BookvoicePipeline()
    config = BookvoiceConfig(
        input_pdf=canonical_content_pdf_fixture_path(),
        output_dir=tmp_path / "out",
        provider_tts="unsupported",
    )

    with pytest.raises(PipelineStageError, match="Unsupported `provider_tts`"):
        pipeline.run(config)
