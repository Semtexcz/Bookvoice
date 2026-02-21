"""Chapter/subchapter structure normalization helpers.

Responsibilities:
- Convert chapter records into deterministic planning units.
- Detect optional subchapter boundaries from heading-like lines.
- Preserve explicit chapter boundaries for downstream segment planning.
"""

from __future__ import annotations

import re

from ..models.datatypes import Chapter, ChapterStructureUnit


class ChapterStructureNormalizer:
    """Build normalized structure units from chapter text heuristics."""

    _SUBCHAPTER_HEADING_RE = re.compile(
        r"^(?P<title>\s*(?:\d+\.\d+(?:\.\d+)*|(?:section|subchapter)\s+\d+)"
        r"(?:[ \t]*[:.\-][ \t]*[^\n]+|[ \t]+[^\n]+)?)\s*$",
        re.IGNORECASE | re.MULTILINE,
    )

    def from_chapters(self, chapters: list[Chapter], source: str) -> list[ChapterStructureUnit]:
        """Build deterministic planning units from chapter records.

        For each chapter:
        - Emit one chapter-level unit when no subchapter headings are detected.
        - Emit one unit per detected subchapter heading otherwise.
        """

        units: list[ChapterStructureUnit] = []
        order_index = 1
        for chapter in sorted(chapters, key=lambda item: item.index):
            chapter_units = self._chapter_units(chapter, source, order_index)
            units.extend(chapter_units)
            order_index += len(chapter_units)
        return units

    def _chapter_units(
        self,
        chapter: Chapter,
        source: str,
        start_order_index: int,
    ) -> list[ChapterStructureUnit]:
        """Build planning units for one chapter using subchapter heading detection."""

        normalized_text = chapter.text.replace("\r\n", "\n").replace("\r", "\n").strip()
        if not normalized_text:
            return [
                ChapterStructureUnit(
                    order_index=start_order_index,
                    chapter_index=chapter.index,
                    chapter_title=chapter.title,
                    subchapter_index=None,
                    subchapter_title=None,
                    text=chapter.title,
                    char_start=0,
                    char_end=len(chapter.title),
                    source=source,
                )
            ]

        headings = list(self._SUBCHAPTER_HEADING_RE.finditer(normalized_text))
        if not headings:
            return [
                ChapterStructureUnit(
                    order_index=start_order_index,
                    chapter_index=chapter.index,
                    chapter_title=chapter.title,
                    subchapter_index=None,
                    subchapter_title=None,
                    text=normalized_text,
                    char_start=0,
                    char_end=len(normalized_text),
                    source=source,
                )
            ]

        units: list[ChapterStructureUnit] = []
        for position, heading in enumerate(headings):
            start = heading.end()
            end = headings[position + 1].start() if position + 1 < len(headings) else len(
                normalized_text
            )
            content = normalized_text[start:end].strip()
            title = " ".join(heading.group("title").split())
            text = content if content else title
            units.append(
                ChapterStructureUnit(
                    order_index=start_order_index + position,
                    chapter_index=chapter.index,
                    chapter_title=chapter.title,
                    subchapter_index=position + 1,
                    subchapter_title=title,
                    text=text,
                    char_start=max(0, start),
                    char_end=max(start, end),
                    source=source,
                )
            )
        return units
