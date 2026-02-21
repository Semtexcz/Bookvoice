"""Integration tests for segmented-part pipeline artifacts and resume stability."""

from __future__ import annotations

import json
from pathlib import Path

from pytest import MonkeyPatch
from typer.testing import CliRunner

from bookvoice.cli import app
from bookvoice.models.datatypes import Chapter, ChapterStructureUnit


def _split_stub(*_: object, **__: object) -> tuple[list[Chapter], str, str]:
    """Return deterministic chapter split output for segmented artifact tests."""

    return (
        [
            Chapter(index=1, title="Chapter One", text="Chapter one."),
            Chapter(index=2, title="Chapter Two", text="Chapter two."),
        ],
        "text_heuristic",
        "outline_missing",
    )


def _structure_stub(
    *_: object,
    **__: object,
) -> list[ChapterStructureUnit]:
    """Return deterministic normalized units that produce multiple chapter parts."""

    return [
        ChapterStructureUnit(
            order_index=1,
            chapter_index=1,
            chapter_title="Chapter One",
            subchapter_index=1,
            subchapter_title="1.1",
            text="A" * 1200,
            char_start=0,
            char_end=1200,
            source="text_heuristic",
        ),
        ChapterStructureUnit(
            order_index=2,
            chapter_index=1,
            chapter_title="Chapter One",
            subchapter_index=2,
            subchapter_title="1.2",
            text="B" * 1200,
            char_start=1201,
            char_end=2401,
            source="text_heuristic",
        ),
        ChapterStructureUnit(
            order_index=3,
            chapter_index=2,
            chapter_title="Chapter Two",
            subchapter_index=1,
            subchapter_title="2.1",
            text="C" * 800,
            char_start=0,
            char_end=800,
            source="text_heuristic",
        ),
    ]


def test_build_command_emits_segmented_part_artifacts(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    """Build should persist chapter/part mapping and source references in artifacts."""

    monkeypatch.setattr("bookvoice.pipeline.BookvoicePipeline._split_chapters", _split_stub)
    monkeypatch.setattr(
        "bookvoice.pipeline.BookvoicePipeline._extract_normalized_structure",
        _structure_stub,
    )
    runner = CliRunner()
    out_dir = tmp_path / "out"
    fixture_pdf = Path("tests/files/zero_to_one.pdf")

    result = runner.invoke(app, ["build", str(fixture_pdf), "--out", str(out_dir)])
    assert result.exit_code == 0, result.output

    manifest_path = next(out_dir.glob("run-*/run_manifest.json"))
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    run_root = Path(payload["extra"]["run_root"])

    chunks_payload = json.loads((run_root / "text/chunks.json").read_text(encoding="utf-8"))
    assert chunks_payload["metadata"]["planner"]["strategy"] == "text_budget_segment_planner"
    assert chunks_payload["metadata"]["planner"]["source_structure_order_indices"] == [1, 2, 3]
    assert [item["part_index"] for item in chunks_payload["chunks"]] == [1, 2, 1]
    assert [item["source_order_indices"] for item in chunks_payload["chunks"]] == [[1], [2], [3]]

    parts_payload = json.loads((run_root / "audio/parts.json").read_text(encoding="utf-8"))
    assert [item["part_index"] for item in parts_payload["audio_parts"]] == [1, 2, 1]
    assert [item["part_id"] for item in parts_payload["audio_parts"]] == [
        "001_01_chapter-one",
        "001_02_chapter-one",
        "002_01_chapter-two",
    ]
    assert [Path(item["path"]).name for item in parts_payload["audio_parts"]] == [
        "001_01_chapter-one.wav",
        "001_02_chapter-one.wav",
        "002_01_chapter-two.wav",
    ]
    assert [item["source_order_indices"] for item in parts_payload["audio_parts"]] == [
        [1],
        [2],
        [3],
    ]
    assert parts_payload["metadata"]["chapter_part_map"] == [
        {
            "chapter_index": 1,
            "part_index": 1,
            "part_id": "001_01_chapter-one",
            "source_order_indices": [1],
            "filename": "001_01_chapter-one.wav",
        },
        {
            "chapter_index": 1,
            "part_index": 2,
            "part_id": "001_02_chapter-one",
            "source_order_indices": [2],
            "filename": "001_02_chapter-one.wav",
        },
        {
            "chapter_index": 2,
            "part_index": 1,
            "part_id": "002_01_chapter-two",
            "source_order_indices": [3],
            "filename": "002_01_chapter-two.wav",
        },
    ]
    assert [item["filename"] for item in parts_payload["audio_parts"]] == [
        "001_01_chapter-one.wav",
        "001_02_chapter-one.wav",
        "002_01_chapter-two.wav",
    ]

    assert payload["extra"]["part_count"] == "3"
    assert payload["extra"]["chapter_part_map_csv"] == "1:1,1:2,2:1"
    assert (
        payload["extra"]["part_filenames_csv"]
        == "001_01_chapter-one.wav,001_02_chapter-one.wav,002_01_chapter-two.wav"
    )
    assert payload["extra"]["part_source_structure_indices_csv"] == "1,2,3"


def test_resume_command_keeps_segmented_part_identifiers_stable(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    """Resume should regenerate deterministic part IDs and chapter/part mapping."""

    monkeypatch.setattr("bookvoice.pipeline.BookvoicePipeline._split_chapters", _split_stub)
    monkeypatch.setattr(
        "bookvoice.pipeline.BookvoicePipeline._extract_normalized_structure",
        _structure_stub,
    )
    runner = CliRunner()
    out_dir = tmp_path / "out"
    fixture_pdf = Path("tests/files/zero_to_one.pdf")

    build_result = runner.invoke(app, ["build", str(fixture_pdf), "--out", str(out_dir)])
    assert build_result.exit_code == 0, build_result.output

    manifest_path = next(out_dir.glob("run-*/run_manifest.json"))
    manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    before_parts_payload = json.loads(
        Path(manifest_payload["extra"]["audio_parts"]).read_text(encoding="utf-8")
    )
    before_part_ids = [item["part_id"] for item in before_parts_payload["audio_parts"]]

    Path(manifest_payload["extra"]["chunks"]).unlink()
    Path(manifest_payload["extra"]["translations"]).unlink()
    Path(manifest_payload["extra"]["rewrites"]).unlink()
    Path(manifest_payload["extra"]["audio_parts"]).unlink()
    Path(manifest_payload["merged_audio_path"]).unlink()

    resume_result = runner.invoke(app, ["resume", str(manifest_path)])
    assert resume_result.exit_code == 0, resume_result.output
    assert "Resumed from stage: chunk" in resume_result.output

    resumed_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    resumed_parts_payload = json.loads(
        Path(resumed_payload["extra"]["audio_parts"]).read_text(encoding="utf-8")
    )
    resumed_part_ids = [item["part_id"] for item in resumed_parts_payload["audio_parts"]]

    assert resumed_part_ids == before_part_ids
    assert resumed_payload["extra"]["chapter_part_map_csv"] == "1:1,1:2,2:1"
    assert (
        resumed_payload["extra"]["part_filenames_csv"]
        == "001_01_chapter-one.wav,001_02_chapter-one.wav,002_01_chapter-two.wav"
    )
    assert resumed_payload["extra"]["part_source_structure_indices_csv"] == "1,2,3"
