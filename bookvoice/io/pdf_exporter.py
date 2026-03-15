"""Deterministic PDF export from canonical translated-document artifacts.

Responsibilities:
- Render translated-document chapters into reader-friendly PDF pages.
- Keep chapter ordering, output layout, and metadata deterministic.
- Apply explicit unsupported-glyph fallback for non-Latin-1 characters.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Final

from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from ..models.datatypes import TranslatedDocument, TranslatedDocumentChapter

_A4_WIDTH: Final[float] = 595.276
_A4_HEIGHT: Final[float] = 841.89
_MARGIN_X: Final[float] = 54.0
_MARGIN_TOP: Final[float] = 60.0
_MARGIN_BOTTOM: Final[float] = 54.0
_TITLE_FONT_SIZE: Final[float] = 20.0
_CHAPTER_FONT_SIZE: Final[float] = 15.0
_BODY_FONT_SIZE: Final[float] = 11.0
_TITLE_LINE_HEIGHT: Final[float] = 28.0
_CHAPTER_LINE_HEIGHT: Final[float] = 22.0
_BODY_LINE_HEIGHT: Final[float] = 16.0
_PARAGRAPH_SPACING: Final[float] = 8.0
_SECTION_SPACING: Final[float] = 16.0
_UNSUPPORTED_GLYPH_PLACEHOLDER: Final[str] = "?"


@dataclass(frozen=True, slots=True)
class PdfExportRequest:
    """Inputs required to render one deterministic PDF export."""

    document: TranslatedDocument
    output_path: Path
    book_title: str | None = None
    author: str | None = None


@dataclass(frozen=True, slots=True)
class _TextLine:
    """One positioned text fragment written to a single PDF page."""

    font_key: str
    font_size: float
    x: float
    y: float
    text: str


class PdfExporter:
    """Render canonical translated-document payloads as deterministic PDF files."""

    def export(self, request: PdfExportRequest) -> Path:
        """Write a deterministic PDF file and return the emitted path."""

        request.output_path.parent.mkdir(parents=True, exist_ok=True)

        title = self._resolve_title(request)
        pages = self._layout_pages(
            title=title,
            author=request.author,
            chapters=request.document.chapters,
        )

        writer = PdfWriter()
        writer.add_metadata(
            {
                "/Title": title,
                "/Author": (request.author or "").strip(),
                "/Subject": "Translated document",
                "/Creator": "Bookvoice",
                "/Producer": "Bookvoice",
                "/CreationDate": "D:19800101000000+00'00'",
                "/ModDate": "D:19800101000000+00'00'",
            }
        )

        for lines in pages:
            page = writer.add_blank_page(width=_A4_WIDTH, height=_A4_HEIGHT)
            page[NameObject("/Resources")] = DictionaryObject(
                {
                    NameObject("/Font"): DictionaryObject(
                        {
                            NameObject("/F1"): DictionaryObject(
                                {
                                    NameObject("/Type"): NameObject("/Font"),
                                    NameObject("/Subtype"): NameObject("/Type1"),
                                    NameObject("/BaseFont"): NameObject("/Helvetica"),
                                }
                            ),
                            NameObject("/F2"): DictionaryObject(
                                {
                                    NameObject("/Type"): NameObject("/Font"),
                                    NameObject("/Subtype"): NameObject("/Type1"),
                                    NameObject("/BaseFont"): NameObject("/Helvetica-Bold"),
                                }
                            ),
                        }
                    )
                }
            )
            stream = DecodedStreamObject()
            stream.set_data(self._content_stream(lines).encode("latin-1"))
            page[NameObject("/Contents")] = writer._add_object(stream)

        with request.output_path.open("wb") as handle:
            writer.write(handle)
        return request.output_path

    @staticmethod
    def _resolve_title(request: PdfExportRequest) -> str:
        """Resolve a human-readable book title for the document heading."""

        explicit_title = (request.book_title or "").strip()
        if explicit_title:
            return explicit_title

        stem = request.document.source_path.stem.replace("_", " ").replace("-", " ").strip()
        normalized_stem = re.sub(r"\s+", " ", stem)
        if not normalized_stem:
            return "Translated Document"
        return normalized_stem.title()

    def _layout_pages(
        self,
        *,
        title: str,
        author: str | None,
        chapters: tuple[TranslatedDocumentChapter, ...],
    ) -> tuple[tuple[_TextLine, ...], ...]:
        """Create deterministic page layout instructions for headings and paragraphs."""

        y = _A4_HEIGHT - _MARGIN_TOP
        current_lines: list[_TextLine] = []
        pages: list[tuple[_TextLine, ...]] = []

        def _commit_page() -> None:
            nonlocal y, current_lines
            if current_lines:
                pages.append(tuple(current_lines))
            current_lines = []
            y = _A4_HEIGHT - _MARGIN_TOP

        def _ensure(height: float) -> None:
            nonlocal y
            if y - height < _MARGIN_BOTTOM:
                _commit_page()

        def _append(font_key: str, size: float, line_height: float, text: str) -> None:
            nonlocal y
            _ensure(line_height)
            current_lines.append(
                _TextLine(
                    font_key=font_key,
                    font_size=size,
                    x=_MARGIN_X,
                    y=y,
                    text=self._sanitize_text(text),
                )
            )
            y -= line_height

        _append("F2", _TITLE_FONT_SIZE, _TITLE_LINE_HEIGHT, title)
        y -= _SECTION_SPACING

        normalized_author = (author or "").strip()
        if normalized_author:
            _append("F1", _BODY_FONT_SIZE, _BODY_LINE_HEIGHT, f"Author: {normalized_author}")
            y -= _SECTION_SPACING

        max_width = _A4_WIDTH - (2 * _MARGIN_X)
        for chapter in chapters:
            _append(
                "F2",
                _CHAPTER_FONT_SIZE,
                _CHAPTER_LINE_HEIGHT,
                chapter.title.strip() or "Untitled Chapter",
            )
            y -= _PARAGRAPH_SPACING
            for paragraph in self._paragraphs(chapter.body):
                for wrapped in self._wrap_text(paragraph, max_width=max_width, font_size=_BODY_FONT_SIZE):
                    _append("F1", _BODY_FONT_SIZE, _BODY_LINE_HEIGHT, wrapped)
                y -= _PARAGRAPH_SPACING
            y -= _SECTION_SPACING

        _commit_page()
        return tuple(pages)

    @staticmethod
    def _paragraphs(body: str) -> tuple[str, ...]:
        """Split chapter body into normalized paragraphs suitable for line wrapping."""

        segments = [segment.strip() for segment in re.split(r"\n\s*\n", body) if segment.strip()]
        if not segments:
            return ("",)
        return tuple(re.sub(r"\s*\n\s*", " ", segment) for segment in segments)

    def _wrap_text(self, text: str, *, max_width: float, font_size: float) -> tuple[str, ...]:
        """Wrap text using deterministic fixed-width approximation for readability."""

        safe = self._sanitize_text(text)
        if not safe:
            return ("",)

        max_chars = max(12, int(max_width / (font_size * 0.56)))
        words = safe.split()
        if not words:
            return ("",)

        lines: list[str] = []
        current = words[0]
        for word in words[1:]:
            candidate = f"{current} {word}"
            if len(candidate) <= max_chars:
                current = candidate
                continue
            lines.append(current)
            current = word
        lines.append(current)
        return tuple(lines)

    def _sanitize_text(self, text: str) -> str:
        """Normalize text and replace unsupported glyphs with a stable placeholder."""

        normalized = text.replace("\r\n", "\n").replace("\r", "\n").replace("\t", "    ")

        def _normalize_char(char: str) -> str:
            if char in {"\n", "\u00a0"}:
                return " "
            codepoint = ord(char)
            if 32 <= codepoint <= 255:
                return char
            return _UNSUPPORTED_GLYPH_PLACEHOLDER

        return "".join(_normalize_char(char) for char in normalized)

    @staticmethod
    def _content_stream(lines: tuple[_TextLine, ...]) -> str:
        """Build one deterministic PDF content stream from positioned text lines."""

        stream_lines = ["BT"]
        for line in lines:
            escaped = PdfExporter._escape_pdf_text(line.text)
            stream_lines.append(f"/{line.font_key} {line.font_size:.2f} Tf")
            stream_lines.append(f"1 0 0 1 {line.x:.2f} {line.y:.2f} Tm")
            stream_lines.append(f"({escaped}) Tj")
        stream_lines.append("ET")
        return "\n".join(stream_lines)

    @staticmethod
    def _escape_pdf_text(text: str) -> str:
        """Escape PDF literal string syntax for deterministic text operators."""

        return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
