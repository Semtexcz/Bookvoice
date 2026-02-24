"""Shared helpers for resolving canonical test fixture paths."""

from __future__ import annotations

from pathlib import Path

_CANONICAL_CONTENT_PDF_FIXTURE_NAME = "canonical_synthetic_fixture.pdf"


def canonical_content_pdf_fixture_path() -> Path:
    """Return the canonical PDF fixture path used by content-based tests."""

    return Path("tests") / "files" / _CANONICAL_CONTENT_PDF_FIXTURE_NAME
