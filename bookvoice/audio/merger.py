"""Audio merge stage scaffold.

Responsibilities:
- Merge chunk/chapter audio parts into final outputs.
- Preserve deterministic ordering by chapter and chunk indices.
"""

from __future__ import annotations

import wave
from pathlib import Path

from ..models.datatypes import AudioPart


class AudioMerger:
    """Merge WAV audio parts into one deterministic WAV output."""

    def merge(self, audio_parts: list[AudioPart], output_path: Path) -> Path:
        """Merge ordered audio parts into one output file."""

        output_path.parent.mkdir(parents=True, exist_ok=True)

        ordered_parts = sorted(
            audio_parts,
            key=lambda item: (item.chapter_index, item.chunk_index),
        )

        if not ordered_parts:
            with wave.open(str(output_path), "wb") as merged:
                merged.setnchannels(1)
                merged.setsampwidth(2)
                merged.setframerate(24000)
                merged.writeframes(b"")
            return output_path

        with wave.open(str(ordered_parts[0].path), "rb") as first:
            channels = first.getnchannels()
            sample_width = first.getsampwidth()
            framerate = first.getframerate()

        with wave.open(str(output_path), "wb") as merged:
            merged.setnchannels(channels)
            merged.setsampwidth(sample_width)
            merged.setframerate(framerate)

            for part in ordered_parts:
                with wave.open(str(part.path), "rb") as chunk:
                    if (
                        chunk.getnchannels() != channels
                        or chunk.getsampwidth() != sample_width
                        or chunk.getframerate() != framerate
                    ):
                        raise ValueError(
                            f"Incompatible WAV parameters for chunk: {part.path}"
                        )
                    merged.writeframes(chunk.readframes(chunk.getnframes()))

        return output_path
