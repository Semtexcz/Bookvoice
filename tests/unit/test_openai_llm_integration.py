"""Unit tests for OpenAI-backed translation and rewrite integrations."""

from __future__ import annotations

import io
import json
from pathlib import Path
import wave

import pytest

from bookvoice.config import BookvoiceConfig
from bookvoice.errors import PipelineStageError
from bookvoice.io.storage import ArtifactStore
from bookvoice.llm.audio_rewriter import AudioRewriter
from bookvoice.llm import openai_client as openai_http
from bookvoice.llm.openai_client import OpenAIChatClient, OpenAIProviderError, OpenAISpeechClient
from bookvoice.llm.translator import OpenAITranslator
from bookvoice.models.datatypes import Chunk, RewriteResult, TranslationResult
from bookvoice.pipeline import BookvoicePipeline
from bookvoice.tts.synthesizer import OpenAITTSSynthesizer
from bookvoice.tts.voices import VoiceProfile


class _MockRequestsResponse:
    """Minimal requests response mock for HTTP transport patching."""

    def __init__(self, *, payload: bytes, status_code: int = 200) -> None:
        """Initialize response with raw payload bytes and HTTP status."""

        self.content = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        """Raise HTTPError when the response status represents a failure."""

        if self.status_code >= 400:
            raise openai_http.requests.HTTPError(
                f"HTTP {self.status_code} error",
                response=self,
            )


class _MockBinaryHTTPResponse:
    """Minimal requests response mock for binary TTS payloads."""

    def __init__(self, payload: bytes) -> None:
        """Initialize response with binary payload bytes."""

        self._payload = payload

    @property
    def content(self) -> bytes:
        """Return serialized binary payload bytes."""

        return self._payload

    @property
    def status_code(self) -> int:
        """Expose successful HTTP status for compatibility with requests API."""

        return 200

    def raise_for_status(self) -> None:
        """No-op for successful mocked binary responses."""

        return None


def _mock_wav_bytes(duration_seconds: float = 0.25, sample_rate: int = 24000) -> bytes:
    """Build deterministic mono WAV bytes for OpenAI TTS unit tests."""

    frame_count = int(duration_seconds * sample_rate)
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(b"\x00\x00" * frame_count)
    return buffer.getvalue()


def test_openai_translator_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """Translator should return OpenAI text output and preserve provider/model metadata."""

    def _mock_post(_url: str, **_kwargs: object) -> _MockRequestsResponse:
        """Return a mocked OpenAI chat-completions response."""

        return _MockRequestsResponse(
            payload=json.dumps(
                {
                    "choices": [
                        {"message": {"content": "Ahoj svete."}},
                    ]
                }
            ).encode("utf-8")
        )

    monkeypatch.setattr("bookvoice.llm.openai_client.requests.post", _mock_post)

    translator = OpenAITranslator(model="gpt-4.1-mini", provider_id="openai", api_key="key")
    chunk = Chunk(chapter_index=1, chunk_index=0, text="Hello world.", char_start=0, char_end=12)

    result = translator.translate(chunk, target_language="cs")

    assert result.translated_text == "Ahoj svete."
    assert result.provider == "openai"
    assert result.model == "gpt-4.1-mini"


def test_openai_translator_provider_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """Translator should raise provider error when OpenAI request fails."""

    def _mock_post(_url: str, **_kwargs: object) -> _MockRequestsResponse:
        """Raise transport error for provider-failure path."""

        raise openai_http.requests.ConnectionError("network down")

    monkeypatch.setattr("bookvoice.llm.openai_client.requests.post", _mock_post)

    translator = OpenAITranslator(model="gpt-4.1-mini", provider_id="openai", api_key="key")
    chunk = Chunk(chapter_index=1, chunk_index=0, text="Hello world.", char_start=0, char_end=12)

    with pytest.raises(OpenAIProviderError, match="transport error"):
        translator.translate(chunk, target_language="cs")


def test_openai_rewriter_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """Rewriter should return OpenAI text output and preserve provider/model metadata."""

    def _mock_post(_url: str, **_kwargs: object) -> _MockRequestsResponse:
        """Return a mocked OpenAI rewrite response payload."""

        return _MockRequestsResponse(
            payload=json.dumps(
                {
                    "choices": [
                        {"message": {"content": "Ahoj svete, vitejte u poslechu."}},
                    ]
                }
            ).encode("utf-8")
        )

    monkeypatch.setattr("bookvoice.llm.openai_client.requests.post", _mock_post)

    chunk = Chunk(chapter_index=1, chunk_index=0, text="Hello world.", char_start=0, char_end=12)
    translation = TranslationResult(
        chunk=chunk,
        translated_text="Ahoj svete.",
        provider="openai",
        model="gpt-4.1-mini",
    )
    rewriter = AudioRewriter(model="gpt-4.1-mini", provider_id="openai", api_key="key")

    result = rewriter.rewrite(translation)

    assert result.rewritten_text == "Ahoj svete, vitejte u poslechu."
    assert result.provider == "openai"
    assert result.model == "gpt-4.1-mini"


