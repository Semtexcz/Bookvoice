"""TTS synthesizer interfaces and OpenAI-backed implementation.

Responsibilities:
- Define protocol for chunk-level speech synthesis.
- Provide OpenAI-backed chunk-level speech synthesis.
"""

from __future__ import annotations

import io
import wave
from pathlib import Path
from typing import Protocol

from ..llm.openai_client import OpenAIProviderError, OpenAISpeechClient
from ..models.datatypes import AudioPart, RewriteResult
from .voices import VoiceProfile


class TTSSynthesizer(Protocol):
    """Protocol for TTS provider implementations."""

    def synthesize(self, rewrite: RewriteResult, voice: VoiceProfile) -> AudioPart:
        """Synthesize one audio part from rewritten text."""


class OpenAITTSSynthesizer:
    """OpenAI-backed synthesizer that writes deterministic chunk WAV artifacts."""

    def __init__(
        self,
        output_root: Path | None = None,
        model: str = "gpt-4o-mini-tts",
        provider_id: str = "openai",
        api_key: str | None = None,
    ) -> None:
        """Initialize OpenAI-backed TTS synthesizer settings."""

        self.output_root = output_root
        self.model = model
        self.provider_id = provider_id
        self.client = OpenAISpeechClient(api_key=api_key)

    def synthesize(self, rewrite: RewriteResult, voice: VoiceProfile) -> AudioPart:
        """Synthesize one OpenAI WAV file and return deterministic chunk metadata."""

        chunk = rewrite.translation.chunk
        relative = Path(
            f"chapter_{chunk.chapter_index:03d}_chunk_{chunk.chunk_index:03d}.wav"
        )
        output_path = relative if self.output_root is None else self.output_root / relative
        audio_bytes = self.client.synthesize_speech(
            model=self.model,
            voice=voice.provider_voice_id,
            text=rewrite.rewritten_text,
            response_format="wav",
            speed=max(0.25, min(4.0, voice.speaking_rate)),
        )
        duration = self._wav_duration_seconds(audio_bytes)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(audio_bytes)
        return AudioPart(
            chapter_index=chunk.chapter_index,
            chunk_index=chunk.chunk_index,
            path=output_path,
            duration_seconds=duration,
            provider=self.provider_id,
            model=self.model,
            voice=voice.provider_voice_id,
        )

    def _wav_duration_seconds(self, audio_bytes: bytes) -> float:
        """Compute WAV duration in seconds from OpenAI speech response bytes."""

        try:
            with wave.open(io.BytesIO(audio_bytes), "rb") as wav_file:
                frame_count = wav_file.getnframes()
                sample_rate = wav_file.getframerate()
        except Exception as exc:
            raise OpenAIProviderError(
                "OpenAI speech response is not a readable WAV payload."
            ) from exc
        if sample_rate <= 0:
            raise OpenAIProviderError("OpenAI speech response has invalid WAV sample rate.")
        return frame_count / float(sample_rate)
