"""Integration tests for CLI root version option behavior."""

from typer.testing import CliRunner

from bookvoice import __version__
from bookvoice.cli import app


def test_cli_version_option_prints_version_and_exits() -> None:
    """CLI `--version` should print the current package version and exit with code 0."""

    runner = CliRunner()
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert result.output.strip() == f"bookvoice {__version__}"


def test_cli_version_option_with_command_name_still_exits_early() -> None:
    """Eager `--version` should exit before command execution when passed before commands."""

    runner = CliRunner()
    result = runner.invoke(app, ["--version", "build"])

    assert result.exit_code == 0
    assert result.output.strip() == f"bookvoice {__version__}"