def test_openai_rewriter_provider_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """Rewriter should raise provider error when OpenAI request fails."""

    def _mock_post(_url: str, **_kwargs: object) -> _MockRequestsResponse:
        """Raise HTTP error for provider-failure path."""

        return _MockRequestsResponse(
            status_code=401,
            payload=b'{"error":{"message":"invalid api key"}}',
        )

    monkeypatch.setattr("bookvoice.llm.openai_client.requests.post", _mock_post)

    chunk = Chunk(chapter_index=1, chunk_index=0, text="Hello world.", char_start=0, char_end=12)
    translation = TranslationResult(
        chunk=chunk,
        translated_text="Ahoj svete.",
        provider="openai",
        model="gpt-4.1-mini",
    )
    rewriter = AudioRewriter(model="gpt-4.1-mini", provider_id="openai", api_key="key")

    with pytest.raises(OpenAIProviderError, match="authentication failed") as exc_info:
        rewriter.rewrite(translation)
    assert exc_info.value.failure_kind == "invalid_api_key"


def test_openai_tts_happy_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """TTS synthesizer should write OpenAI WAV bytes and preserve provider metadata."""

    def _mock_post(_url: str, **_kwargs: object) -> _MockBinaryHTTPResponse:
        """Return a mocked OpenAI speech binary WAV response payload."""

        return _MockBinaryHTTPResponse(_mock_wav_bytes())

    monkeypatch.setattr("bookvoice.llm.openai_client.requests.post", _mock_post)

    chunk = Chunk(chapter_index=2, chunk_index=3, text="Hello world.", char_start=0, char_end=12)
    rewrite = RewriteResult(
        translation=TranslationResult(
            chunk=chunk,
            translated_text="Ahoj svete.",
            provider="openai",
            model="gpt-4.1-mini",
        ),
        rewritten_text="Ahoj svete.",
        provider="openai",
        model="gpt-4.1-mini",
    )
    synthesizer = OpenAITTSSynthesizer(
        output_root=tmp_path,
        model="gpt-4o-mini-tts",
        provider_id="openai",
        api_key="key",
    )

    part = synthesizer.synthesize(
        rewrite,
        VoiceProfile(
            name="alloy",
            provider_voice_id="alloy",
            language="cs",
            speaking_rate=1.0,
        ),
    )

    assert part.chapter_index == 2
    assert part.chunk_index == 3
    assert part.path == tmp_path / "002_04_chapter-002.wav"
    assert part.path.exists()
    assert part.duration_seconds > 0.0
    assert part.part_index == 4
    assert part.part_id == "002_04_chapter-002"
    assert part.provider == "openai"
    assert part.model == "gpt-4o-mini-tts"
    assert part.voice == "alloy"


