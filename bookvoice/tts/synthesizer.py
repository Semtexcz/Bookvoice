"""TTS synthesizer interfaces and OpenAI-backed implementation.

Responsibilities:
- Define protocol for chunk-level speech synthesis.
- Provide OpenAI-backed chunk-level speech synthesis.
"""

from __future__ import annotations

import io
import re
import unicodedata
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
        part_index = chunk.part_index if chunk.part_index is not None else chunk.chunk_index + 1
        part_title = chunk.part_title if chunk.part_title else f"chapter-{chunk.chapter_index:03d}"
        slug = self._slugify(part_title)
        relative = Path(f"{chunk.chapter_index:03d}_{part_index:02d}_{slug}.wav")
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
            part_index=part_index,
            part_title=part_title,
            part_id=(
                chunk.part_id
                if chunk.part_id
                else f"{chunk.chapter_index:03d}_{part_index:02d}_{slug}"
            ),
            source_order_indices=chunk.source_order_indices,
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

    def _slugify(self, value: str) -> str:
        """Create deterministic filesystem-safe ASCII slug from a title string."""

        normalized = unicodedata.normalize("NFKD", value)
        ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
        lowered = ascii_only.lower().strip()
        collapsed = re.sub(r"[^a-z0-9]+", "-", lowered)
        slug = collapsed.strip("-")
        return slug or "part"
