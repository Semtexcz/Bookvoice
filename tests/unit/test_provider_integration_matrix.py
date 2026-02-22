"""Provider integration matrix tests for mocked happy and failure paths."""

from __future__ import annotations

import io
from pathlib import Path
import wave

import pytest

from bookvoice.config import BookvoiceConfig
from bookvoice.errors import PipelineStageError
from bookvoice.io.storage import ArtifactStore
from bookvoice.llm.openai_client import OpenAIChatClient, OpenAIProviderError, OpenAISpeechClient
from bookvoice.models.datatypes import Chunk, RewriteResult, TranslationResult
from bookvoice.pipeline import BookvoicePipeline
from bookvoice.provider_factory import ProviderFactory
from bookvoice.tts.voices import VoiceProfile


def _mock_wav_bytes(duration_seconds: float = 0.25, sample_rate: int = 24000) -> bytes:
    """Build deterministic mono WAV bytes for matrix TTS tests."""

    frame_count = int(duration_seconds * sample_rate)
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(b"\x00\x00" * frame_count)
    return buffer.getvalue()


def test_provider_happy_path_matrix_translate_rewrite_tts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Provider matrix should cover mocked happy paths for translate, rewrite, and TTS."""

    def _mock_chat_completion(self, **kwargs: object) -> str:
        """Return deterministic text for OpenAI chat-backed stage mocks."""

        _ = self
        _ = kwargs
        return "matrix-mocked-text"

    def _mock_synthesize_speech(self, **kwargs: object) -> bytes:
        """Return deterministic WAV bytes for OpenAI speech-backed stage mocks."""

        _ = self
        _ = kwargs
        return _mock_wav_bytes()

    monkeypatch.setattr(OpenAIChatClient, "chat_completion_text", _mock_chat_completion)
    monkeypatch.setattr(OpenAISpeechClient, "synthesize_speech", _mock_synthesize_speech)

    chunk = Chunk(chapter_index=1, chunk_index=0, text="Hello world.", char_start=0, char_end=12)
    translator = ProviderFactory.create_translator("openai", "translate-model", "test-key")
    translated = translator.translate(chunk, target_language="cs")
    assert translated.translated_text == "matrix-mocked-text"
    assert translated.provider == "openai"
    assert translated.model == "translate-model"

    rewriter = ProviderFactory.create_rewriter("openai", "rewrite-model", "test-key")
    rewritten = rewriter.rewrite(translated)
    assert rewritten.rewritten_text == "matrix-mocked-text"
    assert rewritten.provider == "openai"
    assert rewritten.model == "rewrite-model"

    synthesizer = ProviderFactory.create_tts_synthesizer(
        "openai",
        output_root=tmp_path,
        model="tts-model",
        api_key="test-key",
    )
    audio_part = synthesizer.synthesize(
        rewritten,
        VoiceProfile(
            name="alloy",
            provider_voice_id="alloy",
            language="cs",
            speaking_rate=1.0,
        ),
    )
    assert audio_part.path.exists()
    assert audio_part.provider == "openai"
    assert audio_part.model == "tts-model"
    assert audio_part.voice == "alloy"


@pytest.mark.parametrize(
    ("stage", "failure_kind", "expected_detail", "expected_hint"),
    [
        (
            "translate",
            "invalid_api_key",
            "authentication failed",
            "bookvoice credentials",
        ),
        (
            "rewrite",
            "invalid_model",
            "configured model",
            "--model-rewrite",
        ),
        (
            "tts",
            "timeout",
            "timed out",
            "Retry the command",
        ),
    ],
)
def test_provider_failure_matrix_maps_stage_specific_diagnostics(
    stage: str,
    failure_kind: str,
    expected_detail: str,
    expected_hint: str,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Provider matrix should map representative stage failures to actionable diagnostics."""

    pipeline = BookvoicePipeline()
    config = BookvoiceConfig(input_pdf=Path("in.pdf"), output_dir=tmp_path, api_key="key")
    chunk = Chunk(chapter_index=1, chunk_index=0, text="Text", char_start=0, char_end=4)
    translation = TranslationResult(
        chunk=chunk,
        translated_text="Ahoj",
        provider="openai",
        model="gpt-4.1-mini",
    )
    rewrite = RewriteResult(
        translation=translation,
        rewritten_text="Ahoj",
        provider="openai",
        model="gpt-4.1-mini",
    )

    if stage in {"translate", "rewrite"}:
        def _failing_chat_completion(self, **kwargs: object) -> str:
            """Raise deterministic provider failure from chat client mock."""

            _ = self
            _ = kwargs
            raise OpenAIProviderError("matrix failure", failure_kind=failure_kind)

        monkeypatch.setattr(OpenAIChatClient, "chat_completion_text", _failing_chat_completion)
    else:
        def _failing_synthesize_speech(self, **kwargs: object) -> bytes:
            """Raise deterministic provider failure from speech client mock."""

            _ = self
            _ = kwargs
            raise OpenAIProviderError("matrix failure", failure_kind=failure_kind)

        monkeypatch.setattr(OpenAISpeechClient, "synthesize_speech", _failing_synthesize_speech)

    if stage == "translate":
        with pytest.raises(PipelineStageError, match=expected_detail) as exc_info:
            pipeline._translate([chunk], config)
    elif stage == "rewrite":
        with pytest.raises(PipelineStageError, match=expected_detail) as exc_info:
            pipeline._rewrite_for_audio([translation], config)
    else:
        with pytest.raises(PipelineStageError, match=expected_detail) as exc_info:
            pipeline._tts([rewrite], config, store=ArtifactStore(tmp_path / "run"))

    assert exc_info.value.stage == stage
    assert expected_hint in (exc_info.value.hint or "")
