"""Text normalization stage scaffold.

Responsibilities:
- Apply canonical text formatting before chunking and translation.
- Keep normalization deterministic and locale-aware.
"""

from __future__ import annotations


class TextNormalizer:
    """Normalize cleaned text into canonical internal representation."""

    def normalize(self, text: str) -> str:
        """Normalize text for downstream deterministic processing."""

        return text.strip()
