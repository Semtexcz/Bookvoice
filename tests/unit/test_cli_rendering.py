"""Unit tests for CLI output and error rendering helpers."""

from __future__ import annotations

import pytest
import typer

from bookvoice.cli_rendering import exit_with_command_error
from bookvoice.errors import PipelineStageError


def test_exit_with_command_error_renders_stage_error_with_hint(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Renderer should print stage diagnostics and hint before exiting with code 1."""

    error = PipelineStageError(
        stage="extract",
        detail="Failed to extract text from PDF `broken.pdf`: Input PDF not found.",
        hint="Verify the input file exists and `pdftotext` is installed.",
    )

    with pytest.raises(typer.Exit) as exc_info:
        exit_with_command_error("build", error)

    captured = capsys.readouterr()
    assert exc_info.value.exit_code == 1
    assert "build failed at stage `extract`" in captured.err
    assert "Hint: Verify the input file exists and `pdftotext` is installed." in captured.err


def test_exit_with_command_error_renders_non_stage_fallback(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Renderer should print fallback exception text for non-stage failures."""

    error = RuntimeError("unexpected manifest error")

    with pytest.raises(typer.Exit) as exc_info:
        exit_with_command_error("resume", error)

    captured = capsys.readouterr()
    assert exc_info.value.exit_code == 1
    assert "resume failed: unexpected manifest error" in captured.err
