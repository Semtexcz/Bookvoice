"""Deterministic EPUB export from canonical translated-document artifacts.

Responsibilities:
- Build standards-compliant minimal EPUB archives for reader delivery.
- Preserve translated language metadata and chapter ordering.
- Keep generated archive layout, metadata, and filenames deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from html import escape
from pathlib import Path
import re
from typing import Final
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile, ZipInfo

from ..models.datatypes import TranslatedDocument, TranslatedDocumentChapter

_DETERMINISTIC_ZIP_DATETIME: Final[tuple[int, int, int, int, int, int]] = (
    1980,
    1,
    1,
    0,
    0,
    0,
)


@dataclass(frozen=True, slots=True)
class EpubExportRequest:
    """Inputs required to render one deterministic EPUB export."""

    document: TranslatedDocument
    output_path: Path
    book_title: str | None = None
    author: str | None = None


class EpubExporter:
    """Render canonical translated-document payloads as EPUB archives."""

    def export(self, request: EpubExportRequest) -> Path:
        """Write a deterministic EPUB file and return the emitted path."""

        request.output_path.parent.mkdir(parents=True, exist_ok=True)

        title = self._resolve_title(request)
        language = request.document.target_language.strip() or "und"
        chapter_files = self._chapter_filenames(request.document.chapters)

        with ZipFile(request.output_path, mode="w") as archive:
            self._write_entry(
                archive=archive,
                path="mimetype",
                content="application/epub+zip",
                compress_type=ZIP_STORED,
            )
            self._write_entry(
                archive=archive,
                path="META-INF/container.xml",
                content=self._container_xml(),
                compress_type=ZIP_DEFLATED,
            )
            self._write_entry(
                archive=archive,
                path="OEBPS/content.opf",
                content=self._content_opf(
                    document=request.document,
                    title=title,
                    author=request.author,
                    language=language,
                    chapter_files=chapter_files,
                ),
                compress_type=ZIP_DEFLATED,
            )
            self._write_entry(
                archive=archive,
                path="OEBPS/nav.xhtml",
                content=self._nav_xhtml(
                    title=title,
                    language=language,
                    chapters=request.document.chapters,
                    chapter_files=chapter_files,
                ),
                compress_type=ZIP_DEFLATED,
            )
            self._write_entry(
                archive=archive,
                path="OEBPS/toc.ncx",
                content=self._toc_ncx(
                    document=request.document,
                    title=title,
                    language=language,
                    chapter_files=chapter_files,
                ),
                compress_type=ZIP_DEFLATED,
            )
            for chapter, chapter_file in zip(
                request.document.chapters,
                chapter_files,
                strict=True,
            ):
                self._write_entry(
                    archive=archive,
                    path=f"OEBPS/{chapter_file}",
                    content=self._chapter_xhtml(
                        chapter=chapter,
                        book_title=title,
                        language=language,
                    ),
                    compress_type=ZIP_DEFLATED,
                )
        return request.output_path

    @staticmethod
    def _resolve_title(request: EpubExportRequest) -> str:
        """Resolve a human-readable book title for package metadata."""

        explicit_title = (request.book_title or "").strip()
        if explicit_title:
            return explicit_title

        stem = request.document.source_path.stem.replace("_", " ").replace("-", " ").strip()
        normalized_stem = re.sub(r"\s+", " ", stem)
        if not normalized_stem:
            return "Translated Document"
        return normalized_stem.title()

    @staticmethod
    def _chapter_filenames(chapters: tuple[TranslatedDocumentChapter, ...]) -> tuple[str, ...]:
        """Return deterministic chapter XHTML filenames preserving chapter order."""

        return tuple(f"chapter-{chapter.index:03d}.xhtml" for chapter in chapters)

    @staticmethod
    def _container_xml() -> str:
        """Return the required EPUB container metadata."""

        return (
            "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
            "<container version=\"1.0\" "
            "xmlns=\"urn:oasis:names:tc:opendocument:xmlns:container\">\n"
            "  <rootfiles>\n"
            "    <rootfile full-path=\"OEBPS/content.opf\" "
            "media-type=\"application/oebps-package+xml\"/>\n"
            "  </rootfiles>\n"
            "</container>\n"
        )

    def _content_opf(
        self,
        *,
        document: TranslatedDocument,
        title: str,
        author: str | None,
        language: str,
        chapter_files: tuple[str, ...],
    ) -> str:
        """Return OPF package metadata with nav/spine manifest entries."""

        escaped_title = escape(title)
        escaped_language = escape(language)
        escaped_author = escape(author.strip()) if isinstance(author, str) and author.strip() else ""
        identifier = escape(self._identifier(document))
        chapter_manifest_items = "\n".join(
            f"    <item id=\"chapter-{chapter.index:03d}\" href=\"{filename}\" "
            "media-type=\"application/xhtml+xml\"/>"
            for chapter, filename in zip(document.chapters, chapter_files, strict=True)
        )
        chapter_spine_items = "\n".join(
            f"    <itemref idref=\"chapter-{chapter.index:03d}\"/>"
            for chapter in document.chapters
        )
        creator_line = (
            f"    <dc:creator>{escaped_author}</dc:creator>\n" if escaped_author else ""
        )

        return (
            "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
            "<package xmlns=\"http://www.idpf.org/2007/opf\" "
            "xmlns:dc=\"http://purl.org/dc/elements/1.1/\" "
            "version=\"3.0\" unique-identifier=\"bookvoice-id\">\n"
            "  <metadata>\n"
            f"    <dc:identifier id=\"bookvoice-id\">{identifier}</dc:identifier>\n"
            f"    <dc:title>{escaped_title}</dc:title>\n"
            f"{creator_line}"
            f"    <dc:language>{escaped_language}</dc:language>\n"
            "    <meta property=\"dcterms:modified\">1980-01-01T00:00:00Z</meta>\n"
            "  </metadata>\n"
            "  <manifest>\n"
            "    <item id=\"nav\" href=\"nav.xhtml\" media-type=\"application/xhtml+xml\" "
            "properties=\"nav\"/>\n"
            "    <item id=\"ncx\" href=\"toc.ncx\" media-type=\"application/x-dtbncx+xml\"/>\n"
            f"{chapter_manifest_items}\n"
            "  </manifest>\n"
            "  <spine toc=\"ncx\">\n"
            f"{chapter_spine_items}\n"
            "  </spine>\n"
            "</package>\n"
        )

    def _nav_xhtml(
        self,
        *,
        title: str,
        language: str,
        chapters: tuple[TranslatedDocumentChapter, ...],
        chapter_files: tuple[str, ...],
    ) -> str:
        """Return EPUB3 navigation document with ordered chapter links."""

        nav_items = "\n".join(
            "      "
            + f"<li><a href=\"{filename}\">{escape(chapter.title)}</a></li>"
            for chapter, filename in zip(chapters, chapter_files, strict=True)
        )
        return (
            "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
            "<!DOCTYPE html>\n"
            f"<html xmlns=\"http://www.w3.org/1999/xhtml\" lang=\"{escape(language)}\">\n"
            "  <head>\n"
            "    <meta charset=\"UTF-8\"/>\n"
            f"    <title>{escape(title)}</title>\n"
            "  </head>\n"
            "  <body>\n"
            "    <nav epub:type=\"toc\" xmlns:epub=\"http://www.idpf.org/2007/ops\" "
            "id=\"toc\">\n"
            "      <h1>Contents</h1>\n"
            "      <ol>\n"
            f"{nav_items}\n"
            "      </ol>\n"
            "    </nav>\n"
            "  </body>\n"
            "</html>\n"
        )

    def _toc_ncx(
        self,
        *,
        document: TranslatedDocument,
        title: str,
        language: str,
        chapter_files: tuple[str, ...],
    ) -> str:
        """Return EPUB2-compatible NCX navigation for wider reader compatibility."""

        nav_points = "\n".join(
            "    "
            + (
                f"<navPoint id=\"chapter-{chapter.index:03d}\" playOrder=\"{order}\">"
                f"<navLabel><text>{escape(chapter.title)}</text></navLabel>"
                f"<content src=\"{filename}\"/>"
                "</navPoint>"
            )
            for order, (chapter, filename) in enumerate(
                zip(document.chapters, chapter_files, strict=True),
                start=1,
            )
        )
        return (
            "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
            "<ncx xmlns=\"http://www.daisy.org/z3986/2005/ncx/\" version=\"2005-1\" "
            f"xml:lang=\"{escape(language)}\">\n"
            "  <head>\n"
            f"    <meta name=\"dtb:uid\" content=\"{escape(self._identifier(document))}\"/>\n"
            "  </head>\n"
            f"  <docTitle><text>{escape(title)}</text></docTitle>\n"
            "  <navMap>\n"
            f"{nav_points}\n"
            "  </navMap>\n"
            "</ncx>\n"
        )

    @staticmethod
    def _chapter_xhtml(
        *,
        chapter: TranslatedDocumentChapter,
        book_title: str,
        language: str,
    ) -> str:
        """Return one chapter XHTML content document with readable headings."""

        paragraphs = [segment.strip() for segment in chapter.body.split("\n\n") if segment.strip()]
        if not paragraphs:
            paragraphs = [""]
        paragraph_markup = "\n".join(f"    <p>{escape(paragraph)}</p>" for paragraph in paragraphs)
        return (
            "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
            "<!DOCTYPE html>\n"
            f"<html xmlns=\"http://www.w3.org/1999/xhtml\" lang=\"{escape(language)}\">\n"
            "  <head>\n"
            "    <meta charset=\"UTF-8\"/>\n"
            f"    <title>{escape(chapter.title)} - {escape(book_title)}</title>\n"
            "  </head>\n"
            "  <body>\n"
            f"    <h1>{escape(chapter.title)}</h1>\n"
            f"{paragraph_markup}\n"
            "  </body>\n"
            "</html>\n"
        )

    @staticmethod
    def _identifier(document: TranslatedDocument) -> str:
        """Build deterministic package identifier from source + language + chapter scope."""

        scope_entries = ",".join(
            f"{key}={value}" for key, value in sorted(document.chapter_scope.items())
        )
        fingerprint = (
            f"{document.source_format}|{document.source_path}|{document.target_language}|"
            f"{scope_entries}|"
            + "|".join(f"{chapter.index}:{chapter.title}" for chapter in document.chapters)
        )
        digest = sha256(fingerprint.encode("utf-8")).hexdigest()[:24]
        return f"urn:bookvoice:translated:{digest}"

    @staticmethod
    def _write_entry(
        *,
        archive: ZipFile,
        path: str,
        content: str,
        compress_type: int,
    ) -> None:
        """Write one ZIP entry with deterministic timestamp and compression metadata."""

        zip_info = ZipInfo(filename=path, date_time=_DETERMINISTIC_ZIP_DATETIME)
        zip_info.compress_type = compress_type
        zip_info.create_system = 0
        zip_info.external_attr = 0o644 << 16
        archive.writestr(zip_info, content.encode("utf-8"))
