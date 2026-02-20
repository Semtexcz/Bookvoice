"""Chapter splitting logic scaffold.

Responsibilities:
- Convert cleaned book text into chapter objects.
- Preserve deterministic chapter ordering and indexing.
"""

from __future__ import annotations

from ..models.datatypes import Chapter


class ChapterSplitter:
    """Split raw book text into chapter records."""

    def split(self, text: str) -> list[Chapter]:
        """Split text into chapters.

        This stub returns a single chapter when text is non-empty.
        """

        if not text:
            return []
        return [Chapter(index=1, title="Chapter 1", text=text)]
