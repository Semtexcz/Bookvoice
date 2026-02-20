"""Audio merge stage scaffold.

Responsibilities:
- Merge chunk/chapter audio parts into final outputs.
- Preserve deterministic ordering by chapter and chunk indices.
"""

from __future__ import annotations

from pathlib import Path

from ..models.datatypes import AudioPart


class AudioMerger:
    """Placeholder merger for audio parts."""

    def merge(self, audio_parts: list[AudioPart], output_path: Path) -> Path:
        """Merge ordered audio parts into one output file."""

        _ = audio_parts
        return output_path
