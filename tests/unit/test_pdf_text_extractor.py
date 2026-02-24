"""Unit tests for deterministic PDF text extraction fallbacks."""

from __future__ import annotations

import subprocess

from pytest import MonkeyPatch

from bookvoice.io.pdf_text_extractor import PdfTextExtractor
from tests.fixture_paths import canonical_content_pdf_fixture_path


def test_extract_falls_back_to_pypdf_when_pdftotext_is_missing(
    monkeypatch: MonkeyPatch,
) -> None:
    """Extractor should use `pypdf` for full text when `pdftotext` is unavailable."""

    def _run_missing_pdftotext(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        _ = kwargs
        command = args[0]
        if isinstance(command, list) and command and "pdftotext" in str(command[0]).lower():
            raise FileNotFoundError("pdftotext")
        raise AssertionError("extract() should only call pdftotext on this path")

    monkeypatch.setattr(subprocess, "run", _run_missing_pdftotext)

    text = PdfTextExtractor().extract(canonical_content_pdf_fixture_path())

    assert "A Practical Atlas of Synthetic Systems" in text
    assert "Chapter 1: Orchard Ledger" in text


def test_extract_pages_falls_back_to_pypdf_when_pdfinfo_is_missing(
    monkeypatch: MonkeyPatch,
) -> None:
    """Extractor should use `pypdf` page reads when `pdfinfo` is unavailable."""

    def _run_missing_pdfinfo(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        _ = kwargs
        command = args[0]
        if isinstance(command, list) and command and "pdfinfo" in str(command[0]).lower():
            raise FileNotFoundError("pdfinfo")
        raise AssertionError("extract_pages() should not call pdftotext when pdfinfo is missing")

    monkeypatch.setattr(subprocess, "run", _run_missing_pdfinfo)

    pages = PdfTextExtractor().extract_pages(canonical_content_pdf_fixture_path())

    assert len(pages) >= 2
    assert any("Chapter 1: Orchard Ledger" in page for page in pages)
