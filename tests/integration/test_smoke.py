"""Smoke tests for the end-to-end `bookvoice build` command."""

from pathlib import Path

from pytest import MonkeyPatch
from typer.testing import CliRunner

from bookvoice.cli import app
from bookvoice.errors import PipelineStageError


def test_build_smoke_creates_manifest_and_audio(tmp_path: Path) -> None:
    """Build smoke test should produce core end artifacts from a text PDF fixture."""

    runner = CliRunner()
    out_dir = tmp_path / "out"
    fixture_pdf = Path("tests/files/canonical_synthetic_fixture.pdf")

    result = runner.invoke(app, ["build", str(fixture_pdf), "--out", str(out_dir)])

    assert result.exit_code == 0, result.output

    manifests = sorted(out_dir.glob("run-*/run_manifest.json"))
    merged_files = sorted(out_dir.glob("run-*/audio/bookvoice_merged.wav"))

    assert manifests, "manifest should be written"
    assert merged_files, "merged audio should be written"
    assert merged_files[0].stat().st_size > 44, "merged WAV should contain audio data"


def test_build_smoke_failure_output_includes_stage(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    """Smoke failure output should clearly report the failing pipeline stage."""

    def _failing_run(*_: object, **__: object) -> None:
        """Raise a stage-specific pipeline exception for smoke diagnostics."""

        raise PipelineStageError(
            stage="chunk",
            detail="Failed to chunk chapters: target size must be positive.",
            hint="Verify chapter artifacts are well-formed and chunk size is positive.",
        )

    monkeypatch.setattr("bookvoice.cli.BookvoicePipeline.run", _failing_run)

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["build", str(tmp_path / "input.pdf"), "--out", str(tmp_path / "out")],
    )

    assert result.exit_code == 1
    assert "build failed at stage `chunk`" in result.output
