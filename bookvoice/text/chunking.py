"""Chapter-to-chunk segmentation logic.

Responsibilities:
- Split chapter text into bounded chunks for provider calls.
- Preserve index metadata required for deterministic reassembly.
"""

from __future__ import annotations

from ..models.datatypes import Chapter, Chunk


class Chunker:
    """Create fixed-size character chunks from chapters."""

    _MIN_BOUNDARY_RATIO = 0.60

    def to_chunks(self, chapters: list[Chapter], target_size: int) -> list[Chunk]:
        """Split chapter texts into chunk records.

        Args:
            chapters: Ordered chapter list.
            target_size: Desired maximum chunk length in characters.

        Returns:
            Generated chunk list preserving chapter/chunk indices.
        """

        if target_size <= 0:
            return []

        chunks: list[Chunk] = []
        for chapter in chapters:
            text = chapter.text
            chunk_index = 0
            start = 0
            text_length = len(text)
            while start < text_length:
                end = min(start + target_size, text_length)
                end = self._prefer_boundary(text, start, end, target_size)
                chunks.append(
                    Chunk(
                        chapter_index=chapter.index,
                        chunk_index=chunk_index,
                        text=text[start:end],
                        char_start=start,
                        char_end=end,
                    )
                )
                chunk_index += 1
                start = end
        return chunks

    def _prefer_boundary(self, text: str, start: int, end: int, target_size: int) -> int:
        """Shift split left to a natural delimiter when close to target size."""

        if end >= len(text):
            return end

        window = text[start:end]
        min_boundary = int(target_size * self._MIN_BOUNDARY_RATIO)
        for delimiter in ("\n\n", "\n", " "):
            boundary_pos = window.rfind(delimiter)
            if boundary_pos >= min_boundary:
                adjusted = start + boundary_pos + len(delimiter)
                if adjusted > start:
                    return adjusted
        return end
