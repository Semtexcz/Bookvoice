"""EPUB text and chapter extraction helpers.

Responsibilities:
- Read EPUB container/package metadata and spine ordering from archive content.
- Extract deterministic plain text from XHTML spine documents.
- Build chapter records from EPUB navigation metadata with explicit fallback status.
"""

from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
import posixpath
import re
import xml.etree.ElementTree as ET
import zipfile

from ..models.datatypes import Chapter


_NAMESPACES: dict[str, str] = {
    "container": "urn:oasis:names:tc:opendocument:xmlns:container",
    "opf": "http://www.idpf.org/2007/opf",
    "dc": "http://purl.org/dc/elements/1.1/",
}


@dataclass(frozen=True, slots=True)
class EpubPackageItem:
    """One manifest item declared in an OPF package."""

    item_id: str
    href: str
    media_type: str
    properties: frozenset[str]


@dataclass(frozen=True, slots=True)
class EpubPackage:
    """Normalized EPUB package metadata and spine ordering."""

    opf_path: PurePosixPath
    title: str | None
    author: str | None
    spine_item_ids: tuple[str, ...]
    manifest: dict[str, EpubPackageItem]
    nav_item_id: str | None
    ncx_item_id: str | None


@dataclass(frozen=True, slots=True)
class EpubChapterExtraction:
    """Result of attempting chapter extraction from EPUB navigation metadata.

    Status values:
    - `epub_nav`: extraction succeeded and returned chapter records.
    - `nav_missing`: EPUB navigation metadata is unavailable.
    - `nav_invalid`: navigation metadata exists but could not produce chapter ranges.
    - `nav_unusable`: navigation entries did not map to the spine order.
    """

    chapters: list[Chapter]
    status: str


@dataclass(frozen=True, slots=True)
class EpubSpineDocument:
    """Resolved spine XHTML document with deterministic plain text payload."""

    archive_path: PurePosixPath
    text: str


class EpubExtractionError(RuntimeError):
    """Raised when deterministic EPUB extraction cannot be completed."""


