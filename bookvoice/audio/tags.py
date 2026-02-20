"""Audio metadata tagging scaffold.

Responsibilities:
- Write audiobook metadata tags to final artifacts.
- Keep tagging logic separate from merge processing.
"""

from __future__ import annotations

from pathlib import Path

from ..models.datatypes import BookMeta


class MetadataWriter:
    """Placeholder ID3 metadata writer."""

    def write_id3(self, audio_path: Path, book: BookMeta) -> Path:
        """Write ID3 tags and return the tagged audio path."""

        _ = book
        return audio_path
