"""CLI error-handling tests for concise MVP diagnostics."""

from pathlib import Path

from pytest import MonkeyPatch
from typer.testing import CliRunner

from bookvoice.cli import app
from bookvoice.errors import PipelineStageError


def test_build_command_reports_stage_error_with_hint(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    """Build command should print stage-aware diagnostics and fail with exit code 1."""

    def _failing_run(*_: object, **__: object) -> None:
        """Raise a stage-specific error to simulate pipeline failure."""

        raise PipelineStageError(
            stage="extract",
            detail="Failed to extract text from PDF `broken.pdf`: Input PDF not found.",
            hint="Verify the input file exists and `pdftotext` is installed.",
        )

    monkeypatch.setattr("bookvoice.cli.BookvoicePipeline.run", _failing_run)
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["build", str(tmp_path / "broken.pdf"), "--out", str(tmp_path / "out")],
    )

    assert result.exit_code == 1
    assert "build failed at stage `extract`" in result.output
    assert "Hint: Verify the input file exists and `pdftotext` is installed." in result.output


def test_resume_command_reports_non_stage_error(monkeypatch: MonkeyPatch) -> None:
    """Resume command should still report non-stage exceptions with exit code 1."""

    def _failing_resume(*_: object, **__: object) -> None:
        """Raise a generic error to verify fallback CLI diagnostics."""

        raise RuntimeError("unexpected manifest error")

    monkeypatch.setattr("bookvoice.cli.BookvoicePipeline.resume", _failing_resume)
    runner = CliRunner()

    result = runner.invoke(app, ["resume", "out/run_manifest.json"])

    assert result.exit_code == 1
    assert "resume failed: unexpected manifest error" in result.output


def test_build_command_reports_missing_config_file() -> None:
    """Build should fail with stage-aware diagnostics when `--config` path is missing."""

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "build",
            "--config",
            "missing-bookvoice.yaml",
        ],
    )

    assert result.exit_code == 1
    assert "build failed at stage `config`" in result.output
    assert "Config file not found: `missing-bookvoice.yaml`." in result.output


def test_translate_only_reports_invalid_config_payload(tmp_path: Path) -> None:
    """Translate-only should fail fast when YAML config schema/values are invalid."""

    config_path = tmp_path / "invalid.yaml"
    config_path.write_text("output_dir: out\n", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "translate-only",
            "--config",
            str(config_path),
        ],
    )

    assert result.exit_code == 1
    assert "translate-only failed at stage `config`" in result.output
    assert "is missing required key(s): input_pdf" in result.output
