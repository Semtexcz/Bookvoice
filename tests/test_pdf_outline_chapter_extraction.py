"""Tests for PDF-outline-first chapter extraction with deterministic fallback."""

from pathlib import Path

import pytest
from pytest import MonkeyPatch

from bookvoice.io.pdf_outline_extractor import OutlineChapterExtraction
from bookvoice.models.datatypes import Chapter
from bookvoice.pipeline import BookvoicePipeline


def _create_pdf_with_outline(pdf_path: Path) -> None:
    """Create a minimal multi-page PDF file with first-level outline entries."""

    pypdf = pytest.importorskip("pypdf")
    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=595, height=842)
    writer.add_blank_page(width=595, height=842)
    writer.add_blank_page(width=595, height=842)

    writer.add_outline_item("Chapter 1", page_number=0)
    writer.add_outline_item("Chapter 2", page_number=2)

    with pdf_path.open("wb") as handle:
        writer.write(handle)


def test_pipeline_prefers_outline_chapters_when_available(monkeypatch: MonkeyPatch) -> None:
    """Pipeline should use outline-derived chapters before text heuristics."""

    outline_chapters = [
        Chapter(index=1, title="Part I", text="Outline chapter text."),
    ]

    def _extract_outline(_: object, __: Path) -> OutlineChapterExtraction:
        """Return synthetic outline chapter extraction for deterministic testing."""

        return OutlineChapterExtraction(chapters=outline_chapters, status="pdf_outline")

    def _unexpected_split(_: object, __: str) -> list[Chapter]:
        """Fail fast if text splitter is called for outline-success path."""

        raise AssertionError("text splitter should not run when outline chapters are available")

    monkeypatch.setattr("bookvoice.pipeline.PdfOutlineChapterExtractor.extract", _extract_outline)
    monkeypatch.setattr("bookvoice.pipeline.ChapterSplitter.split", _unexpected_split)

    pipeline = BookvoicePipeline()
    chapters, source, fallback_reason = pipeline._split_chapters("clean text", Path("book.pdf"))

    assert chapters == outline_chapters
    assert source == "pdf_outline"
    assert fallback_reason == ""


def test_pipeline_falls_back_to_text_splitter_with_explicit_reason(
    monkeypatch: MonkeyPatch,
) -> None:
    """Pipeline should deterministically fall back to text splitter when outline is unavailable."""

    fallback_chapters = [
        Chapter(index=1, title="Chapter 1", text="Fallback chapter text."),
    ]

    def _extract_outline(_: object, __: Path) -> OutlineChapterExtraction:
        """Return an empty outline extraction with deterministic missing status."""

        return OutlineChapterExtraction(chapters=[], status="outline_missing")

    def _split_text(_: object, __: str) -> list[Chapter]:
        """Return deterministic text-split chapters for fallback path assertions."""

        return fallback_chapters

    monkeypatch.setattr("bookvoice.pipeline.PdfOutlineChapterExtractor.extract", _extract_outline)
    monkeypatch.setattr("bookvoice.pipeline.ChapterSplitter.split", _split_text)

    pipeline = BookvoicePipeline()
    chapters, source, fallback_reason = pipeline._split_chapters("clean text", Path("book.pdf"))

    assert chapters == fallback_chapters
    assert source == "text_heuristic"
    assert fallback_reason == "outline_missing"


def test_pipeline_splits_from_pdf_outline_without_text_headings(tmp_path: Path) -> None:
    """Pipeline should split chapters from PDF outline even when clean text has no headings."""

    source_pdf = tmp_path / "outlined.pdf"
    _create_pdf_with_outline(source_pdf)

    pipeline = BookvoicePipeline()
    chapters, source, fallback_reason = pipeline._split_chapters(
        "single body block without chapter headings", source_pdf
    )

    assert source == "pdf_outline"
    assert fallback_reason == ""
    assert [chapter.index for chapter in chapters] == [1, 2]
    assert [chapter.title for chapter in chapters] == ["Chapter 1", "Chapter 2"]
