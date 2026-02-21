"""Text-budget segment planner with paragraph-aware boundaries.

Responsibilities:
- Build deterministic chapter-scoped segment plans from structure units.
- Enforce active text budget with a fixed upper budget ceiling.
- Prefer paragraph boundaries and only cut paragraphs when unavoidable.
"""

from __future__ import annotations

from dataclasses import dataclass
import re

from ..models.datatypes import ChapterStructureUnit, Chunk, PlannedSegment, SegmentPlan
from .slug import slugify_audio_title


@dataclass(frozen=True, slots=True)
class _SegmentDraft:
    """Internal mutable-free draft segment used during planning."""

    chapter_index: int
    chapter_title: str
    text: str
    char_start: int
    char_end: int
    source_order_indices: tuple[int, ...]


class TextBudgetSegmentPlanner:
    """Plan deterministic text segments from chapter/subchapter structure units."""

    DEFAULT_BUDGET_CHARS = 6500
    TEN_MINUTE_BUDGET_CEILING_CHARS = 9300
    _MIN_SENTENCE_BOUNDARY_RATIO = 0.60
    _MAX_SENTENCE_EXTENSION_RATIO = 0.35
    _PARAGRAPH_BOUNDARY_RE = re.compile(r"\n\s*\n+")
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

    def plan(
        self,
        units: list[ChapterStructureUnit],
        budget_chars: int | None = None,
    ) -> SegmentPlan:
        """Build a deterministic segment plan from normalized structure units."""

        requested_budget = (
            budget_chars if budget_chars is not None else self.DEFAULT_BUDGET_CHARS
        )
        if requested_budget <= 0:
            raise ValueError("budget_chars must be a positive integer.")
        active_budget = min(requested_budget, self.TEN_MINUTE_BUDGET_CEILING_CHARS)

        grouped_units = self._group_units_by_chapter(units)
        planned_segments: list[PlannedSegment] = []
        next_order_index = 1
        for chapter_index in sorted(grouped_units):
            chapter_units = grouped_units[chapter_index]
            chapter_segments = self._plan_chapter(chapter_units, active_budget)
            for segment_index, segment in enumerate(chapter_segments):
                planned_segments.append(
                    PlannedSegment(
                        order_index=next_order_index,
                        chapter_index=segment.chapter_index,
                        segment_index=segment_index,
                        chapter_title=segment.chapter_title,
                        text=segment.text,
                        char_start=segment.char_start,
                        char_end=segment.char_end,
                        source_order_indices=segment.source_order_indices,
                    )
                )
                next_order_index += 1

        return SegmentPlan(
            budget_chars=active_budget,
            budget_ceiling_chars=self.TEN_MINUTE_BUDGET_CEILING_CHARS,
            segments=tuple(planned_segments),
        )

    def to_chunks(self, plan: SegmentPlan) -> list[Chunk]:
        """Convert planned segments into chunk records consumable by existing stages."""

        return [
            Chunk(
                chapter_index=segment.chapter_index,
                chunk_index=segment.segment_index,
                text=segment.text,
                char_start=segment.char_start,
                char_end=segment.char_end,
                part_index=segment.segment_index + 1,
                part_title=segment.chapter_title,
                part_id=(
                    f"{segment.chapter_index:03d}_"
                    f"{segment.segment_index + 1:02d}_"
                    f"{slugify_audio_title(segment.chapter_title)}"
                ),
                source_order_indices=segment.source_order_indices,
            )
            for segment in plan.segments
        ]

    def _group_units_by_chapter(
        self,
        units: list[ChapterStructureUnit],
    ) -> dict[int, list[ChapterStructureUnit]]:
        """Group structure units by chapter with deterministic unit ordering."""

        grouped: dict[int, list[ChapterStructureUnit]] = {}
        for unit in sorted(units, key=lambda item: (item.chapter_index, item.order_index)):
            grouped.setdefault(unit.chapter_index, []).append(unit)
        return grouped

    def _plan_chapter(
        self,
        chapter_units: list[ChapterStructureUnit],
        budget_chars: int,
    ) -> list[_SegmentDraft]:
        """Plan one chapter with strict chapter boundaries and merge-when-fit behavior."""

        planned: list[_SegmentDraft] = []
        current: _SegmentDraft | None = None
        for unit in chapter_units:
            for unit_part in self._split_unit(unit, budget_chars):
                if current is None:
                    current = unit_part
                    continue
                merged = self._try_merge(current, unit_part, budget_chars)
                if merged is not None:
                    current = merged
                else:
                    planned.append(current)
                    current = unit_part
        if current is not None:
            planned.append(current)
        return planned

    def _try_merge(
        self,
        left: _SegmentDraft,
        right: _SegmentDraft,
        budget_chars: int,
    ) -> _SegmentDraft | None:
        """Merge two adjacent chapter-local drafts when merged length fits budget."""

        joined_text = f"{left.text}\n\n{right.text}"
        if len(joined_text) > budget_chars:
            return None
        return _SegmentDraft(
            chapter_index=left.chapter_index,
            chapter_title=left.chapter_title,
            text=joined_text,
            char_start=left.char_start,
            char_end=right.char_end,
            source_order_indices=left.source_order_indices + right.source_order_indices,
        )

    def _split_unit(
        self,
        unit: ChapterStructureUnit,
        budget_chars: int,
    ) -> list[_SegmentDraft]:
        """Split one structure unit by paragraph boundaries under active budget."""

        normalized_text = unit.text.strip()
        if not normalized_text:
            normalized_text = unit.chapter_title.strip() or f"Chapter {unit.chapter_index}"
        if len(normalized_text) <= budget_chars:
            return [self._build_unit_part(unit, normalized_text, 0, len(normalized_text))]

        paragraph_spans = self._paragraph_spans(normalized_text)
        parts: list[_SegmentDraft] = []
        current_text = ""
        current_start = 0
        current_end = 0
        for paragraph_text, paragraph_start, paragraph_end in paragraph_spans:
            if len(paragraph_text) > budget_chars:
                if current_text:
                    parts.append(
                        self._build_unit_part(unit, current_text, current_start, current_end)
                    )
                    current_text = ""
                parts.extend(
                    self._split_long_paragraph(unit, paragraph_text, paragraph_start, budget_chars)
                )
                current_start = 0
                current_end = 0
                continue
            candidate = paragraph_text if not current_text else f"{current_text}\n\n{paragraph_text}"
            if len(candidate) <= budget_chars:
                if not current_text:
                    current_start = paragraph_start
                current_text = candidate
                current_end = paragraph_end
                continue
            parts.append(self._build_unit_part(unit, current_text, current_start, current_end))
            current_text = paragraph_text
            current_start = paragraph_start
            current_end = paragraph_end

        if current_text:
            parts.append(self._build_unit_part(unit, current_text, current_start, current_end))
        return parts

    def _split_long_paragraph(
        self,
        unit: ChapterStructureUnit,
        paragraph_text: str,
        paragraph_start: int,
        budget_chars: int,
    ) -> list[_SegmentDraft]:
        """Split an oversized paragraph using sentence boundaries with deterministic fallback."""

        parts: list[_SegmentDraft] = []
        start = 0
        while start < len(paragraph_text):
            if start + budget_chars >= len(paragraph_text):
                split_at = len(paragraph_text)
            else:
                split_at = self._resolve_sentence_split(
                    text=paragraph_text,
                    start=start,
                    budget_chars=budget_chars,
                )
            piece = paragraph_text[start:split_at].strip()
            if piece:
                local_start = paragraph_start + start
                local_end = paragraph_start + split_at
                parts.append(self._build_unit_part(unit, piece, local_start, local_end))
            start = split_at
        return parts

    def _resolve_sentence_split(
        self,
        text: str,
        start: int,
        budget_chars: int,
    ) -> int:
        """Resolve split index that prefers sentence-complete boundaries for long paragraphs."""

        text_length = len(text)
        target_end = min(start + budget_chars, text_length)
        min_boundary = start + int(budget_chars * self._MIN_SENTENCE_BOUNDARY_RATIO)

        backward_boundary = self._find_backward_sentence_boundary(
            text=text,
            start=start,
            target_end=target_end,
            min_boundary=min_boundary,
        )
        if backward_boundary is not None:
            return backward_boundary

        extension_budget = max(1, int(budget_chars * self._MAX_SENTENCE_EXTENSION_RATIO))
        extension_limit = min(text_length, target_end + extension_budget)
        forward_boundary = self._find_forward_sentence_boundary(
            text=text,
            from_index=target_end,
            extension_limit=extension_limit,
        )
        if forward_boundary is not None:
            return forward_boundary

        return self._fallback_split(text, start, target_end, extension_limit)

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

    def _fallback_split(
        self,
        text: str,
        start: int,
        target_end: int,
        extension_limit: int,
    ) -> int:
        """Return deterministic split index when sentence boundary is not available."""

        for index in range(target_end, extension_limit):
            if text[index].isspace():
                return index + 1

        for index in range(target_end - 1, start, -1):
            if text[index].isspace():
                return index + 1

        return extension_limit if extension_limit > start else target_end

    def _paragraph_spans(self, text: str) -> list[tuple[str, int, int]]:
        """Return deterministic paragraph spans from normalized text."""

        spans: list[tuple[str, int, int]] = []
        start = 0
        for match in self._PARAGRAPH_BOUNDARY_RE.finditer(text):
            end = match.start()
            paragraph = text[start:end].strip()
            if paragraph:
                spans.append((paragraph, start, end))
            start = match.end()
        tail = text[start:].strip()
        if tail:
            spans.append((tail, start, len(text)))
        if not spans:
            spans.append((text, 0, len(text)))
        return spans

    def _build_unit_part(
        self,
        unit: ChapterStructureUnit,
        text: str,
        local_start: int,
        local_end: int,
    ) -> _SegmentDraft:
        """Build one chapter-local draft segment from unit-local offsets."""

        estimated_start = max(unit.char_start, unit.char_start + local_start)
        estimated_end = max(estimated_start, min(unit.char_end, unit.char_start + local_end))
        return _SegmentDraft(
            chapter_index=unit.chapter_index,
            chapter_title=unit.chapter_title,
            text=text,
            char_start=estimated_start,
            char_end=estimated_end,
            source_order_indices=(unit.order_index,),
        )
