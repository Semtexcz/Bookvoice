"""Chapter-to-chunk segmentation logic.

Responsibilities:
- Split chapter text into bounded chunks for provider calls.
- Preserve index metadata required for deterministic reassembly.
"""

from __future__ import annotations

import re

from ..models.datatypes import Chapter, Chunk


class Chunker:
    """Create sentence-complete chunks from chapters with deterministic fallback."""

    _MIN_BOUNDARY_RATIO = 0.60
    _MAX_EXTENSION_RATIO = 0.35
    _TRAILING_SENTENCE_CLOSERS = "\"')]}»”"
    _COMMON_ABBREVIATIONS = frozenset(
        {
            "mr.",
            "mrs.",
            "ms.",
            "dr.",
            "prof.",
            "sr.",
            "jr.",
            "st.",
            "etc.",
            "e.g.",
            "i.e.",
            "vs.",
            "no.",
            "fig.",
            "al.",
        }
    )
    _ACRONYM_PATTERN = re.compile(r"(?:[A-Za-z]\.){2,}$")

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
                end, boundary_strategy = self._resolve_boundary(text, start, target_size)
                chunks.append(
                    Chunk(
                        chapter_index=chapter.index,
                        chunk_index=chunk_index,
                        text=text[start:end],
                        char_start=start,
                        char_end=end,
                        boundary_strategy=boundary_strategy,
                    )
                )
                chunk_index += 1
                start = end
        return chunks

    def _resolve_boundary(
        self,
        text: str,
        start: int,
        target_size: int,
    ) -> tuple[int, str]:
        """Resolve chunk end index and boundary strategy marker."""

        text_length = len(text)
        if start + target_size >= text_length:
            return text_length, "chapter_end"

        target_end = min(start + target_size, text_length)
        min_boundary = start + int(target_size * self._MIN_BOUNDARY_RATIO)

        backward_boundary = self._find_backward_sentence_boundary(
            text=text,
            start=start,
            target_end=target_end,
            min_boundary=min_boundary,
        )
        if backward_boundary is not None:
            return backward_boundary, "sentence_complete"

        extension_budget = max(1, int(target_size * self._MAX_EXTENSION_RATIO))
        extension_limit = min(text_length, target_end + extension_budget)

        forward_boundary = self._find_forward_sentence_boundary(
            text=text,
            from_index=target_end,
            extension_limit=extension_limit,
        )
        if forward_boundary is not None:
            return forward_boundary, "sentence_complete"

        fallback_boundary = self._fallback_boundary(text, start, target_end, extension_limit)
        return fallback_boundary, "forced_split_no_sentence_boundary"

    def _find_backward_sentence_boundary(
        self,
        text: str,
        start: int,
        target_end: int,
        min_boundary: int,
    ) -> int | None:
        """Find nearest acceptable sentence boundary before target end."""

        for punctuation in (".", "!", "?"):
            index = target_end - 1
            while index >= max(start, min_boundary):
                if text[index] == punctuation and self._is_sentence_boundary(text, index):
                    return self._consume_trailing_sentence_tail(text, index + 1)
                index -= 1
        return None

    def _find_forward_sentence_boundary(
        self,
        text: str,
        from_index: int,
        extension_limit: int,
    ) -> int | None:
        """Find next acceptable sentence boundary after target end within safety margin."""

        if extension_limit <= from_index:
            return None

        for punctuation in (".", "!", "?"):
            index = from_index
            while index < extension_limit:
                if text[index] == punctuation and self._is_sentence_boundary(text, index):
                    return self._consume_trailing_sentence_tail(text, index + 1)
                index += 1
        return None

    def _is_sentence_boundary(self, text: str, punctuation_index: int) -> bool:
        """Return whether punctuation at index terminates a sentence."""

        punctuation = text[punctuation_index]
        if punctuation != ".":
            return True
        if self._is_decimal_period(text, punctuation_index):
            return False
        if self._is_abbreviation_period(text, punctuation_index):
            return False
        return True

    def _is_decimal_period(self, text: str, punctuation_index: int) -> bool:
        """Return whether a period is part of a decimal number."""

        if punctuation_index <= 0 or punctuation_index + 1 >= len(text):
            return False
        return text[punctuation_index - 1].isdigit() and text[punctuation_index + 1].isdigit()

    def _is_abbreviation_period(self, text: str, punctuation_index: int) -> bool:
        """Return whether a period belongs to a likely abbreviation token."""

        start = punctuation_index
        while start > 0 and text[start - 1].isalpha():
            start -= 1
        token = text[start : punctuation_index + 1].lower()
        if token in self._COMMON_ABBREVIATIONS:
            return True

        acronym_start = max(0, punctuation_index - 8)
        acronym_window = text[acronym_start : punctuation_index + 1]
        return bool(self._ACRONYM_PATTERN.search(acronym_window))

    def _consume_trailing_sentence_tail(self, text: str, index: int) -> int:
        """Consume trailing closing punctuation and whitespace after sentence end."""

        adjusted = index
        text_length = len(text)
        while adjusted < text_length and text[adjusted] in self._TRAILING_SENTENCE_CLOSERS:
            adjusted += 1
        while adjusted < text_length and text[adjusted].isspace():
            adjusted += 1
        return adjusted

    def _fallback_boundary(
        self,
        text: str,
        start: int,
        target_end: int,
        extension_limit: int,
    ) -> int:
        """Return deterministic split index for punctuation-free pathological text."""

        for index in range(target_end, extension_limit):
            if text[index].isspace():
                return index + 1

        for index in range(target_end - 1, start, -1):
            if text[index].isspace():
                return index + 1

        return extension_limit if extension_limit > start else target_end
