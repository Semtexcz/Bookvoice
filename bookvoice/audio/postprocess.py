"""Audio postprocessing stage scaffold.

Responsibilities:
- Define normalization and silence-trimming operations.
- Keep postprocessing deterministic and auditable.
"""

from __future__ import annotations

from pathlib import Path


class AudioPostProcessor:
    """Placeholder audio postprocessing service."""

    def normalize(self, audio_path: Path) -> Path:
        """Normalize loudness for an audio file and return output path."""

        return audio_path

    def trim_silence(self, audio_path: Path) -> Path:
        """Trim leading/trailing silence and return output path."""

        return audio_path
