"""Chapter-to-chunk segmentation logic.

Responsibilities:
- Split chapter text into bounded chunks for provider calls.
- Preserve index metadata required for deterministic reassembly.
"""

from __future__ import annotations

from ..models.datatypes import Chapter, Chunk


class Chunker:
    """Create fixed-size character chunks from chapters."""

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
            for start in range(0, len(text), target_size):
                end = min(start + target_size, len(text))
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
        return chunks
