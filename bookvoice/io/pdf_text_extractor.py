"""PDF text extraction interfaces.

Responsibilities:
- Define minimal interface for extracting plain text from PDF inputs.
- Support full-document extraction and page-wise extraction workflows.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path


class PdfExtractionError(RuntimeError):
    """Raised when text extraction from PDF cannot be completed."""


class PdfTextExtractor:
    """Extractor for text-based PDFs using the `pdftotext` tool."""

    def extract(self, pdf_path: Path) -> str:
        """Extract all text from a PDF file."""

        output = self._run_pdftotext(pdf_path)
        text = output.replace("\f", "\n").strip()
        if not text:
            raise PdfExtractionError(
                f"No extractable text found in PDF: {pdf_path}. "
                "Only text-based PDFs are supported in MVP."
            )
        return text

    def extract_pages(self, pdf_path: Path) -> list[str]:
        """Extract text per page from a PDF file."""

        page_count = self._page_count(pdf_path)
        pages: list[str] = []
        for page in range(1, page_count + 1):
            page_text = self._run_pdftotext(pdf_path, first_page=page, last_page=page)
            pages.append(page_text.replace("\f", "\n").strip())
        return pages

    def _run_pdftotext(
        self, pdf_path: Path, first_page: int | None = None, last_page: int | None = None
    ) -> str:
        if not pdf_path.exists():
            raise PdfExtractionError(f"Input PDF not found: {pdf_path}")

        command = ["pdftotext", "-enc", "UTF-8"]
        if first_page is not None:
            command.extend(["-f", str(first_page)])
        if last_page is not None:
            command.extend(["-l", str(last_page)])
        command.extend([str(pdf_path), "-"])

        try:
            result = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError as exc:
            raise PdfExtractionError(
                "The `pdftotext` command is required but was not found."
            ) from exc

        if result.returncode != 0:
            details = result.stderr.strip() or "unknown error"
            raise PdfExtractionError(f"pdftotext failed for {pdf_path}: {details}")

        return result.stdout

    def _page_count(self, pdf_path: Path) -> int:
        try:
            result = subprocess.run(
                ["pdfinfo", str(pdf_path)],
                check=False,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError as exc:
            raise PdfExtractionError(
                "The `pdfinfo` command is required but was not found."
            ) from exc

        if result.returncode != 0:
            details = result.stderr.strip() or "unknown error"
            raise PdfExtractionError(f"pdfinfo failed for {pdf_path}: {details}")

        match = re.search(r"(?m)^Pages:\s+(\d+)\s*$", result.stdout)
        if not match:
            raise PdfExtractionError(
                f"Could not determine page count for PDF: {pdf_path}"
            )
        return int(match.group(1))
