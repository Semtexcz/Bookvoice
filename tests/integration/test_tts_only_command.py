"""TTS-only command integration tests for manifest-driven replay behavior."""

import json
from pathlib import Path

import pytest
from pytest import MonkeyPatch
from typer.testing import CliRunner

from bookvoice.cli import app


def test_tts_only_command_replays_tts_merge_without_upstream_stages(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    """TTS-only should run only TTS/merge/manifest stages from prior rewrite artifacts."""

    runner = CliRunner()
    out_dir = tmp_path / "out"
    fixture_pdf = Path("tests/files/zero_to_one.pdf")

    build_result = runner.invoke(app, ["build", str(fixture_pdf), "--out", str(out_dir)])
    assert build_result.exit_code == 0, build_result.output

    manifest_path = next(out_dir.glob("run-*/run_manifest.json"))
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    Path(payload["extra"]["audio_parts"]).unlink()
    Path(payload["merged_audio_path"]).unlink()

    def _unexpected_stage(*_: object, **__: object) -> object:
        """Fail test when upstream stages are unexpectedly executed."""

        raise AssertionError("Upstream stages must not run during `tts-only` replay.")

    monkeypatch.setattr("bookvoice.pipeline.BookvoicePipeline._extract", _unexpected_stage)
    monkeypatch.setattr("bookvoice.pipeline.BookvoicePipeline._clean", _unexpected_stage)
    monkeypatch.setattr("bookvoice.pipeline.BookvoicePipeline._split_chapters", _unexpected_stage)
    monkeypatch.setattr("bookvoice.pipeline.BookvoicePipeline._chunk", _unexpected_stage)
    monkeypatch.setattr("bookvoice.pipeline.BookvoicePipeline._translate", _unexpected_stage)
    monkeypatch.setattr("bookvoice.pipeline.BookvoicePipeline._rewrite_for_audio", _unexpected_stage)

    result = runner.invoke(app, ["tts-only", str(manifest_path)])
    assert result.exit_code == 0, result.output
    assert "command=tts-only" in result.output
    assert "7/10 stage=tts" in result.output
    assert "8/10 stage=merge" in result.output
    assert "9/10 stage=package" in result.output
    assert "10/10 stage=manifest" in result.output
    assert "stage=extract" not in result.output
    assert "Audio parts artifact:" in result.output

    replayed_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert replayed_payload["extra"]["pipeline_mode"] == "tts_only"
    assert Path(replayed_payload["extra"]["audio_parts"]).exists()
    assert Path(replayed_payload["merged_audio_path"]).exists()
    assert replayed_payload["total_llm_cost_usd"] == pytest.approx(0.0)
    assert replayed_payload["total_tts_cost_usd"] > 0.0
    assert replayed_payload["total_cost_usd"] == pytest.approx(
        replayed_payload["total_llm_cost_usd"] + replayed_payload["total_tts_cost_usd"]
    )


def test_tts_only_command_reports_missing_rewrites_prerequisite(tmp_path: Path) -> None:
    """TTS-only should fail when rewrites are missing but downstream artifacts still exist."""

    runner = CliRunner()
    out_dir = tmp_path / "out"
    fixture_pdf = Path("tests/files/zero_to_one.pdf")

    build_result = runner.invoke(app, ["build", str(fixture_pdf), "--out", str(out_dir)])
    assert build_result.exit_code == 0, build_result.output

    manifest_path = next(out_dir.glob("run-*/run_manifest.json"))
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    Path(payload["extra"]["rewrites"]).unlink()

    result = runner.invoke(app, ["tts-only", str(manifest_path)])
    assert result.exit_code == 1
    assert "tts-only failed at stage `resume-validation`" in result.output
    assert "missing `rewrites`" in result.output


def test_tts_only_command_reports_corrupted_chunk_metadata_prerequisite(
    tmp_path: Path,
) -> None:
    """TTS-only should fail when chunk metadata required for replay is missing."""

    runner = CliRunner()
    out_dir = tmp_path / "out"
    fixture_pdf = Path("tests/files/zero_to_one.pdf")

    build_result = runner.invoke(app, ["build", str(fixture_pdf), "--out", str(out_dir)])
    assert build_result.exit_code == 0, build_result.output

    manifest_path = next(out_dir.glob("run-*/run_manifest.json"))
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    chunks_path = Path(payload["extra"]["chunks"])
    chunks_payload = json.loads(chunks_path.read_text(encoding="utf-8"))
    chunks_payload["metadata"] = {}
    chunks_path.write_text(
        json.dumps(chunks_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    result = runner.invoke(app, ["tts-only", str(manifest_path)])
    assert result.exit_code == 1
    assert "tts-only failed at stage `tts-only-prerequisites`" in result.output
    assert "metadata.chapter_scope" in result.output
