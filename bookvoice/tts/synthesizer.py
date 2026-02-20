"""TTS synthesizer interfaces and stubs.

Responsibilities:
- Define protocol for chunk-level speech synthesis.
- Provide placeholder provider implementation for future integration.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from ..models.datatypes import AudioPart, RewriteResult
from .voices import VoiceProfile


class TTSSynthesizer(Protocol):
    """Protocol for TTS provider implementations."""

    def synthesize(self, rewrite: RewriteResult, voice: VoiceProfile) -> AudioPart:
        """Synthesize one audio part from rewritten text."""


class OpenAITTSSynthesizer:
    """Stub synthesizer for future OpenAI TTS integration."""

    def synthesize(self, rewrite: RewriteResult, voice: VoiceProfile) -> AudioPart:
        """Return a placeholder audio-part metadata object."""

        _ = voice
        chunk = rewrite.translation.chunk
        return AudioPart(
            chapter_index=chunk.chapter_index,
            chunk_index=chunk.chunk_index,
            path=Path(f"chapter_{chunk.chapter_index:03d}_chunk_{chunk.chunk_index:03d}.wav"),
            duration_seconds=0.0,
        )
