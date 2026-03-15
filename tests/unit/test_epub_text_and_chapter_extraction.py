"""Unit tests for deterministic EPUB text and chapter extraction behavior."""

from __future__ import annotations

from pathlib import Path
import zipfile

from bookvoice.io.epub_text_extractor import EpubTextExtractor
from bookvoice.pipeline import BookvoicePipeline


def _create_epub_without_navigation(epub_path: Path) -> None:
    """Create a minimal EPUB fixture that has spine docs but no nav metadata."""

    content_opf = """<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bookid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="bookid">urn:uuid:test-no-nav</dc:identifier>
    <dc:title>No Navigation Fixture</dc:title>
    <dc:creator>Bookvoice Test Author</dc:creator>
    <dc:language>en</dc:language>
  </metadata>
  <manifest>
    <item id="ch1" href="chapter-1.xhtml" media-type="application/xhtml+xml"/>
    <item id="ch2" href="chapter-2.xhtml" media-type="application/xhtml+xml"/>
  </manifest>
  <spine>
    <itemref idref="ch1"/>
    <itemref idref="ch2"/>
  </spine>
</package>
"""
    chapter_one = """<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" lang="en">
  <body>
    <h1>Chapter 1</h1>
    <p>Alpha chapter text.</p>
  </body>
</html>
"""
    chapter_two = """<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" lang="en">
  <body>
    <h1>Chapter 2</h1>
    <p>Beta chapter text.</p>
  </body>
</html>
"""
    container_xml = """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
"""

    with zipfile.ZipFile(epub_path, "w") as archive:
        archive.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        archive.writestr("META-INF/container.xml", container_xml)
        archive.writestr("OEBPS/content.opf", content_opf)
        archive.writestr("OEBPS/chapter-1.xhtml", chapter_one)
        archive.writestr("OEBPS/chapter-2.xhtml", chapter_two)


def test_epub_extractor_reads_ordered_spine_text_and_package_metadata(
    canonical_content_epub_fixture_path: Path,
) -> None:
    """Extractor should read package metadata and deterministic spine text order."""

    extractor = EpubTextExtractor()
    text = extractor.extract(canonical_content_epub_fixture_path)
    title, author = extractor.extract_package_metadata(canonical_content_epub_fixture_path)

    assert title == "A Practical Atlas of Synthetic Systems"
    assert author == "Bookvoice Fixture Author"
    assert "Chapter 1: Orchard Ledger" in text
    assert "Chapter 2: Lantern Workshop" in text
    assert text.index("Chapter 1: Orchard Ledger") < text.index("Chapter 2: Lantern Workshop")


def test_epub_extractor_uses_nav_for_chapter_ordering(
    canonical_content_epub_fixture_path: Path,
) -> None:
    """Chapter extraction should prefer EPUB nav metadata when available."""

    result = EpubTextExtractor().extract_chapters(canonical_content_epub_fixture_path)

    assert result.status == "epub_nav"
    assert [chapter.index for chapter in result.chapters] == [1, 2]
    assert [chapter.title for chapter in result.chapters] == [
        "Chapter 1: Orchard Ledger",
        "Chapter 2: Lantern Workshop",
    ]
    assert "orchard ledger opens" in result.chapters[0].text.lower()


def test_epub_extractor_reports_missing_navigation_metadata(tmp_path: Path) -> None:
    """Chapter extraction should emit explicit missing-nav status without nav metadata."""

    source_epub = tmp_path / "no-nav.epub"
    _create_epub_without_navigation(source_epub)

    result = EpubTextExtractor().extract_chapters(source_epub)

    assert result.chapters == []
    assert result.status == "nav_missing"


def test_pipeline_falls_back_to_text_splitter_when_epub_nav_is_missing(tmp_path: Path) -> None:
    """Pipeline should use text heuristics for EPUB when nav metadata is unavailable."""

    source_epub = tmp_path / "no-nav.epub"
    _create_epub_without_navigation(source_epub)
    clean_text = EpubTextExtractor().extract(source_epub)

    chapters, source, fallback_reason = BookvoicePipeline()._split_chapters(clean_text, source_epub)

    assert source == "text_heuristic"
    assert fallback_reason == "nav_missing"
    assert [chapter.title for chapter in chapters] == ["Chapter 1", "Chapter 2"]
