"""Integration-test fixtures for deterministic provider behavior."""

from __future__ import annotations

import io
import wave

import pytest

from bookvoice.llm.openai_client import OpenAIChatClient, OpenAISpeechClient


@pytest.fixture(autouse=True)
def _mock_openai_llm_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock OpenAI LLM calls in integration tests to avoid network/key requirements."""

    def _mock_chat_completion(self, **kwargs: object) -> str:
        """Return deterministic placeholder text for translation and rewrite stages."""

        _ = self
        _ = kwargs
        return "integration-mocked-llm-text"

    def _mock_synthesize_speech(self, **kwargs: object) -> bytes:
        """Return deterministic placeholder WAV payload for TTS stage."""

        _ = self
        _ = kwargs
        frame_count = 2400
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(24000)
            wav_file.writeframes(b"\x00\x00" * frame_count)
        return buffer.getvalue()

    monkeypatch.setattr(OpenAIChatClient, "chat_completion_text", _mock_chat_completion)
    monkeypatch.setattr(OpenAISpeechClient, "synthesize_speech", _mock_synthesize_speech)
