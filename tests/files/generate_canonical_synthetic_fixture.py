"""Generate the canonical synthetic PDF fixture for integration and unit tests.

The generated file is deterministic and contains repository-authored text only.
"""

from __future__ import annotations

from pathlib import Path

from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

OUTPUT_PATH = Path(__file__).with_name("canonical_synthetic_fixture.pdf")
PAGE_WIDTH = 595
PAGE_HEIGHT = 842
FONT_SIZE = 12
LEFT_MARGIN = 72
TOP_Y = 780
LINE_HEIGHT = 16
MAX_LINES_PER_PAGE = 39


def _escape_pdf_text(value: str) -> str:
    """Escape literal text for safe inclusion in a PDF text stream."""

    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _page_lines(title: str, body: list[str]) -> list[str]:
    """Build deterministic page lines with a chapter heading and body paragraphs."""

    return [title, ""] + body


def _paginate_lines(lines: list[str], max_lines: int = MAX_LINES_PER_PAGE) -> list[list[str]]:
    """Split text lines into deterministic page slices of at most ``max_lines`` each."""

    return [lines[index : index + max_lines] for index in range(0, len(lines), max_lines)]


def _add_text_page(writer: PdfWriter, lines: list[str]) -> None:
    """Append a single page containing extractable text lines."""

    page = writer.add_blank_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    font_ref = writer._add_object(
        DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
            }
        )
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {
            NameObject("/Font"): DictionaryObject({NameObject("/F1"): font_ref})
        }
    )

    content_lines = [
        "BT",
        f"/F1 {FONT_SIZE} Tf",
        f"{LEFT_MARGIN} {TOP_Y} Td",
        f"{LINE_HEIGHT} TL",
    ]
    for index, line in enumerate(lines):
        escaped = _escape_pdf_text(line)
        content_lines.append(f"({escaped}) Tj")
        if index < len(lines) - 1:
            content_lines.append("T*")
    content_lines.append("ET")

    stream = DecodedStreamObject()
    stream.set_data("\n".join(content_lines).encode("latin-1"))
    page[NameObject("/Contents")] = writer._add_object(stream)


def _build_front_matter_lines(chapter_titles: list[str]) -> list[list[str]]:
    """Return deterministic front matter pages for title, legal notice, preface, and TOC."""

    title_page = [
        "A Practical Atlas of Synthetic Systems",
        "",
        "A repository-owned synthetic fixture for deterministic tests.",
        "Prepared for the Bookvoice project integration and unit suites.",
        "",
        "Author: Synthetic Editorial Committee",
        "Edition: Canonical Test Edition",
        "Publication Year: 2026",
    ]
    legal_page = [
        "Copyright and Reproduction Notice",
        "",
        "This PDF contains synthetic text authored only for this repository.",
        "No external publication is quoted, copied, transformed, or redistributed.",
        "All names, institutions, and settings are fictional and non-identifying.",
        "",
        "License Notice",
        "The fixture may be stored and redistributed with this repository.",
        "It is intended solely for deterministic software testing workflows.",
    ]
    preface_page = [
        "Preface",
        "",
        "This fixture emulates a realistic book layout with front matter and chapters.",
        "Its purpose is to test extraction, chapter planning, chunking, and manifests.",
        "Paragraph structure intentionally varies to simulate technical narrative prose.",
        "Section titles and chapter headings remain deterministic across regenerations.",
        "The text length is intentionally larger than prior fixtures for better coverage.",
    ]

    toc_page = ["Table of Contents", "", "Front Matter"]
    toc_page.append("  Preface ............................................................ iii")
    toc_page.append("  Usage Notes ....................................................... iv")
    toc_page.append("")
    toc_page.append("Part I: Foundations")
    for chapter_index, chapter_title in enumerate(chapter_titles, start=1):
        toc_page.append(
            f"  {chapter_title} .................................................... {chapter_index + 4}"
        )
    toc_page.append("")
    toc_page.append("Appendix")
    toc_page.append("  Glossary of Synthetic Terms ....................................... 99")

    return [title_page, legal_page, preface_page, toc_page]


def _chapter_body(chapter_number: int, chapter_slug: str) -> list[str]:
    """Return deterministic long-form chapter body text for a realistic fixture."""

    lines: list[str] = []
    for section_index in range(1, 6):
        lines.append(f"{chapter_number}.{section_index} {chapter_slug} Section {section_index}")
        lines.append(
            "The editorial board records observations in a strictly repeatable narrative format."
        )
        lines.append(
            "Each paragraph references synthetic operations, synthetic teams, and synthetic audits."
        )
        lines.append(
            "Deterministic wording keeps chapter extraction and chunk boundaries stable across runs."
        )
        lines.append(
            "No sentence in this fixture depends on external corpora, websites, or copyrighted books."
        )
        lines.append(
            "Operational cadence is expressed as morning review, midday execution, and evening recap."
        )
        lines.append(
            "Quality checkpoints include source verification, checksum review, and handoff signoff."
        )
        lines.append(
            "Every section closes by reaffirming repository-owned and reusable test-fixture content."
        )
        lines.append(
            "Resume workflows rely on deterministic identifiers for chunks, parts, and artifacts."
        )
        lines.append(
            "The chapter vocabulary is intentionally broad enough to emulate real-world prose variation."
        )
        lines.append("")
    return lines


def generate_fixture(output_path: Path = OUTPUT_PATH) -> Path:
    """Generate the canonical synthetic fixture and return its path."""

    writer = PdfWriter()
    chapter_titles = [
        "Chapter 1: Orchard Ledger",
        "Chapter 2: River Workshop",
        "Chapter 3: Lantern Assembly",
        "Chapter 4: Harbor Summary",
    ]
    chapter_slugs = [
        "Orchard-Ledger",
        "River-Workshop",
        "Lantern-Assembly",
        "Harbor-Summary",
    ]

    for front_matter_lines in _build_front_matter_lines(chapter_titles):
        _add_text_page(writer, front_matter_lines)

    chapter_start_pages: list[int] = []
    for chapter_number, (chapter_title, chapter_slug) in enumerate(
        zip(chapter_titles, chapter_slugs),
        start=1,
    ):
        chapter_start_pages.append(len(writer.pages))
        chapter_lines = _page_lines(chapter_title, _chapter_body(chapter_number, chapter_slug))
        for page_lines in _paginate_lines(chapter_lines):
            _add_text_page(writer, page_lines)

    for chapter_start_page, chapter_title in zip(chapter_start_pages, chapter_titles):
        writer.add_outline_item(chapter_title, page_number=chapter_start_page)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("wb") as handle:
        writer.write(handle)
    return output_path


def main() -> None:
    """Generate the canonical synthetic fixture and print the output location."""

    output_path = generate_fixture()
    print(output_path)


if __name__ == "__main__":
    main()
