"""Chapter-to-chunk segmentation logic.

Responsibilities:
- Split chapter text into bounded chunks for provider calls.
- Preserve index metadata required for deterministic reassembly.
"""

from __future__ import annotations

from dataclasses import dataclass
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


@dataclass(frozen=True, slots=True)
class ChunkBoundaryRepairReport:
    """Result of deterministic sentence-boundary chunk repair."""

    chunks: list[Chunk]
    sentence_boundary_repairs_count: int


class SentenceBoundaryRepairer:
    """Repair chunk boundaries when deterministic chunking still splits mid-sentence."""

    _TRAILING_SENTENCE_CLOSERS = "\"')]}»”"
    _OPENING_QUOTES = "\"'([{«“"
    _CONTINUATION_HEAD_RE = re.compile(r"^[a-z]")
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

    def __init__(self, max_extension_chars: int) -> None:
        """Initialize repairer with deterministic per-boundary extension guard."""

        self.max_extension_chars = max(1, max_extension_chars)

    def repair(self, chunks: list[Chunk], target_size: int) -> ChunkBoundaryRepairReport:
        """Repair unfinished sentence boundaries using bounded carry-over from the next chunk."""

        if target_size <= 0 or len(chunks) < 2:
            return ChunkBoundaryRepairReport(
                chunks=list(chunks),
                sentence_boundary_repairs_count=0,
            )

        repaired = list(chunks)
        repairs_count = 0
        index = 0
        while index < len(repaired) - 1:
            previous = repaired[index]
            current = repaired[index + 1]
            if previous.chapter_index != current.chapter_index:
                index += 1
                continue
            if not self._is_repair_candidate(previous.text, current.text):
                index += 1
                continue

            extension_allowance = target_size + self.max_extension_chars - len(previous.text)
            if extension_allowance <= 0:
                index += 1
                continue
            carry_over = self._extract_sentence_continuation(
                text=current.text,
                max_chars=min(extension_allowance, len(current.text)),
            )
            if carry_over is None or not carry_over.strip():
                index += 1
                continue
            if len(carry_over) >= len(current.text):
                index += 1
                continue

            repaired_previous = Chunk(
                chapter_index=previous.chapter_index,
                chunk_index=previous.chunk_index,
                text=f"{previous.text}{carry_over}",
                char_start=previous.char_start,
                char_end=previous.char_end + len(carry_over),
                part_index=previous.part_index,
                part_title=previous.part_title,
                part_id=previous.part_id,
                source_order_indices=previous.source_order_indices,
                boundary_strategy="sentence_boundary_repaired",
            )
            repaired_current = Chunk(
                chapter_index=current.chapter_index,
                chunk_index=current.chunk_index,
                text=current.text[len(carry_over) :],
                char_start=current.char_start + len(carry_over),
                char_end=current.char_end,
                part_index=current.part_index,
                part_title=current.part_title,
                part_id=current.part_id,
                source_order_indices=current.source_order_indices,
                boundary_strategy=current.boundary_strategy,
            )
            repaired[index] = repaired_previous
            repaired[index + 1] = repaired_current
            repairs_count += 1
            index += 1

        return ChunkBoundaryRepairReport(
            chunks=repaired,
            sentence_boundary_repairs_count=repairs_count,
        )

    def _is_repair_candidate(self, previous_text: str, current_text: str) -> bool:
        """Return whether adjacent chunk text strongly indicates mid-sentence split."""

        if self._ends_with_sentence_terminator(previous_text):
            return False
        if self._starts_with_continuation(current_text):
            return True
        return self._has_unmatched_quote(previous_text)

    def _starts_with_continuation(self, text: str) -> bool:
        """Return whether text starts with a likely continuation token."""

        stripped = text.lstrip()
        if not stripped:
            return False
        if self._CONTINUATION_HEAD_RE.match(stripped):
            return True
        if stripped[0] in ",;:)":
            return True
        if stripped[0] in self._OPENING_QUOTES and len(stripped) > 1:
            return bool(self._CONTINUATION_HEAD_RE.match(stripped[1:]))
        return False

    def _ends_with_sentence_terminator(self, text: str) -> bool:
        """Return whether text ends with a sentence terminator after trailing closers."""

        trimmed = text.rstrip()
        while trimmed and trimmed[-1] in self._TRAILING_SENTENCE_CLOSERS:
            trimmed = trimmed[:-1]
            trimmed = trimmed.rstrip()
        return bool(trimmed and trimmed[-1] in ".!?")

    def _has_unmatched_quote(self, text: str) -> bool:
        """Return whether text has unmatched straight double quotes."""

        return text.count('"') % 2 == 1

    def _extract_sentence_continuation(self, text: str, max_chars: int) -> str | None:
        """Extract minimal prefix from `text` that completes the current sentence."""

        if max_chars <= 0:
            return None

        limit = min(max_chars, len(text))
        index = 0
        while index < limit:
            punctuation = text[index]
            if punctuation in ".!?" and self._is_sentence_boundary(text, index):
                end = self._consume_trailing_sentence_tail(text, index + 1, limit)
                return text[:end]
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
        """Return whether period belongs to a decimal number token."""

        if punctuation_index <= 0 or punctuation_index + 1 >= len(text):
            return False
        return text[punctuation_index - 1].isdigit() and text[punctuation_index + 1].isdigit()

    def _is_abbreviation_period(self, text: str, punctuation_index: int) -> bool:
        """Return whether period belongs to an abbreviation or acronym token."""

        start = punctuation_index
        while start > 0 and text[start - 1].isalpha():
            start -= 1
        token = text[start : punctuation_index + 1].lower()
        if token in self._COMMON_ABBREVIATIONS:
            return True
        acronym_start = max(0, punctuation_index - 8)
        acronym_window = text[acronym_start : punctuation_index + 1]
        return bool(self._ACRONYM_PATTERN.search(acronym_window))

    def _consume_trailing_sentence_tail(self, text: str, index: int, limit: int) -> int:
        """Consume closers and whitespace after a sentence boundary without crossing limit."""

        adjusted = index
        while adjusted < limit and text[adjusted] in self._TRAILING_SENTENCE_CLOSERS:
            adjusted += 1
        while adjusted < limit and text[adjusted].isspace():
            adjusted += 1
        return adjusted
