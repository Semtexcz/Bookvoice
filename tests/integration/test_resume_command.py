"""Resume command integration tests for artifact recovery and run metadata."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from bookvoice.cli import app


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
