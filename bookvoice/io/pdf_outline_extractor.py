"""PDF outline chapter extraction helpers.

Responsibilities:
- Read first-level PDF outline/bookmark entries when available.
- Convert outline page ranges into deterministic chapter records.
- Return explicit extraction status so pipeline fallback stays observable.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..models.datatypes import Chapter
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

    def _read_first_level_entries(self, pdf_path: Path) -> list[_OutlineEntry] | str:
        """Read first-level outline entries from PDF using `pypdf` when available."""

        try:
            from pypdf import PdfReader
            from pypdf.generic import Destination
        except ImportError:
            return "outline_unavailable"

        reader = PdfReader(str(pdf_path))
        outline = list(reader.outline or [])

        entries: list[_OutlineEntry] = []
        for item in outline:
            if isinstance(item, list):
                continue

            title = self._normalize_title(getattr(item, "title", ""))
            if not title:
                continue

            page_index: int | None = None
            if isinstance(item, Destination):
                page_index = reader.get_destination_page_number(item)
            elif hasattr(item, "page"):
                try:
                    page_index = reader.get_destination_page_number(item)
                except Exception:
                    page_index = None

            if page_index is None:
                continue
            entries.append(_OutlineEntry(title=title, page_index=page_index))

        return entries

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

    def _normalize_title(self, value: object) -> str:
        """Normalize outline title into single-line whitespace-collapsed text."""

        return " ".join(str(value).split())