class _XhtmlTextExtractor(HTMLParser):
    """Convert XHTML content into deterministic plain text."""

    _BLOCK_TAGS = {
        "address",
        "article",
        "aside",
        "blockquote",
        "br",
        "dd",
        "div",
        "dl",
        "dt",
        "figcaption",
        "figure",
        "footer",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "header",
        "hr",
        "li",
        "main",
        "nav",
        "ol",
        "p",
        "pre",
        "section",
        "table",
        "tbody",
        "td",
        "th",
        "thead",
        "tr",
        "ul",
    }
    _SKIP_TAGS = {"script", "style"}

    def __init__(self) -> None:
        """Initialize parser state for deterministic XHTML text extraction."""

        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Track skip context and block separators for XHTML tags."""

        _ = attrs
        normalized_tag = tag.lower()
        if normalized_tag in self._SKIP_TAGS:
            self._skip_depth += 1
        if self._skip_depth == 0 and normalized_tag in self._BLOCK_TAGS:
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        """Track skip context and block separators for closing tags."""

        normalized_tag = tag.lower()
        if normalized_tag in self._SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1
        if self._skip_depth == 0 and normalized_tag in self._BLOCK_TAGS:
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        """Capture visible text while preserving deterministic spacing."""

        if self._skip_depth > 0:
            return
        if data:
            self._parts.append(data)

    def text(self) -> str:
        """Return normalized plain-text representation of parsed XHTML input."""

        joined = "".join(self._parts)
        normalized = joined.replace("\r\n", "\n").replace("\r", "\n")
        normalized = re.sub(r"[ \t\f\v]+", " ", normalized)
        normalized = re.sub(r" *\n *", "\n", normalized)
        normalized = re.sub(r"\n{3,}", "\n\n", normalized)
        return normalized.strip()


class EpubTextExtractor:
    """Extractor for deterministic text/chapter extraction from EPUB archives."""

    def extract(self, epub_path: Path) -> str:
        """Extract full document text by reading OPF spine documents in order."""

        package, spine_documents = self._extract_spine_documents(epub_path)
        _ = package
        text = "\n\n".join(
            document.text for document in spine_documents if document.text.strip()
        ).strip()
        if not text:
            raise EpubExtractionError(
                f"No extractable text found in EPUB: {epub_path}. "
                "Only text-based EPUB content documents are supported."
            )
        return text

    def extract_chapters(self, epub_path: Path) -> EpubChapterExtraction:
        """Extract chapters from EPUB navigation metadata with deterministic fallback status."""

        package, spine_documents = self._extract_spine_documents(epub_path)
        nav_entries = self._read_navigation_entries(epub_path, package)
        if nav_entries is None:
            return EpubChapterExtraction(chapters=[], status="nav_missing")
        if not nav_entries:
            return EpubChapterExtraction(chapters=[], status="nav_invalid")

        chapters = self._chapters_from_navigation(package, spine_documents, nav_entries)
        if not chapters:
            return EpubChapterExtraction(chapters=[], status="nav_unusable")
        return EpubChapterExtraction(chapters=chapters, status="epub_nav")

    def extract_package_metadata(self, epub_path: Path) -> tuple[str | None, str | None]:
        """Return EPUB package title/author metadata when available."""

        package = self._read_package(epub_path)
        return package.title, package.author

    def _extract_spine_documents(
        self,
        epub_path: Path,
    ) -> tuple[EpubPackage, list[EpubSpineDocument]]:
        """Read package + ordered spine text documents from an EPUB archive."""

        package = self._read_package(epub_path)
        documents: list[EpubSpineDocument] = []
        with self._open_epub(epub_path) as archive:
            for item_id in package.spine_item_ids:
                item = package.manifest.get(item_id)
                if item is None:
                    continue
                normalized_media_type = item.media_type.strip().lower()
                if normalized_media_type not in {
                    "application/xhtml+xml",
                    "text/html",
                    "application/xml",
                }:
                    continue

                archive_path = self._resolve_archive_path(package.opf_path, item.href)
                if archive_path is None:
                    continue
                text = self._extract_xhtml_text(
                    self._read_archive_text(archive, archive_path, epub_path=epub_path)
                )
                documents.append(EpubSpineDocument(archive_path=archive_path, text=text))

        return package, documents

    def _read_package(self, epub_path: Path) -> EpubPackage:
        """Read OPF package metadata, manifest, and spine ordering from an EPUB archive."""

        with self._open_epub(epub_path) as archive:
            opf_path = self._locate_opf_path(archive, epub_path)
            opf_root = self._parse_xml(
                self._read_archive_text(archive, opf_path, epub_path=epub_path),
                context=f"OPF package `{opf_path.as_posix()}`",
            )

            metadata = opf_root.find("opf:metadata", _NAMESPACES)
            title = self._normalize_optional_text(
                metadata.findtext("dc:title", default="", namespaces=_NAMESPACES)
                if metadata is not None
                else ""
            )
            author = self._normalize_optional_text(
                metadata.findtext("dc:creator", default="", namespaces=_NAMESPACES)
                if metadata is not None
                else ""
            )

            manifest_node = opf_root.find("opf:manifest", _NAMESPACES)
            if manifest_node is None:
                raise EpubExtractionError(
                    f"EPUB OPF manifest is missing in `{epub_path}`."
                )

            manifest: dict[str, EpubPackageItem] = {}
            nav_item_id: str | None = None
            ncx_item_id: str | None = None
            for item in manifest_node.findall("opf:item", _NAMESPACES):
                item_id = self._normalize_optional_text(item.attrib.get("id", ""))
                href = self._normalize_optional_text(item.attrib.get("href", ""))
                media_type = self._normalize_optional_text(item.attrib.get("media-type", ""))
                if item_id is None or href is None or media_type is None:
                    continue
                properties = frozenset(
                    segment
                    for segment in (item.attrib.get("properties", "") or "").split()
                    if segment
                )
                manifest[item_id] = EpubPackageItem(
                    item_id=item_id,
                    href=href,
                    media_type=media_type,
                    properties=properties,
                )
                if "nav" in properties:
                    nav_item_id = item_id
                if media_type.lower() == "application/x-dtbncx+xml":
                    ncx_item_id = item_id

            spine_node = opf_root.find("opf:spine", _NAMESPACES)
            if spine_node is None:
                raise EpubExtractionError(f"EPUB OPF spine is missing in `{epub_path}`.")
            if ncx_item_id is None:
                ncx_candidate = self._normalize_optional_text(spine_node.attrib.get("toc", ""))
                ncx_item_id = ncx_candidate

            spine_item_ids: list[str] = []
            for item_ref in spine_node.findall("opf:itemref", _NAMESPACES):
                item_id = self._normalize_optional_text(item_ref.attrib.get("idref", ""))
                if item_id is None:
                    continue
                spine_item_ids.append(item_id)

            if not spine_item_ids:
                raise EpubExtractionError(f"EPUB OPF spine has no `itemref` entries in `{epub_path}`.")

            return EpubPackage(
                opf_path=opf_path,
                title=title,
                author=author,
                spine_item_ids=tuple(spine_item_ids),
                manifest=manifest,
                nav_item_id=nav_item_id,
                ncx_item_id=ncx_item_id,
            )

    def _locate_opf_path(self, archive: zipfile.ZipFile, epub_path: Path) -> PurePosixPath:
        """Locate OPF package path via EPUB `container.xml` metadata."""

        container_path = PurePosixPath("META-INF/container.xml")
        root = self._parse_xml(
            self._read_archive_text(archive, container_path, epub_path=epub_path),
            context=f"container `{container_path.as_posix()}`",
        )
        rootfile = root.find(
            "container:rootfiles/container:rootfile",
            _NAMESPACES,
        )
        if rootfile is None:
            raise EpubExtractionError(
                f"EPUB container metadata is missing rootfile entry in `{epub_path}`."
            )
        full_path = self._normalize_optional_text(rootfile.attrib.get("full-path", ""))
        if full_path is None:
            raise EpubExtractionError(
                f"EPUB container rootfile path is empty in `{epub_path}`."
            )
        return PurePosixPath(full_path)

    def _read_navigation_entries(
        self,
        epub_path: Path,
        package: EpubPackage,
    ) -> list[tuple[str, str]] | None:
        """Return ordered navigation entries as `(href, title)` pairs."""

        with self._open_epub(epub_path) as archive:
            nav_item = package.manifest.get(package.nav_item_id) if package.nav_item_id else None
            if nav_item is not None:
                nav_path = self._resolve_archive_path(package.opf_path, nav_item.href)
                if nav_path is not None:
                    try:
                        nav_document = self._read_archive_text(archive, nav_path, epub_path=epub_path)
                        entries = self._read_nav_xhtml_entries(nav_document)
                        if entries:
                            return entries
                        return []
                    except EpubExtractionError:
                        return []

            ncx_item = package.manifest.get(package.ncx_item_id) if package.ncx_item_id else None
            if ncx_item is not None:
                ncx_path = self._resolve_archive_path(package.opf_path, ncx_item.href)
                if ncx_path is not None:
                    try:
                        ncx_document = self._read_archive_text(archive, ncx_path, epub_path=epub_path)
                        entries = self._read_ncx_entries(ncx_document)
                        if entries:
                            return entries
                        return []
                    except EpubExtractionError:
                        return []
        return None

    def _chapters_from_navigation(
        self,
        package: EpubPackage,
        spine_documents: list[EpubSpineDocument],
        nav_entries: list[tuple[str, str]],
    ) -> list[Chapter]:
        """Build chapters by mapping navigation entries to OPF spine positions."""

        spine_index_by_path: dict[PurePosixPath, int] = {
            document.archive_path: index for index, document in enumerate(spine_documents)
        }

        resolved_starts: list[tuple[int, str]] = []
        last_start = -1
        for raw_href, raw_title in nav_entries:
            candidate_path = self._resolve_archive_path(package.opf_path, raw_href)
            if candidate_path is None:
                continue
            start_index = spine_index_by_path.get(candidate_path)
            if start_index is None:
                continue
            if start_index <= last_start:
                continue
            title = self._normalize_optional_text(raw_title) or f"Chapter {len(resolved_starts) + 1}"
            resolved_starts.append((start_index, title))
            last_start = start_index

        if not resolved_starts:
            return []

        chapters: list[Chapter] = []
        for position, (start, title) in enumerate(resolved_starts):
            end = len(spine_documents)
            if position + 1 < len(resolved_starts):
                end = resolved_starts[position + 1][0]
            if end <= start:
                continue
            text = "\n\n".join(
                item.text for item in spine_documents[start:end] if item.text.strip()
            ).strip()
            chapter_text = text if text else title
            chapters.append(Chapter(index=len(chapters) + 1, title=title, text=chapter_text))
        return chapters

    def _read_nav_xhtml_entries(self, content: str) -> list[tuple[str, str]]:
        """Parse EPUB3 nav XHTML and return chapter entries in source order."""

        root = self._parse_xml(content, context="EPUB nav document")
        toc_nodes = root.findall(".//*[@epub:type='toc']", {"epub": "http://www.idpf.org/2007/ops"})
        if not toc_nodes:
            toc_nodes = root.findall(".//*[@type='toc']")
        if not toc_nodes:
            toc_nodes = root.findall(".//{*}nav")
        if not toc_nodes:
            return []

        entries: list[tuple[str, str]] = []
        for toc_node in toc_nodes:
            for anchor in toc_node.findall(".//{*}a"):
                href = self._normalize_optional_text(anchor.attrib.get("href", ""))
                if href is None:
                    continue
                title = self._normalize_optional_text("".join(anchor.itertext())) or href
                entries.append((href, title))
            if entries:
                break
        return entries

    def _read_ncx_entries(self, content: str) -> list[tuple[str, str]]:
        """Parse EPUB2 NCX navigation and return chapter entries in source order."""

        root = self._parse_xml(content, context="EPUB NCX document")
        entries: list[tuple[str, str]] = []
        for nav_point in root.findall(".//{*}navPoint"):
            content_node = nav_point.find(".//{*}content")
            if content_node is None:
                continue
            src = self._normalize_optional_text(content_node.attrib.get("src", ""))
            if src is None:
                continue
            title = self._normalize_optional_text(
                nav_point.findtext(".//{*}text", default="")
            ) or src
            entries.append((src, title))
        return entries

    def _extract_xhtml_text(self, content: str) -> str:
        """Extract deterministic plain text from one XHTML content document."""

        parser = _XhtmlTextExtractor()
        parser.feed(content)
        parser.close()
        return parser.text()

    @staticmethod
    def _parse_xml(content: str, context: str) -> ET.Element:
        """Parse XML content and map parser failures to extraction error."""

        try:
            return ET.fromstring(content)
        except ET.ParseError as exc:
            raise EpubExtractionError(f"Failed to parse {context}: {exc}") from exc

    @staticmethod
    def _normalize_optional_text(value: str | None) -> str | None:
        """Normalize optional text by trimming and collapsing internal whitespace."""

        if value is None:
            return None
        collapsed = " ".join(value.split())
        return collapsed if collapsed else None

    @staticmethod
    def _open_epub(epub_path: Path) -> zipfile.ZipFile:
        """Open EPUB archive with deterministic missing/corruption diagnostics."""

        if not epub_path.exists():
            raise EpubExtractionError(f"Input EPUB not found: {epub_path}")
        try:
            return zipfile.ZipFile(epub_path)
        except zipfile.BadZipFile as exc:
            raise EpubExtractionError(f"EPUB archive is invalid: {epub_path}") from exc

    @staticmethod
    def _read_archive_text(
        archive: zipfile.ZipFile,
        archive_path: PurePosixPath,
        *,
        epub_path: Path,
    ) -> str:
        """Read UTF-8 text from an archive path with deterministic diagnostics."""

        try:
            raw = archive.read(archive_path.as_posix())
        except KeyError as exc:
            raise EpubExtractionError(
                f"EPUB entry `{archive_path.as_posix()}` is missing in `{epub_path}`."
            ) from exc
        return raw.decode("utf-8-sig", errors="replace")

    @staticmethod
    def _resolve_archive_path(base_path: PurePosixPath, href: str) -> PurePosixPath | None:
        """Resolve relative archive paths from OPF-local href values."""

        candidate = href.split("#", 1)[0].strip()
        if not candidate:
            return None
        base_dir = base_path.parent.as_posix()
        normalized = posixpath.normpath(posixpath.join(base_dir, candidate))
        if normalized.startswith("../") or normalized == "..":
            return None
        return PurePosixPath(normalized)
