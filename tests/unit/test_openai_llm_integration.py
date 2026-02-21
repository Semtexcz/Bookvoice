"""Unit tests for OpenAI-backed translation and rewrite integrations."""

from __future__ import annotations

import io
import json
from pathlib import Path
from urllib import error

import pytest

from bookvoice.config import BookvoiceConfig
from bookvoice.errors import PipelineStageError
from bookvoice.llm.audio_rewriter import AudioRewriter
from bookvoice.llm.openai_client import OpenAIChatClient, OpenAIProviderError
from bookvoice.llm.translator import OpenAITranslator
from bookvoice.models.datatypes import Chunk, TranslationResult
from bookvoice.pipeline import BookvoicePipeline


class _MockHTTPResponse:
    """Minimal context-managed HTTP response mock for urlopen patching."""

    def __init__(self, payload: dict[str, object]) -> None:
        """Initialize response with JSON payload."""

        self._payload = json.dumps(payload).encode("utf-8")

    def __enter__(self) -> _MockHTTPResponse:
        """Return self for context manager entry."""

        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        """Propagate exceptions raised inside context manager block."""

        _ = exc_type
        _ = exc
        _ = tb
        return False

    def read(self) -> bytes:
        """Return serialized JSON bytes."""

        return self._payload


def test_openai_translator_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """Translator should return OpenAI text output and preserve provider/model metadata."""

    def _mock_urlopen(_request, timeout: float = 0.0) -> _MockHTTPResponse:
        """Return a mocked OpenAI chat-completions response."""

        _ = timeout
        return _MockHTTPResponse(
            {
                "choices": [
                    {"message": {"content": "Ahoj svete."}},
                ]
            }
        )

    monkeypatch.setattr("bookvoice.llm.openai_client.request.urlopen", _mock_urlopen)

    translator = OpenAITranslator(model="gpt-4.1-mini", provider_id="openai", api_key="key")
    chunk = Chunk(chapter_index=1, chunk_index=0, text="Hello world.", char_start=0, char_end=12)

    result = translator.translate(chunk, target_language="cs")

    assert result.translated_text == "Ahoj svete."
    assert result.provider == "openai"
    assert result.model == "gpt-4.1-mini"


def test_openai_translator_provider_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """Translator should raise provider error when OpenAI request fails."""

    def _mock_urlopen(_request, timeout: float = 0.0):
        """Raise transport error for provider-failure path."""

        _ = timeout
        raise error.URLError("network down")

    monkeypatch.setattr("bookvoice.llm.openai_client.request.urlopen", _mock_urlopen)

    translator = OpenAITranslator(model="gpt-4.1-mini", provider_id="openai", api_key="key")
    chunk = Chunk(chapter_index=1, chunk_index=0, text="Hello world.", char_start=0, char_end=12)

    with pytest.raises(OpenAIProviderError, match="transport error"):
        translator.translate(chunk, target_language="cs")


def test_openai_rewriter_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """Rewriter should return OpenAI text output and preserve provider/model metadata."""

    def _mock_urlopen(_request, timeout: float = 0.0) -> _MockHTTPResponse:
        """Return a mocked OpenAI rewrite response payload."""

        _ = timeout
        return _MockHTTPResponse(
            {
                "choices": [
                    {"message": {"content": "Ahoj svete, vitejte u poslechu."}},
                ]
            }
        )

    monkeypatch.setattr("bookvoice.llm.openai_client.request.urlopen", _mock_urlopen)

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

    def _mock_urlopen(_request, timeout: float = 0.0):
        """Raise HTTP error for provider-failure path."""

        _ = timeout
        raise error.HTTPError(
            url="https://api.openai.com/v1/chat/completions",
            code=401,
            msg="Unauthorized",
            hdrs=None,
            fp=io.BytesIO(b'{"error":{"message":"invalid api key"}}'),
        )

    monkeypatch.setattr("bookvoice.llm.openai_client.request.urlopen", _mock_urlopen)

    chunk = Chunk(chapter_index=1, chunk_index=0, text="Hello world.", char_start=0, char_end=12)
    translation = TranslationResult(
        chunk=chunk,
        translated_text="Ahoj svete.",
        provider="openai",
        model="gpt-4.1-mini",
    )
    rewriter = AudioRewriter(model="gpt-4.1-mini", provider_id="openai", api_key="key")

    with pytest.raises(OpenAIProviderError, match="HTTP 401"):
        rewriter.rewrite(translation)


def test_pipeline_maps_translate_provider_failure_to_stage_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pipeline should surface translation provider failures as translate stage errors."""

    def _failing_chat_completion(self, **kwargs: object) -> str:
        """Raise deterministic provider error for stage-mapping assertions."""

        _ = self
        _ = kwargs
        raise OpenAIProviderError("boom")

    monkeypatch.setattr(OpenAIChatClient, "chat_completion_text", _failing_chat_completion)
    pipeline = BookvoicePipeline()
    config = BookvoiceConfig(input_pdf=Path("in.pdf"), output_dir=Path("out"), api_key="key")
    chunk = Chunk(chapter_index=1, chunk_index=0, text="Text", char_start=0, char_end=4)

    with pytest.raises(PipelineStageError, match="boom") as exc_info:
        pipeline._translate([chunk], config)
    assert exc_info.value.stage == "translate"
    assert "OPENAI_API_KEY" in (exc_info.value.hint or "")


def test_pipeline_maps_rewrite_provider_failure_to_stage_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pipeline should surface rewrite provider failures as rewrite stage errors."""

    def _failing_chat_completion(self, **kwargs: object) -> str:
        """Raise deterministic provider error for stage-mapping assertions."""

        _ = self
        _ = kwargs
        raise OpenAIProviderError("boom")

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

    with pytest.raises(PipelineStageError, match="boom") as exc_info:
        pipeline._rewrite_for_audio([translation], config)
    assert exc_info.value.stage == "rewrite"
    assert "--rewrite-bypass" in (exc_info.value.hint or "")


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
