"""TTS synthesizer interfaces and stubs.

Responsibilities:
- Define protocol for chunk-level speech synthesis.
- Provide placeholder provider implementation for future integration.
"""

from __future__ import annotations

import io
import math
import struct
import wave
from pathlib import Path
from typing import Protocol

from ..models.datatypes import AudioPart, RewriteResult
from .voices import VoiceProfile


class TTSSynthesizer(Protocol):
    """Protocol for TTS provider implementations."""

    def synthesize(self, rewrite: RewriteResult, voice: VoiceProfile) -> AudioPart:
        """Synthesize one audio part from rewritten text."""


class OpenAITTSSynthesizer:
    """Minimal local synthesizer that writes deterministic WAV chunks."""

    def __init__(self, output_root: Path | None = None, sample_rate: int = 24000) -> None:
        self.output_root = output_root
        self.sample_rate = sample_rate

    def synthesize(self, rewrite: RewriteResult, voice: VoiceProfile) -> AudioPart:
        """Synthesize one deterministic WAV file and return metadata."""

        chunk = rewrite.translation.chunk
        relative = Path(
            f"chapter_{chunk.chapter_index:03d}_chunk_{chunk.chunk_index:03d}.wav"
        )
        output_path = relative if self.output_root is None else self.output_root / relative
        audio_bytes, duration = self._render_wav(
            text=rewrite.rewritten_text,
            speaking_rate=voice.speaking_rate,
            chapter_index=chunk.chapter_index,
            chunk_index=chunk.chunk_index,
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(audio_bytes)
        return AudioPart(
            chapter_index=chunk.chapter_index,
            chunk_index=chunk.chunk_index,
            path=output_path,
            duration_seconds=duration,
        )

    def _render_wav(
        self, text: str, speaking_rate: float, chapter_index: int, chunk_index: int
    ) -> tuple[bytes, float]:
        base_duration = max(0.25, min(6.0, len(text) / 50.0))
        duration = base_duration / max(0.5, speaking_rate)
        frame_count = int(duration * self.sample_rate)
        frequency = 220.0 + float((chapter_index * 31 + chunk_index * 17) % 180)
        amplitude = 0.20

        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(self.sample_rate)

            frames = bytearray()
            for frame_index in range(frame_count):
                sample = amplitude * math.sin(
                    (2.0 * math.pi * frequency * frame_index) / self.sample_rate
                )
                frames.extend(struct.pack("<h", int(sample * 32767)))
            wav_file.writeframes(bytes(frames))

        return buffer.getvalue(), frame_count / float(self.sample_rate)
