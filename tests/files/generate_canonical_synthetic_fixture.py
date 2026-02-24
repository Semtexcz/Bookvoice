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


def _escape_pdf_text(value: str) -> str:
    """Escape literal text for safe inclusion in a PDF text stream."""

    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _page_lines(title: str, body: list[str]) -> list[str]:
    """Build deterministic page lines with a chapter heading and body paragraphs."""

    return [title, ""] + body


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


def generate_fixture(output_path: Path = OUTPUT_PATH) -> Path:
    """Generate the canonical synthetic fixture and return its path."""

    writer = PdfWriter()

    chapter_pages = [
        _page_lines(
            "Chapter 1: Orchard Ledger",
            [
                "Every week the orchard council logs weather, soil, and harvest totals.",
                "The records are synthetic and written only for this repository.",
                "A repeatable fixture keeps integration tests stable across machines.",
                "Deterministic chapter text helps chunking and chapter selection checks.",
            ],
        ),
        _page_lines(
            "Chapter 2: River Workshop",
            [
                "Engineers at the river workshop calibrate pumps with scripted routines.",
                "Each calibration report includes start time, stop time, and checksum.",
                "No external publication is quoted, copied, or transformed in this text.",
                "This chapter exists to provide predictable multi-chapter pipeline input.",
            ],
        ),
        _page_lines(
            "Chapter 3: Lantern Assembly",
            [
                "Night crews assemble lantern frames and verify every bolt torque value.",
                "Inspection rows are grouped by shift and signed with deterministic IDs.",
                "When tests request chapters two to three, this page remains selectable.",
                "The canonical fixture is short by design to keep test runtime low.",
            ],
        ),
        _page_lines(
            "Chapter 4: Harbor Summary",
            [
                "At quarter end, the harbor team compiles a concise operational summary.",
                "The summary references only synthetic locations and synthetic personnel.",
                "Pipeline smoke tests rely on this final section for non-empty output.",
                "All content in this PDF is repository-owned and safe to redistribute.",
            ],
        ),
    ]

    for lines in chapter_pages:
        _add_text_page(writer, lines)

    for page_index, title in enumerate(
        [
            "Chapter 1: Orchard Ledger",
            "Chapter 2: River Workshop",
            "Chapter 3: Lantern Assembly",
            "Chapter 4: Harbor Summary",
        ]
    ):
        writer.add_outline_item(title, page_number=page_index)

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
