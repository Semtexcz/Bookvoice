"""Integration test for drop-cap normalization and sentence-boundary repair metadata."""

from __future__ import annotations

import json
from pathlib import Path

from pytest import MonkeyPatch
from typer.testing import CliRunner

from bookvoice.cli import app
from bookvoice.models.datatypes import Chapter


def _extract_stub(*_: object, **__: object) -> str:
    """Return deterministic raw text containing a split decorative drop-cap."""

    return (
        "E\nVERY MOMENT IN BUSINESS MATTERS. "
        'He asked this question: "What important truth?" Then he paused.'
    )


def _split_stub(
    _: object,
    text: str,
    __: Path,
) -> tuple[list[Chapter], str, str]:
    """Return one deterministic chapter from already cleaned text."""

    return ([Chapter(index=1, title="Chapter One", text=text)], "text_heuristic", "")


def _resolve_boundary_stub(
    _: object,
    text: str,
    start: int,
    __: int,
) -> tuple[int, str]:
    """Force one mid-sentence split to exercise deterministic boundary repair."""

    if start == 0:
        return text.index("important"), "forced_split_no_sentence_boundary"
    return len(text), "chapter_end"


def test_build_normalizes_drop_caps_and_repairs_sentence_boundaries(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Build should merge split drop-cap initials and repair mid-sentence chunk splits."""

    monkeypatch.setattr("bookvoice.pipeline.BookvoicePipeline._extract", _extract_stub)
    monkeypatch.setattr("bookvoice.pipeline.BookvoicePipeline._split_chapters", _split_stub)
    monkeypatch.setattr(
        "bookvoice.pipeline.BookvoicePipeline._extract_normalized_structure",
        lambda *_args, **_kwargs: [],
    )
    monkeypatch.setattr("bookvoice.text.chunking.Chunker._resolve_boundary", _resolve_boundary_stub)

    runner = CliRunner()
    out_dir = tmp_path / "out"
    fixture_pdf = Path("tests/files/zero_to_one.pdf")

    result = runner.invoke(app, ["build", str(fixture_pdf), "--out", str(out_dir)])
    assert result.exit_code == 0, result.output

    manifest_path = next(out_dir.glob("run-*/run_manifest.json"))
    manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    run_root = Path(manifest_payload["extra"]["run_root"])

    clean_text = (run_root / "text/clean.txt").read_text(encoding="utf-8")
    assert "E\nVERY" not in clean_text
    assert "EVERY MOMENT IN BUSINESS MATTERS." in clean_text

    chapters_payload = json.loads((run_root / "text/chapters.json").read_text(encoding="utf-8"))
    assert chapters_payload["metadata"]["normalization"]["drop_cap_merges_count"] == 1

    chunks_payload = json.loads((run_root / "text/chunks.json").read_text(encoding="utf-8"))
    assert chunks_payload["metadata"]["sentence_boundary_repairs_count"] == 1
    assert chunks_payload["chunks"][0]["text"].endswith('important truth?" ')
    assert chunks_payload["chunks"][1]["text"].startswith("Then he paused.")

    assert manifest_payload["extra"]["drop_cap_merges_count"] == "1"
    assert manifest_payload["extra"]["sentence_boundary_repairs_count"] == "1"
