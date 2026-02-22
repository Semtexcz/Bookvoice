"""Resume command integration tests for artifact recovery and run metadata."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from bookvoice.cli import app
from bookvoice.pipeline import BookvoicePipeline


def _schema_shape(value: object) -> object:
    """Normalize nested payload value into a type/shape-only representation."""

    if isinstance(value, dict):
        return {key: _schema_shape(item) for key, item in sorted(value.items())}
    if isinstance(value, list):
        if not value:
            return []
        return [_schema_shape(value[0])]
    return type(value).__name__


def test_resume_command_recovers_from_interrupted_run(tmp_path: Path) -> None:
    """Resume command should rebuild missing artifacts and preserve deterministic costs."""

    runner = CliRunner()
    out_dir = tmp_path / "out"
    fixture_pdf = Path("tests/files/zero_to_one.pdf")

    build_result = runner.invoke(app, ["build", str(fixture_pdf), "--out", str(out_dir)])
    assert build_result.exit_code == 0, build_result.output

    manifest_path = next(out_dir.glob("run-*/run_manifest.json"))
    manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))

    raw_text_path = Path(manifest_payload["extra"]["raw_text"])
    raw_before = raw_text_path.read_text(encoding="utf-8")

    Path(manifest_payload["extra"]["translations"]).unlink()
    Path(manifest_payload["extra"]["rewrites"]).unlink()
    Path(manifest_payload["extra"]["audio_parts"]).unlink()
    Path(manifest_payload["merged_audio_path"]).unlink()

    resume_result = runner.invoke(app, ["resume", str(manifest_path)])
    assert resume_result.exit_code == 0, resume_result.output
    assert "Resumed from stage: translate" in resume_result.output

    resumed_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert Path(resumed_payload["extra"]["translations"]).exists()
    assert Path(resumed_payload["extra"]["rewrites"]).exists()
    assert Path(resumed_payload["extra"]["audio_parts"]).exists()
    assert Path(resumed_payload["merged_audio_path"]).exists()
    assert raw_text_path.read_text(encoding="utf-8") == raw_before
    assert resumed_payload["extra"]["chapter_source"] in {"pdf_outline", "text_heuristic", "unknown"}
    assert isinstance(resumed_payload["extra"]["chapter_fallback_reason"], str)
    assert resumed_payload["total_llm_cost_usd"] > 0.0
    assert resumed_payload["total_tts_cost_usd"] > 0.0
    assert resumed_payload["total_cost_usd"] == pytest.approx(
        resumed_payload["total_llm_cost_usd"] + resumed_payload["total_tts_cost_usd"]
    )
    assert "Cost Total (USD):" in resume_result.output


def test_resume_preserves_translation_and_rewrite_payload_schema(tmp_path: Path) -> None:
    """Resume should regenerate translation/rewrite artifacts with identical payload schema."""

    runner = CliRunner()
    out_dir = tmp_path / "out"
    fixture_pdf = Path("tests/files/zero_to_one.pdf")

    build_result = runner.invoke(app, ["build", str(fixture_pdf), "--out", str(out_dir)])
    assert build_result.exit_code == 0, build_result.output

    manifest_path = next(out_dir.glob("run-*/run_manifest.json"))
    manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))

    before_translations_payload = json.loads(
        Path(manifest_payload["extra"]["translations"]).read_text(encoding="utf-8")
    )
    before_rewrites_payload = json.loads(
        Path(manifest_payload["extra"]["rewrites"]).read_text(encoding="utf-8")
    )

    Path(manifest_payload["extra"]["translations"]).unlink()
    Path(manifest_payload["extra"]["rewrites"]).unlink()
    Path(manifest_payload["extra"]["audio_parts"]).unlink()
    Path(manifest_payload["merged_audio_path"]).unlink()

    resume_result = runner.invoke(app, ["resume", str(manifest_path)])
    assert resume_result.exit_code == 0, resume_result.output

    resumed_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    after_translations_payload = json.loads(
        Path(resumed_payload["extra"]["translations"]).read_text(encoding="utf-8")
    )
    after_rewrites_payload = json.loads(
        Path(resumed_payload["extra"]["rewrites"]).read_text(encoding="utf-8")
    )

    assert _schema_shape(after_translations_payload) == _schema_shape(before_translations_payload)
    assert _schema_shape(after_rewrites_payload) == _schema_shape(before_rewrites_payload)


def test_resume_command_fully_reuses_existing_audio_outputs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Resume should skip TTS and merge when all artifacts and audio files are present."""

    runner = CliRunner()
    out_dir = tmp_path / "out"
    fixture_pdf = Path("tests/files/zero_to_one.pdf")

    build_result = runner.invoke(app, ["build", str(fixture_pdf), "--out", str(out_dir)])
    assert build_result.exit_code == 0, build_result.output

    def _unexpected_tts(*_: object, **__: object) -> list[object]:
        """Fail test when resume unexpectedly executes TTS."""

        raise AssertionError("TTS should not run during full-resume artifact reuse.")

    def _unexpected_merge(*_: object, **__: object) -> Path:
        """Fail test when resume unexpectedly executes merge."""

        raise AssertionError("Merge should not run during full-resume artifact reuse.")

    monkeypatch.setattr("bookvoice.pipeline.BookvoicePipeline._tts", _unexpected_tts)
    monkeypatch.setattr("bookvoice.pipeline.BookvoicePipeline._merge", _unexpected_merge)

    manifest_path = next(out_dir.glob("run-*/run_manifest.json"))
    resume_result = runner.invoke(app, ["resume", str(manifest_path)])
    assert resume_result.exit_code == 0, resume_result.output
    assert "Resumed from stage: done" in resume_result.output


def test_resume_replays_tts_and_merge_when_audio_files_are_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Resume should rerun TTS and merge when chunk WAV files are missing on disk."""

    runner = CliRunner()
    out_dir = tmp_path / "out"
    fixture_pdf = Path("tests/files/zero_to_one.pdf")

    build_result = runner.invoke(app, ["build", str(fixture_pdf), "--out", str(out_dir)])
    assert build_result.exit_code == 0, build_result.output

    manifest_path = next(out_dir.glob("run-*/run_manifest.json"))
    manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    parts_payload = json.loads(Path(manifest_payload["extra"]["audio_parts"]).read_text(encoding="utf-8"))
    missing_audio_path = Path(parts_payload["audio_parts"][0]["path"])
    missing_audio_path.unlink()

    original_tts = BookvoicePipeline._tts
    original_merge = BookvoicePipeline._merge
    tts_calls = {"count": 0}
    merge_calls = {"count": 0}

    def _counting_tts(self: BookvoicePipeline, *args: object, **kwargs: object) -> list[object]:
        """Count TTS calls while delegating to original synthesis logic."""

        tts_calls["count"] += 1
        return original_tts(self, *args, **kwargs)

    def _counting_merge(self: BookvoicePipeline, *args: object, **kwargs: object) -> Path:
        """Count merge calls while delegating to original merge logic."""

        merge_calls["count"] += 1
        return original_merge(self, *args, **kwargs)

    monkeypatch.setattr("bookvoice.pipeline.BookvoicePipeline._tts", _counting_tts)
    monkeypatch.setattr("bookvoice.pipeline.BookvoicePipeline._merge", _counting_merge)

    resume_result = runner.invoke(app, ["resume", str(manifest_path)])
    assert resume_result.exit_code == 0, resume_result.output
    assert tts_calls["count"] == 1
    assert merge_calls["count"] == 1
    assert missing_audio_path.exists()
