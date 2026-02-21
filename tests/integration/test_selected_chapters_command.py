"""Integration tests for selected chapter processing in CLI build and resume flows."""

import json
from pathlib import Path

from pytest import MonkeyPatch
from typer.testing import CliRunner

from bookvoice.cli import app
from bookvoice.models.datatypes import Chapter


def _multi_chapter_split_stub(*_: object, **__: object) -> tuple[list[Chapter], str, str]:
    """Return deterministic multi-chapter split output for selection integration tests."""

    chapters = [
        Chapter(index=index, title=f"Chapter {index}", text=f"Chapter {index} text.")
        for index in range(1, 5)
    ]
    return chapters, "text_heuristic", "outline_unavailable"


def test_build_command_processes_only_selected_chapters(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    """Build should process only selected chapters and persist chapter scope metadata."""

    monkeypatch.setattr("bookvoice.pipeline.BookvoicePipeline._split_chapters", _multi_chapter_split_stub)
    runner = CliRunner()
    out_dir = tmp_path / "out"
    fixture_pdf = Path("tests/files/zero_to_one.pdf")

    result = runner.invoke(
        app,
        ["build", str(fixture_pdf), "--out", str(out_dir), "--chapters", "3,1-2"],
    )

    assert result.exit_code == 0, result.output
    assert "Chapter scope: selected (1-3)" in result.output

    manifest_path = next(out_dir.glob("run-*/run_manifest.json"))
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    run_root = Path(payload["extra"]["run_root"])
    assert payload["extra"]["chapter_scope_mode"] == "selected"
    assert payload["extra"]["chapter_scope_label"] == "1-3"
    assert payload["extra"]["chapter_scope_indices_csv"] == "1,2,3"
    assert "bookvoice_merged.chapters_1_2_3.wav" in payload["merged_audio_path"]

    chunks_payload = json.loads((run_root / "text/chunks.json").read_text(encoding="utf-8"))
    translations_payload = json.loads(
        (run_root / "text/translations.json").read_text(encoding="utf-8")
    )
    rewrites_payload = json.loads((run_root / "text/rewrites.json").read_text(encoding="utf-8"))
    audio_parts_payload = json.loads((run_root / "audio/parts.json").read_text(encoding="utf-8"))

    assert {item["chapter_index"] for item in chunks_payload["chunks"]} == {1, 2, 3}
    assert {
        item["chunk"]["chapter_index"] for item in translations_payload["translations"]
    } == {1, 2, 3}
    assert {
        item["translation"]["chunk"]["chapter_index"] for item in rewrites_payload["rewrites"]
    } == {1, 2, 3}
    assert {item["chapter_index"] for item in audio_parts_payload["audio_parts"]} == {1, 2, 3}


def test_build_command_rejects_invalid_chapter_selection(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    """Build should fail with stage-aware diagnostics on invalid chapter selection."""

    monkeypatch.setattr("bookvoice.pipeline.BookvoicePipeline._split_chapters", _multi_chapter_split_stub)
    runner = CliRunner()
    out_dir = tmp_path / "out"
    fixture_pdf = Path("tests/files/zero_to_one.pdf")

    result = runner.invoke(
        app,
        ["build", str(fixture_pdf), "--out", str(out_dir), "--chapters", "2-4,4"],
    )

    assert result.exit_code == 1
    assert "build failed at stage `chapter-selection`" in result.output
    assert "Overlapping chapter selection" in result.output


def test_resume_command_keeps_selected_scope_when_regenerating_artifacts(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    """Resume should regenerate only selected chapter artifacts for partial runs."""

    monkeypatch.setattr("bookvoice.pipeline.BookvoicePipeline._split_chapters", _multi_chapter_split_stub)
    runner = CliRunner()
    out_dir = tmp_path / "out"
    fixture_pdf = Path("tests/files/zero_to_one.pdf")

    build_result = runner.invoke(
        app,
        ["build", str(fixture_pdf), "--out", str(out_dir), "--chapters", "2-3"],
    )
    assert build_result.exit_code == 0, build_result.output

    manifest_path = next(out_dir.glob("run-*/run_manifest.json"))
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    Path(payload["extra"]["chunks"]).unlink()
    Path(payload["extra"]["translations"]).unlink()
    Path(payload["extra"]["rewrites"]).unlink()
    Path(payload["extra"]["audio_parts"]).unlink()
    Path(payload["merged_audio_path"]).unlink()

    resume_result = runner.invoke(app, ["resume", str(manifest_path)])
    assert resume_result.exit_code == 0, resume_result.output

    resumed_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    chunks_payload = json.loads(Path(resumed_payload["extra"]["chunks"]).read_text(encoding="utf-8"))
    assert {item["chapter_index"] for item in chunks_payload["chunks"]} == {2, 3}
