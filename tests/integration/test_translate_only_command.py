"""Translate-only command integration tests for deterministic text artifacts."""

import json
from pathlib import Path

from tests.fixture_paths import canonical_content_pdf_fixture_path

from pytest import MonkeyPatch
from typer.testing import CliRunner

from bookvoice.cli import app


def test_translate_only_command_creates_expected_artifacts_without_audio(
    tmp_path: Path,
) -> None:
    """Translate-only should persist text artifacts and avoid rewrite/TTS/merge outputs."""

    runner = CliRunner()
    out_dir = tmp_path / "out"
    fixture_pdf = canonical_content_pdf_fixture_path()

    result = runner.invoke(
        app,
        [
            "translate-only",
            str(fixture_pdf),
            "--out",
            str(out_dir),
            "--chapters",
            "2-3",
        ],
    )

    assert result.exit_code == 0, result.output

    manifest_path = next(out_dir.glob("run-*/run_manifest.json"))
    run_root = manifest_path.parent
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))

    expected_paths = (
        run_root / "text/raw.txt",
        run_root / "text/clean.txt",
        run_root / "text/chapters.json",
        run_root / "text/chunks.json",
        run_root / "text/translations.json",
    )
    for artifact_path in expected_paths:
        assert artifact_path.exists(), f"Expected artifact missing: {artifact_path}"

    assert not (run_root / "text/rewrites.json").exists()
    assert not (run_root / "audio/parts.json").exists()
    assert not (run_root / "audio/bookvoice_merged.wav").exists()

    assert payload["extra"]["pipeline_mode"] == "translate_only"
    assert payload["extra"]["chapter_scope_mode"] == "selected"
    assert payload["extra"]["chapter_scope_indices_csv"] == "2,3"
    assert Path(payload["extra"]["translations"]).exists()
    assert "Translations artifact:" in result.output
    assert "Cost LLM (USD):" in result.output
    assert "Cost TTS (USD): 0.000000" in result.output


def test_translate_only_command_reports_stage_error_with_hint(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    """Translate-only should render stage-aware failure diagnostics on pipeline errors."""

    from bookvoice.errors import PipelineStageError

    def _failing_translate_only(*_: object, **__: object) -> None:
        """Raise stage error to validate CLI rendering for translate-only command."""

        raise PipelineStageError(
            stage="translate",
            detail="Provider authentication failed for OpenAI API credentials.",
            hint="Set a valid API key via `bookvoice credentials`.",
        )

    monkeypatch.setattr(
        "bookvoice.cli.BookvoicePipeline.run_translate_only",
        _failing_translate_only,
    )
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["translate-only", str(tmp_path / "input.pdf"), "--out", str(tmp_path / "out")],
    )

    assert result.exit_code == 1
    assert "translate-only failed at stage `translate`" in result.output
    assert "Hint: Set a valid API key via `bookvoice credentials`." in result.output
