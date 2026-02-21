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
