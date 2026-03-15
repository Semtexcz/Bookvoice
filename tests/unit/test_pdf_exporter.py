"""Unit tests for deterministic PDF export from translated-document artifacts."""

from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader

from bookvoice.io.pdf_exporter import PdfExportRequest, PdfExporter
from bookvoice.models.datatypes import TranslatedDocument, TranslatedDocumentChapter


def test_pdf_exporter_emits_readable_document_with_ordered_chapters(tmp_path: Path) -> None:
    """Exporter should emit chapter headings and bodies in stable chapter order."""

    output_path = tmp_path / "translated.pdf"
    document = TranslatedDocument(
        source_format="pdf",
        source_path=Path("tests/files/canonical_synthetic_fixture.pdf"),
        target_language="cs",
        chapter_scope={
            "chapter_scope_mode": "selected",
            "chapter_scope_label": "1-2",
            "chapter_scope_indices_csv": "1,2",
        },
        chapters=(
            TranslatedDocumentChapter(
                index=1,
                title="Kapitola 1: Sadovy Ledger",
                body="Prvni odstavec.\n\nDruhy odstavec s emoji 😀.",
            ),
            TranslatedDocumentChapter(
                index=2,
                title="Kapitola 2: Dilna Luceren",
                body="Treti odstavec.",
            ),
        ),
    )

    emitted = PdfExporter().export(
        PdfExportRequest(
            document=document,
            output_path=output_path,
            book_title="Cesky Preklad Atlasu",
            author="Bookvoice Fixture Author",
        )
    )

    assert emitted == output_path
    assert emitted.exists()

    page_text = "\n".join(
        (page.extract_text() or "")
        for page in PdfReader(str(emitted)).pages
    )

    assert "Cesky Preklad Atlasu" in page_text
    assert "Kapitola 1: Sadovy Ledger" in page_text
    assert "Prvni odstavec." in page_text
    assert "Druhy odstavec s emoji ?." in page_text
    assert "Kapitola 2: Dilna Luceren" in page_text
    assert page_text.index("Kapitola 1: Sadovy Ledger") < page_text.index("Kapitola 2: Dilna Luceren")
