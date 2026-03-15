"""Unit tests for deterministic EPUB export from translated-document artifacts."""

from __future__ import annotations

from pathlib import Path
import zipfile

from bookvoice.io.epub_exporter import EpubExportRequest, EpubExporter
from bookvoice.models.datatypes import TranslatedDocument, TranslatedDocumentChapter


def test_epub_exporter_emits_valid_minimal_archive_with_ordered_chapters(tmp_path: Path) -> None:
    """Exporter should emit deterministic EPUB structure and chapter ordering metadata."""

    output_path = tmp_path / "translated.epub"
    document = TranslatedDocument(
        source_format="epub",
        source_path=Path("tests/files/canonical_synthetic_fixture.epub"),
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
                body="Prvni odstavec.\n\nDruhy odstavec.",
            ),
            TranslatedDocumentChapter(
                index=2,
                title="Kapitola 2: Dilna Luceren",
                body="Treti odstavec.",
            ),
        ),
    )

    emitted = EpubExporter().export(
        EpubExportRequest(
            document=document,
            output_path=output_path,
            book_title="Cesky Preklad Atlasu",
            author="Bookvoice Fixture Author",
        )
    )

    assert emitted == output_path
    assert emitted.exists()

    with zipfile.ZipFile(emitted, "r") as archive:
        names = archive.namelist()
        assert names[0] == "mimetype"
        assert archive.getinfo("mimetype").compress_type == zipfile.ZIP_STORED
        assert archive.read("mimetype").decode("utf-8") == "application/epub+zip"
        assert "META-INF/container.xml" in names
        assert "OEBPS/content.opf" in names
        assert "OEBPS/nav.xhtml" in names
        assert "OEBPS/toc.ncx" in names
        assert "OEBPS/chapter-001.xhtml" in names
        assert "OEBPS/chapter-002.xhtml" in names

        opf = archive.read("OEBPS/content.opf").decode("utf-8")
        nav = archive.read("OEBPS/nav.xhtml").decode("utf-8")
        chapter_one = archive.read("OEBPS/chapter-001.xhtml").decode("utf-8")
        chapter_two = archive.read("OEBPS/chapter-002.xhtml").decode("utf-8")

    assert "<dc:language>cs</dc:language>" in opf
    assert "<dc:title>Cesky Preklad Atlasu</dc:title>" in opf
    assert "<dc:creator>Bookvoice Fixture Author</dc:creator>" in opf
    assert opf.index("chapter-001.xhtml") < opf.index("chapter-002.xhtml")
    assert nav.index("chapter-001.xhtml") < nav.index("chapter-002.xhtml")
    assert "Kapitola 1: Sadovy Ledger" in chapter_one
    assert "<p>Prvni odstavec.</p>" in chapter_one
    assert "<p>Druhy odstavec.</p>" in chapter_one
    assert "Kapitola 2: Dilna Luceren" in chapter_two
