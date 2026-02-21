"""PDF outline chapter extraction helpers.

Responsibilities:
- Read first-level PDF outline/bookmark entries when available.
- Convert outline page ranges into deterministic chapter records.
- Return explicit extraction status so pipeline fallback stays observable.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..models.datatypes import Chapter, ChapterStructureUnit
from .pdf_text_extractor import PdfTextExtractor


@dataclass(frozen=True, slots=True)
class OutlineChapterExtraction:
    """Result of attempting chapter extraction from a PDF outline.

    Attributes:
        chapters: Ordered chapters derived from outline entries.
        status: Deterministic extraction status code.
    """

    chapters: list[Chapter]
    status: str


@dataclass(frozen=True, slots=True)
class _OutlineEntry:
    """Internal representation of a first-level outline entry."""

    title: str
    page_index: int


@dataclass(frozen=True, slots=True)
class OutlineStructureExtraction:
    """Result of extracting normalized chapter/subchapter units from PDF outline."""

    units: list[ChapterStructureUnit]
    status: str


@dataclass(frozen=True, slots=True)
class _OutlineChapterNode:
    """Internal chapter node with optional nested subchapter entries."""

    title: str
    page_index: int
    subchapters: list[_OutlineEntry]


class PdfOutlineChapterExtractor:
    """Extract chapter boundaries from first-level PDF outline entries."""

    def extract(self, pdf_path: Path) -> OutlineChapterExtraction:
        """Extract chapters from PDF outline/bookmarks if available.

        Status values:
        - `pdf_outline`: extraction succeeded and returned chapter records.
        - `outline_unavailable`: outline backend is unavailable.
        - `outline_missing`: no usable first-level outline entries were found.
        - `outline_invalid`: outline entries existed but could not form chapter ranges.
        """

        entries_or_status = self._read_first_level_entries(pdf_path)
        if isinstance(entries_or_status, str):
            return OutlineChapterExtraction(chapters=[], status=entries_or_status)

        entries = self._normalize_entries(entries_or_status)
        if not entries:
            return OutlineChapterExtraction(chapters=[], status="outline_missing")

        pages = PdfTextExtractor().extract_pages(pdf_path)
        if not pages:
            return OutlineChapterExtraction(chapters=[], status="outline_invalid")

        chapters = self._chapters_from_entries(entries, pages)
        if not chapters:
            return OutlineChapterExtraction(chapters=[], status="outline_invalid")

        return OutlineChapterExtraction(chapters=chapters, status="pdf_outline")

    def extract_structure(self, pdf_path: Path) -> OutlineStructureExtraction:
        """Extract normalized chapter/subchapter units from PDF outline hierarchy."""

        nodes_or_status = self._read_outline_hierarchy(pdf_path)
        if isinstance(nodes_or_status, str):
            return OutlineStructureExtraction(units=[], status=nodes_or_status)

        nodes = self._normalize_hierarchy(nodes_or_status)
        if not nodes:
            return OutlineStructureExtraction(units=[], status="outline_missing")

        pages = PdfTextExtractor().extract_pages(pdf_path)
        if not pages:
            return OutlineStructureExtraction(units=[], status="outline_invalid")

        units = self._structure_units_from_nodes(nodes, pages)
        if not units:
            return OutlineStructureExtraction(units=[], status="outline_invalid")
        return OutlineStructureExtraction(units=units, status="pdf_outline")

    def _read_first_level_entries(self, pdf_path: Path) -> list[_OutlineEntry] | str:
        """Read first-level outline entries from PDF using `pypdf` when available."""

        nodes_or_status = self._read_outline_hierarchy(pdf_path)
        if isinstance(nodes_or_status, str):
            return nodes_or_status
        return [
            _OutlineEntry(title=node.title, page_index=node.page_index)
            for node in nodes_or_status
        ]

    def _read_outline_hierarchy(self, pdf_path: Path) -> list[_OutlineChapterNode] | str:
        """Read first-level outline chapters and second-level subchapters."""

        try:
            from pypdf import PdfReader
            from pypdf.generic import Destination
        except ImportError:
            return "outline_unavailable"

        reader = PdfReader(str(pdf_path))
        outline = list(reader.outline or [])

        nodes: list[_OutlineChapterNode] = []
        current_node: _OutlineChapterNode | None = None
        for item in outline:
            if isinstance(item, list):
                if current_node is None:
                    continue
                for child in self._flatten_outline_items(item):
                    entry = self._outline_entry_from_item(reader, child, Destination)
                    if entry is None:
                        continue
                    current_node.subchapters.append(entry)
                continue

            entry = self._outline_entry_from_item(reader, item, Destination)
            if entry is None:
                current_node = None
                continue
            current_node = _OutlineChapterNode(
                title=entry.title,
                page_index=entry.page_index,
                subchapters=[],
            )
            nodes.append(current_node)
        return nodes

    def _outline_entry_from_item(
        self,
        reader: object,
        item: object,
        destination_type: type[object],
    ) -> _OutlineEntry | None:
        """Convert a raw pypdf outline item into a normalized outline entry."""

        title = self._normalize_title(getattr(item, "title", ""))
        if not title:
            return None

        page_index: int | None = None
        if isinstance(item, destination_type):
            page_index = reader.get_destination_page_number(item)
        elif hasattr(item, "page"):
            try:
                page_index = reader.get_destination_page_number(item)
            except Exception:
                page_index = None

        if page_index is None:
            return None
        return _OutlineEntry(title=title, page_index=page_index)

    def _flatten_outline_items(self, items: list[object]) -> list[object]:
        """Flatten nested list structures under a chapter into a deterministic sequence."""

        flattened: list[object] = []
        for item in items:
            if isinstance(item, list):
                flattened.extend(self._flatten_outline_items(item))
            else:
                flattened.append(item)
        return flattened

    def _normalize_entries(self, entries: list[_OutlineEntry]) -> list[_OutlineEntry]:
        """Drop invalid and non-increasing page entries to keep chapter boundaries stable."""

        normalized: list[_OutlineEntry] = []
        last_page = -1
        for entry in entries:
            if entry.page_index < 0:
                continue
            if entry.page_index <= last_page:
                continue
            normalized.append(entry)
            last_page = entry.page_index
        return normalized

    def _normalize_hierarchy(
        self, nodes: list[_OutlineChapterNode]
    ) -> list[_OutlineChapterNode]:
        """Normalize chapter/subchapter hierarchy with stable increasing page boundaries."""

        normalized: list[_OutlineChapterNode] = []
        last_chapter_page = -1
        for node in nodes:
            if node.page_index < 0 or node.page_index <= last_chapter_page:
                continue

            subchapters: list[_OutlineEntry] = []
            last_subchapter_page = node.page_index - 1
            for child in node.subchapters:
                if child.page_index < node.page_index:
                    continue
                if child.page_index <= last_subchapter_page:
                    continue
                subchapters.append(child)
                last_subchapter_page = child.page_index

            normalized.append(
                _OutlineChapterNode(
                    title=node.title,
                    page_index=node.page_index,
                    subchapters=subchapters,
                )
            )
            last_chapter_page = node.page_index
        return normalized

    def _chapters_from_entries(self, entries: list[_OutlineEntry], pages: list[str]) -> list[Chapter]:
        """Build chapter list by slicing page text between outline boundaries."""

        chapters: list[Chapter] = []
        page_count = len(pages)
        for position, entry in enumerate(entries):
            if entry.page_index >= page_count:
                continue

            next_page = page_count
            if position + 1 < len(entries):
                next_page = min(page_count, entries[position + 1].page_index)
            if next_page <= entry.page_index:
                continue

            raw_text = "\n\n".join(pages[entry.page_index:next_page]).strip()
            chapter_text = raw_text if raw_text else entry.title
            chapters.append(
                Chapter(index=len(chapters) + 1, title=entry.title, text=chapter_text)
            )
        return chapters

    def _structure_units_from_nodes(
        self, nodes: list[_OutlineChapterNode], pages: list[str]
    ) -> list[ChapterStructureUnit]:
        """Build normalized planning units from chapter and subchapter outline nodes."""

        units: list[ChapterStructureUnit] = []
        page_count = len(pages)
        order_index = 1
        for chapter_position, chapter_node in enumerate(nodes):
            if chapter_node.page_index >= page_count:
                continue

            chapter_end_page = page_count
            if chapter_position + 1 < len(nodes):
                chapter_end_page = min(page_count, nodes[chapter_position + 1].page_index)
            if chapter_end_page <= chapter_node.page_index:
                continue

            valid_subchapters = [
                item
                for item in chapter_node.subchapters
                if chapter_node.page_index <= item.page_index < chapter_end_page
            ]
            if not valid_subchapters:
                chapter_text = "\n\n".join(pages[chapter_node.page_index:chapter_end_page]).strip()
                payload = chapter_text if chapter_text else chapter_node.title
                units.append(
                    ChapterStructureUnit(
                        order_index=order_index,
                        chapter_index=chapter_position + 1,
                        chapter_title=chapter_node.title,
                        subchapter_index=None,
                        subchapter_title=None,
                        text=payload,
                        char_start=0,
                        char_end=len(payload),
                        source="pdf_outline",
                    )
                )
                order_index += 1
                continue

            chapter_text = "\n\n".join(pages[chapter_node.page_index:chapter_end_page]).strip()
            chapter_cursor = 0
            for subchapter_position, subchapter in enumerate(valid_subchapters):
                subchapter_end_page = chapter_end_page
                if subchapter_position + 1 < len(valid_subchapters):
                    subchapter_end_page = valid_subchapters[subchapter_position + 1].page_index
                if subchapter_end_page <= subchapter.page_index:
                    continue

                subchapter_text = "\n\n".join(
                    pages[subchapter.page_index:subchapter_end_page]
                ).strip()
                payload = subchapter_text if subchapter_text else subchapter.title
                char_start = chapter_text.find(payload, chapter_cursor)
                if char_start < 0:
                    char_start = chapter_cursor
                char_end = char_start + len(payload)
                chapter_cursor = max(chapter_cursor, char_end)
                units.append(
                    ChapterStructureUnit(
                        order_index=order_index,
                        chapter_index=chapter_position + 1,
                        chapter_title=chapter_node.title,
                        subchapter_index=subchapter_position + 1,
                        subchapter_title=subchapter.title,
                        text=payload,
                        char_start=char_start,
                        char_end=char_end,
                        source="pdf_outline",
                    )
                )
                order_index += 1
        return units

    def _normalize_title(self, value: object) -> str:
        """Normalize outline title into single-line whitespace-collapsed text."""

        return " ".join(str(value).split())
