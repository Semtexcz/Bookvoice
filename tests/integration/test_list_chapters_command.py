"""Integration tests for the chapter-listing CLI command."""

from pathlib import Path

from typer.testing import CliRunner

from bookvoice.cli import app


def test_list_chapters_command_lists_from_artifact(tmp_path: Path) -> None:
    """List-chapters should print deterministic chapter rows from chapters artifact JSON."""

    runner = CliRunner()
    out_dir = tmp_path / "out"
    fixture_pdf = Path("tests/files/canonical_synthetic_fixture.pdf")

    chapters_result = runner.invoke(
        app, ["chapters-only", str(fixture_pdf), "--out", str(out_dir)]
    )
    assert chapters_result.exit_code == 0, chapters_result.output

    chapters_path = next(out_dir.glob("run-*/text/chapters.json"))
    result = runner.invoke(
        app,
        ["list-chapters", "--chapters-artifact", str(chapters_path)],
    )

    assert result.exit_code == 0, result.output
    assert "Chapter source:" in result.output
    assert any(line.startswith("1. ") for line in result.output.splitlines())


def test_list_chapters_command_fails_for_missing_artifact(tmp_path: Path) -> None:
    """List-chapters should report a stage-aware error for missing chapter artifact file."""

    runner = CliRunner()
    missing_path = tmp_path / "missing/chapters.json"

    result = runner.invoke(
        app,
        ["list-chapters", "--chapters-artifact", str(missing_path)],
    )

    assert result.exit_code == 1
    assert "list-chapters failed at stage `chapters-artifact`" in result.output
    assert "Chapters artifact not found" in result.output
