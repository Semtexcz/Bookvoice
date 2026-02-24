"""Resume command integration tests for artifact recovery and run metadata."""

import json
from pathlib import Path

from tests.fixture_paths import canonical_content_pdf_fixture_path

import pytest
from typer.testing import CliRunner

from bookvoice.cli import app
from bookvoice.config import BookvoiceConfig, ProviderRuntimeConfig
from bookvoice.io.storage import ArtifactStore
from bookvoice.models.datatypes import AudioPart, RewriteResult
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
    fixture_pdf = canonical_content_pdf_fixture_path()

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
    assert resumed_payload["extra"]["resume_validation_status"] == "recoverable"
    assert resumed_payload["extra"]["resume_validation_next_stage"] == "translate"
    assert resumed_payload["extra"]["resume_validation_issue_count"] == "0"
    assert isinstance(resumed_payload["extra"]["resume_validation_diagnostics"], str)
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
    fixture_pdf = canonical_content_pdf_fixture_path()

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
    fixture_pdf = canonical_content_pdf_fixture_path()

    build_result = runner.invoke(app, ["build", str(fixture_pdf), "--out", str(out_dir)])
    assert build_result.exit_code == 0, build_result.output

    def _unexpected_tts(
        self: BookvoicePipeline,
        rewrites: list[RewriteResult],
        config: BookvoiceConfig,
        store: ArtifactStore,
        runtime_config: ProviderRuntimeConfig | None = None,
    ) -> list[AudioPart]:
        """Fail test when resume unexpectedly executes TTS."""

        _ = (self, rewrites, config, store, runtime_config)
        raise AssertionError("TTS should not run during full-resume artifact reuse.")

    def _unexpected_merge(
        self: BookvoicePipeline,
        audio_parts: list[AudioPart],
        config: BookvoiceConfig,
        store: ArtifactStore,
        output_path: Path | None = None,
    ) -> Path:
        """Fail test when resume unexpectedly executes merge."""

        _ = (self, audio_parts, config, store, output_path)
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
    fixture_pdf = canonical_content_pdf_fixture_path()

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

    def _counting_tts(
        self: BookvoicePipeline,
        rewrites: list[RewriteResult],
        config: BookvoiceConfig,
        store: ArtifactStore,
        runtime_config: ProviderRuntimeConfig | None = None,
    ) -> list[AudioPart]:
        """Count TTS calls while delegating to original synthesis logic."""

        tts_calls["count"] += 1
        return original_tts(self, rewrites, config, store, runtime_config)

    def _counting_merge(
        self: BookvoicePipeline,
        audio_parts: list[AudioPart],
        config: BookvoiceConfig,
        store: ArtifactStore,
        output_path: Path | None = None,
    ) -> Path:
        """Count merge calls while delegating to original merge logic."""

        merge_calls["count"] += 1
        return original_merge(self, audio_parts, config, store, output_path)

    monkeypatch.setattr("bookvoice.pipeline.BookvoicePipeline._tts", _counting_tts)
    monkeypatch.setattr("bookvoice.pipeline.BookvoicePipeline._merge", _counting_merge)

    resume_result = runner.invoke(app, ["resume", str(manifest_path)])
    assert resume_result.exit_code == 0, resume_result.output
    assert tts_calls["count"] == 1
    assert merge_calls["count"] == 1
    assert missing_audio_path.exists()


def test_resume_fails_for_mixed_missing_and_stale_critical_artifacts(tmp_path: Path) -> None:
    """Resume should fail fast when an upstream critical artifact is missing but downstream exists."""

    runner = CliRunner()
    out_dir = tmp_path / "out"
    fixture_pdf = canonical_content_pdf_fixture_path()

    build_result = runner.invoke(app, ["build", str(fixture_pdf), "--out", str(out_dir)])
    assert build_result.exit_code == 0, build_result.output

    manifest_path = next(out_dir.glob("run-*/run_manifest.json"))
    manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    chunks_path = Path(manifest_payload["extra"]["chunks"])
    translations_path = Path(manifest_payload["extra"]["translations"])
    chunks_path.unlink()
    assert translations_path.exists()

    resume_result = runner.invoke(app, ["resume", str(manifest_path)])
    assert resume_result.exit_code == 1
    assert "resume failed at stage `resume-validation`" in resume_result.output
    assert str(chunks_path) in resume_result.output
    assert str(translations_path) in resume_result.output
    assert "Manual cleanup required" in resume_result.output


def test_resume_fails_for_cross_artifact_payload_mismatch(tmp_path: Path) -> None:
    """Resume should fail for mismatched chunk/translation payload signatures."""

    runner = CliRunner()
    out_dir = tmp_path / "out"
    fixture_pdf = canonical_content_pdf_fixture_path()

    build_result = runner.invoke(app, ["build", str(fixture_pdf), "--out", str(out_dir)])
    assert build_result.exit_code == 0, build_result.output

    manifest_path = next(out_dir.glob("run-*/run_manifest.json"))
    manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    translations_path = Path(manifest_payload["extra"]["translations"])
    translations_payload = json.loads(translations_path.read_text(encoding="utf-8"))
    assert isinstance(translations_payload["translations"], list)
    assert len(translations_payload["translations"]) > 1
    translations_payload["translations"] = translations_payload["translations"][:-1]
    translations_path.write_text(json.dumps(translations_payload), encoding="utf-8")

    resume_result = runner.invoke(app, ["resume", str(manifest_path)])
    assert resume_result.exit_code == 1
    assert "resume failed at stage `resume-validation`" in resume_result.output
    assert str(Path(manifest_payload["extra"]["chunks"])) in resume_result.output
    assert str(translations_path) in resume_result.output
    assert "count/order mismatch" in resume_result.output