def test_openai_tts_slugifies_non_ascii_part_titles(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """TTS synthesizer should emit deterministic ASCII slug filenames for non-ASCII titles."""

    def _mock_post(_url: str, **_kwargs: object) -> _MockBinaryHTTPResponse:
        """Return a mocked OpenAI speech binary WAV response payload."""

        return _MockBinaryHTTPResponse(_mock_wav_bytes())

    monkeypatch.setattr("bookvoice.llm.openai_client.requests.post", _mock_post)

    chunk = Chunk(
        chapter_index=1,
        chunk_index=0,
        text="Hello world.",
        char_start=0,
        char_end=12,
        part_index=1,
        part_title="Český název: Úvod!",
    )
    rewrite = RewriteResult(
        translation=TranslationResult(
            chunk=chunk,
            translated_text="Ahoj svete.",
            provider="openai",
            model="gpt-4.1-mini",
        ),
        rewritten_text="Ahoj svete.",
        provider="openai",
        model="gpt-4.1-mini",
    )
    synthesizer = OpenAITTSSynthesizer(
        output_root=tmp_path,
        model="gpt-4o-mini-tts",
        provider_id="openai",
        api_key="key",
    )

    part = synthesizer.synthesize(
        rewrite,
        VoiceProfile(
            name="alloy",
            provider_voice_id="alloy",
            language="cs",
            speaking_rate=1.0,
        ),
    )

    assert part.path == tmp_path / "001_01_cesky-nazev-uvod.wav"
    assert part.part_id == "001_01_cesky-nazev-uvod"


def test_openai_tts_provider_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """TTS synthesizer should raise provider error when OpenAI request fails."""

    def _mock_post(_url: str, **_kwargs: object) -> _MockRequestsResponse:
        """Raise HTTP error for provider-failure path."""

        return _MockRequestsResponse(
            status_code=401,
            payload=b'{"error":{"message":"invalid api key"}}',
        )

    monkeypatch.setattr("bookvoice.llm.openai_client.requests.post", _mock_post)

    with pytest.raises(OpenAIProviderError, match="authentication failed") as exc_info:
        OpenAISpeechClient(api_key="key").synthesize_speech(
            model="gpt-4o-mini-tts",
            voice="alloy",
            text="Ahoj svete.",
        )
    assert exc_info.value.failure_kind == "invalid_api_key"


def test_openai_client_classifies_quota_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """OpenAI client should classify HTTP 429 quota responses for diagnostics."""

    def _mock_post(_url: str, **_kwargs: object) -> _MockRequestsResponse:
        """Raise deterministic insufficient quota response."""

        return _MockRequestsResponse(
            status_code=429,
            payload=(
                b'{\"error\":{\"message\":\"You exceeded your current quota.\",'
                b'\"code\":\"insufficient_quota\"}}'
            ),
        )

    monkeypatch.setattr("bookvoice.llm.openai_client.requests.post", _mock_post)
    client = OpenAIChatClient(api_key="key")

    with pytest.raises(OpenAIProviderError, match="quota is insufficient") as exc_info:
        client.chat_completion_text(
            model="gpt-4.1-mini",
            system_prompt="system",
            user_prompt="user",
        )
    assert exc_info.value.failure_kind == "insufficient_quota"


def test_openai_client_handles_http_error_with_undecodable_body(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """OpenAI client should map HTTP errors even when body bytes cannot be decoded."""

    def _mock_post(_url: str, **_kwargs: object) -> _MockRequestsResponse:
        """Raise deterministic malformed HTTP error response."""

        return _MockRequestsResponse(
            status_code=500,
            payload=b"\xff\xfe\xfd",
        )

    monkeypatch.setattr("bookvoice.llm.openai_client.requests.post", _mock_post)
    client = OpenAIChatClient(api_key="key")

    with pytest.raises(
        OpenAIProviderError,
        match="OpenAI request failed \\(HTTP 500\\)",
    ) as exc_info:
        client.chat_completion_text(
            model="gpt-4.1-mini",
            system_prompt="system",
            user_prompt="user",
        )
    assert exc_info.value.failure_kind == "http_error"
    assert exc_info.value.status_code == 500


def test_openai_client_classifies_transport_error_as_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """OpenAI client should classify requests timeout transport failures."""

    def _mock_post(_url: str, **_kwargs: object) -> _MockRequestsResponse:
        """Raise deterministic timeout transport error."""

        raise openai_http.requests.Timeout("socket timed out")

    monkeypatch.setattr("bookvoice.llm.openai_client.requests.post", _mock_post)
    client = OpenAIChatClient(api_key="key")

    with pytest.raises(OpenAIProviderError, match="timed out") as exc_info:
        client.chat_completion_text(
            model="gpt-4.1-mini",
            system_prompt="system",
            user_prompt="user",
        )
    assert exc_info.value.failure_kind == "timeout"


def test_openai_client_classifies_transport_error_as_transport(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """OpenAI client should classify non-timeout transport failures as transport."""

    def _mock_post(_url: str, **_kwargs: object) -> _MockRequestsResponse:
        """Raise deterministic non-timeout transport error."""

        raise openai_http.requests.ConnectionError("temporary DNS failure")

    monkeypatch.setattr("bookvoice.llm.openai_client.requests.post", _mock_post)
    client = OpenAISpeechClient(api_key="key")

    with pytest.raises(OpenAIProviderError, match="transport error") as exc_info:
        client.synthesize_speech(
            model="gpt-4o-mini-tts",
            voice="alloy",
            text="Ahoj svete.",
        )
    assert exc_info.value.failure_kind == "transport"


def test_openai_speech_rejects_empty_response_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """OpenAI speech client should reject empty responses from shared transport helper."""

    def _mock_post(_url: str, **_kwargs: object) -> _MockBinaryHTTPResponse:
        """Return an empty binary payload."""

        return _MockBinaryHTTPResponse(b"")

    monkeypatch.setattr("bookvoice.llm.openai_client.requests.post", _mock_post)
    client = OpenAISpeechClient(api_key="key")

    with pytest.raises(OpenAIProviderError, match="OpenAI speech response is empty."):
        client.synthesize_speech(
            model="gpt-4o-mini-tts",
            voice="alloy",
            text="Ahoj svete.",
        )


def test_pipeline_maps_translate_invalid_key_to_stage_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pipeline should map invalid API key failures to translate stage diagnostics."""

    def _failing_chat_completion(self, **kwargs: object) -> str:
        """Raise deterministic provider error for stage-mapping assertions."""

        _ = self
        _ = kwargs
        raise OpenAIProviderError("auth failed", failure_kind="invalid_api_key")

    monkeypatch.setattr(OpenAIChatClient, "chat_completion_text", _failing_chat_completion)
    pipeline = BookvoicePipeline()
    config = BookvoiceConfig(input_pdf=Path("in.pdf"), output_dir=Path("out"), api_key="key")
    chunk = Chunk(chapter_index=1, chunk_index=0, text="Text", char_start=0, char_end=4)

    with pytest.raises(PipelineStageError, match="authentication failed") as exc_info:
        pipeline._translate([chunk], config)
    assert exc_info.value.stage == "translate"
    assert "bookvoice credentials" in (exc_info.value.hint or "")


def test_pipeline_maps_translate_quota_to_stage_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pipeline should map quota failures to actionable translate stage diagnostics."""

    def _failing_chat_completion(self, **kwargs: object) -> str:
        """Raise deterministic provider error for stage-mapping assertions."""

        _ = self
        _ = kwargs
        raise OpenAIProviderError("quota", failure_kind="insufficient_quota")

    monkeypatch.setattr(OpenAIChatClient, "chat_completion_text", _failing_chat_completion)
    pipeline = BookvoicePipeline()
    config = BookvoiceConfig(input_pdf=Path("in.pdf"), output_dir=Path("out"), api_key="key")
    chunk = Chunk(chapter_index=1, chunk_index=0, text="Text", char_start=0, char_end=4)

    with pytest.raises(PipelineStageError, match="quota is insufficient") as exc_info:
        pipeline._translate([chunk], config)
    assert exc_info.value.stage == "translate"
    assert "billing/quota" in (exc_info.value.hint or "")


def test_pipeline_maps_rewrite_invalid_model_to_stage_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pipeline should map invalid model failures to rewrite stage diagnostics."""

    def _failing_chat_completion(self, **kwargs: object) -> str:
        """Raise deterministic provider error for stage-mapping assertions."""

        _ = self
        _ = kwargs
        raise OpenAIProviderError("model rejected", failure_kind="invalid_model")

    monkeypatch.setattr(OpenAIChatClient, "chat_completion_text", _failing_chat_completion)
    pipeline = BookvoicePipeline()
    config = BookvoiceConfig(input_pdf=Path("in.pdf"), output_dir=Path("out"), api_key="key")
    chunk = Chunk(chapter_index=1, chunk_index=0, text="Text", char_start=0, char_end=4)
    translation = TranslationResult(
        chunk=chunk,
        translated_text="Ahoj",
        provider="openai",
        model="gpt-4.1-mini",
    )

    with pytest.raises(PipelineStageError, match="configured model") as exc_info:
        pipeline._rewrite_for_audio([translation], config)
    assert exc_info.value.stage == "rewrite"
    assert "--model-rewrite" in (exc_info.value.hint or "")
    assert "--rewrite-bypass" in (exc_info.value.hint or "")


def test_pipeline_maps_tts_timeout_to_stage_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Pipeline should map timeout failures to TTS stage diagnostics."""

    def _failing_speech(self, **kwargs: object) -> bytes:
        """Raise deterministic provider error for stage-mapping assertions."""

        _ = self
        _ = kwargs
        raise OpenAIProviderError("timeout", failure_kind="timeout")

    monkeypatch.setattr(OpenAISpeechClient, "synthesize_speech", _failing_speech)
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

    with pytest.raises(PipelineStageError, match="timed out") as exc_info:
        pipeline._tts([rewrite], config, store=ArtifactStore(tmp_path / "run"))
    assert exc_info.value.stage == "tts"
    assert "Retry the command" in (exc_info.value.hint or "")


def test_pipeline_rewrite_bypass_returns_deterministic_pass_through() -> None:
    """Rewrite bypass mode should preserve translated text with explicit bypass metadata."""

    pipeline = BookvoicePipeline()
    config = BookvoiceConfig(
        input_pdf=Path("in.pdf"),
        output_dir=Path("out"),
        rewrite_bypass=True,
    )
    chunk = Chunk(chapter_index=1, chunk_index=0, text="Text", char_start=0, char_end=4)
    translation = TranslationResult(
        chunk=chunk,
        translated_text="Ahoj",
        provider="openai",
        model="gpt-4.1-mini",
    )

    rewrites = pipeline._rewrite_for_audio([translation], config)

    assert rewrites[0].rewritten_text == "Ahoj"
    assert rewrites[0].provider == "bypass"
    assert rewrites[0].model == "deterministic-pass-through-v1"
