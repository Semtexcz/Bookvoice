"""Unit tests for translate-only reader export contract helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from bookvoice.pipeline.reader_exports import (
    reader_export_formats_csv,
    reader_export_manifest_metadata,
    reader_export_output_path,
    resolve_reader_export_formats,
)


def test_resolve_reader_export_formats_normalizes_supported_values() -> None:
    """Reader export format parser should normalize values to canonical order."""

    assert resolve_reader_export_formats(None) == tuple()
    assert resolve_reader_export_formats("none") == tuple()
    assert resolve_reader_export_formats(" epub ") == ("epub",)
    assert resolve_reader_export_formats("pdf") == ("pdf",)
    assert resolve_reader_export_formats("pdf,epub") == ("epub", "pdf")


def test_resolve_reader_export_formats_rejects_invalid_tokens() -> None:
    """Reader export format parser should fail on unsupported or mixed-none values."""

    with pytest.raises(ValueError, match="Supported: `epub`, `pdf`, or `epub,pdf`"):
        resolve_reader_export_formats("docx")
    with pytest.raises(ValueError, match="cannot be combined"):
        resolve_reader_export_formats("none,pdf")


def test_reader_export_manifest_metadata_is_deterministic() -> None:
    """Reader export metadata helper should build stable planned output references."""

    metadata = reader_export_manifest_metadata(
        run_root=Path("out/run-abc"),
        source_path=Path("input.epub"),
        language="cs",
        chapter_scope={
            "chapter_scope_mode": "selected",
            "chapter_scope_indices_csv": "2,4",
        },
        formats=("epub", "pdf"),
    )

    assert metadata["reader_export_requested"] == "true"
    assert metadata["reader_export_formats_csv"] == "epub,pdf"
    assert metadata["reader_export_output_dir"] == "out/run-abc/reader"
    assert metadata["reader_export_basename"] == "input.cs.chapters-2-4.translated"
    assert metadata["reader_export_planned_count"] == "2"
    assert metadata["reader_export_emitted_count"] == "0"
    assert metadata["reader_export_planned_epub"].endswith(".epub")
    assert metadata["reader_export_planned_pdf"].endswith(".pdf")
    assert reader_export_formats_csv(tuple()) == "none"


def test_reader_export_manifest_metadata_marks_partial_when_some_formats_emit() -> None:
    """Reader export metadata should mark partial status when only subset is emitted."""

    metadata = reader_export_manifest_metadata(
        run_root=Path("out/run-abc"),
        source_path=Path("input.epub"),
        language="cs",
        chapter_scope={
            "chapter_scope_mode": "all",
            "chapter_scope_label": "all",
        },
        formats=("epub", "pdf"),
        emitted_paths={"epub": Path("out/run-abc/reader/input.cs.all.translated.epub")},
    )

    assert metadata["reader_export_status"] == "partial"
    assert metadata["reader_export_emitted_count"] == "1"
    assert metadata["reader_export_emitted_epub"].endswith(".epub")


def test_reader_export_output_path_is_deterministic() -> None:
    """Reader export output path helper should preserve deterministic naming tokens."""

    path = reader_export_output_path(
        run_root=Path("out/run-xyz"),
        source_path=Path("my-input.epub"),
        language="cs",
        chapter_scope={
            "chapter_scope_mode": "selected",
            "chapter_scope_indices_csv": "3,8",
        },
        export_format="epub",
    )

    assert path.as_posix() == "out/run-xyz/reader/my-input.cs.chapters-3-8.translated.epub"
