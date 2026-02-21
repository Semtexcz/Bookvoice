"""Tests for normalized chapter/subchapter structure extraction."""

from pathlib import Path

from pytest import MonkeyPatch

from bookvoice.io.pdf_outline_extractor import OutlineStructureExtraction
from bookvoice.models.datatypes import Chapter, ChapterStructureUnit
from bookvoice.pipeline import BookvoicePipeline


def test_pipeline_prefers_outline_structure_when_available(monkeypatch: MonkeyPatch) -> None:
    """Pipeline should use outline-derived structure units when outline source is active."""

    chapters = [Chapter(index=1, title="Chapter 1", text="Body.")]
    outline_units = [
        ChapterStructureUnit(
            order_index=1,
            chapter_index=1,
            chapter_title="Chapter 1",
            subchapter_index=1,
            subchapter_title="1.1 Intro",
            text="Intro body.",
            char_start=0,
            char_end=11,
            source="pdf_outline",
        )
    ]

    def _extract_structure(_: object, __: Path) -> OutlineStructureExtraction:
        """Return deterministic outline structure units."""

        return OutlineStructureExtraction(units=outline_units, status="pdf_outline")

    monkeypatch.setattr(
        "bookvoice.pipeline.PdfOutlineChapterExtractor.extract_structure",
        _extract_structure,
    )

    pipeline = BookvoicePipeline()
    units = pipeline._extract_normalized_structure(
        chapters=chapters,
        chapter_source="pdf_outline",
        source_pdf=Path("book.pdf"),
    )

    assert units == outline_units
    assert units[0].source == "pdf_outline"


def test_pipeline_falls_back_to_text_heading_structure(monkeypatch: MonkeyPatch) -> None:
    """Pipeline should derive structure units from text headings when outline units are missing."""

    chapters = [
        Chapter(
            index=1,
            title="Chapter 1",
            text="1.1 Intro\nAlpha paragraph.\n\n1.2 Deep Dive\nBeta paragraph.",
        )
    ]

    def _missing_structure(_: object, __: Path) -> OutlineStructureExtraction:
        """Return missing outline structure to force text-based fallback."""

        return OutlineStructureExtraction(units=[], status="outline_missing")

    monkeypatch.setattr(
        "bookvoice.pipeline.PdfOutlineChapterExtractor.extract_structure",
        _missing_structure,
    )

    pipeline = BookvoicePipeline()
    units = pipeline._extract_normalized_structure(
        chapters=chapters,
        chapter_source="pdf_outline",
        source_pdf=Path("book.pdf"),
    )

    assert [item.subchapter_index for item in units] == [1, 2]
    assert [item.subchapter_title for item in units] == ["1.1 Intro", "1.2 Deep Dive"]
    assert [item.source for item in units] == ["text_heuristic", "text_heuristic"]


def test_structure_ordering_is_stable_across_repeated_runs() -> None:
    """Structure unit ordering should be deterministic for identical chapter input."""

    chapters = [
        Chapter(index=2, title="Chapter 2", text="No subchapter headings."),
        Chapter(index=1, title="Chapter 1", text="1.1 Intro\nBody."),
    ]
    pipeline = BookvoicePipeline()

    first = pipeline._extract_normalized_structure(
        chapters=chapters,
        chapter_source="text_heuristic",
        source_pdf=Path("book.pdf"),
    )
    second = pipeline._extract_normalized_structure(
        chapters=chapters,
        chapter_source="text_heuristic",
        source_pdf=Path("book.pdf"),
    )

    assert first == second
    assert [(item.order_index, item.chapter_index) for item in first] == [(1, 1), (2, 2)]
