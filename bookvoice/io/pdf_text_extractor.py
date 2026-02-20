"""PDF text extraction interfaces.

Responsibilities:
- Define minimal interface for extracting plain text from PDF inputs.
- Support full-document extraction and page-wise extraction workflows.
"""

from __future__ import annotations

from pathlib import Path


class PdfTextExtractor:
    """Base extractor interface for text-based PDFs."""

    def extract(self, pdf_path: Path) -> str:
        """Extract all text from a PDF file."""

        _ = pdf_path
        return ""

    def extract_pages(self, pdf_path: Path) -> list[str]:
        """Extract text per page from a PDF file."""

        _ = pdf_path
        return []
