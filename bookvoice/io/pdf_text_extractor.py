"""PDF text extraction interfaces.

Responsibilities:
- Define minimal interface for extracting plain text from PDF inputs.
- Support full-document extraction and page-wise extraction workflows.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from ..runtime_tools import resolve_executable


class PdfExtractionError(RuntimeError):
    """Raised when text extraction from PDF cannot be completed."""


class PdfTextExtractor:
    """Extractor for text-based PDFs using the `pdftotext` tool."""

    def extract(self, pdf_path: Path) -> str:
        """Extract all text from a PDF file."""

        try:
            output = self._run_pdftotext(pdf_path)
            text = output.replace("\f", "\n").strip()
        except PdfExtractionError as exc:
            if not self._is_missing_binary_error(exc):
                raise
            text = self._extract_with_pypdf(pdf_path).strip()
        if not text:
            raise PdfExtractionError(
                f"No extractable text found in PDF: {pdf_path}. "
                "Only text-based PDFs are supported in MVP."
            )
        return text

    def extract_pages(self, pdf_path: Path) -> list[str]:
        """Extract text per page from a PDF file."""

        try:
            page_count = self._page_count(pdf_path)
        except PdfExtractionError as exc:
            if not self._is_missing_binary_error(exc):
                raise
            return self._extract_pages_with_pypdf(pdf_path)

        pages: list[str] = []
        for page in range(1, page_count + 1):
            try:
                page_text = self._run_pdftotext(pdf_path, first_page=page, last_page=page)
                pages.append(page_text.replace("\f", "\n").strip())
            except PdfExtractionError as exc:
                if not self._is_missing_binary_error(exc):
                    raise
                return self._extract_pages_with_pypdf(pdf_path)
        return pages

    def _run_pdftotext(
        self, pdf_path: Path, first_page: int | None = None, last_page: int | None = None
    ) -> str:
        if not pdf_path.exists():
            raise PdfExtractionError(f"Input PDF not found: {pdf_path}")

        command = [resolve_executable("pdftotext"), "-enc", "UTF-8"]
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
                [resolve_executable("pdfinfo"), str(pdf_path)],
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

    def _extract_with_pypdf(self, pdf_path: Path) -> str:
        """Extract full-document text using `pypdf` as a deterministic fallback."""

        return "\n".join(self._extract_pages_with_pypdf(pdf_path)).strip()

    def _extract_pages_with_pypdf(self, pdf_path: Path) -> list[str]:
        """Extract per-page text with `pypdf` when system PDF tools are unavailable."""

        if not pdf_path.exists():
            raise PdfExtractionError(f"Input PDF not found: {pdf_path}")
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise PdfExtractionError(
                "The `pypdf` package is required for fallback PDF extraction but was not found."
            ) from exc

        reader = PdfReader(str(pdf_path))
        pages: list[str] = []
        for page in reader.pages:
            extracted_text = page.extract_text()
            pages.append((extracted_text or "").replace("\f", "\n").strip())
        return pages

    def _is_missing_binary_error(self, error: PdfExtractionError) -> bool:
        """Return whether extraction failed due to unavailable external PDF binaries."""

        detail = str(error)
        return detail.endswith("command is required but was not found.")
