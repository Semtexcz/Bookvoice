"""Command-line interface for Bookvoice.

Responsibilities:
- Expose user-facing commands for pipeline operations.
- Convert CLI arguments into `BookvoiceConfig` and execute stubs.

Key public functions:
- `app`: Typer application instance.
- `main`: invoke the Typer application.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, NoReturn

import typer

from .config import BookvoiceConfig
from .errors import PipelineStageError
from .pipeline import BookvoicePipeline

app = typer.Typer(
    name="bookvoice",
    no_args_is_help=True,
    help="Bookvoice CLI.",
)


def _exit_with_command_error(command_name: str, exc: Exception) -> NoReturn:
    """Print concise diagnostics for command failures and exit with code 1."""

    if isinstance(exc, PipelineStageError):
        typer.secho(
            f"{command_name} failed at stage `{exc.stage}`: {exc.detail}",
            fg=typer.colors.RED,
            err=True,
        )
        if exc.hint:
            typer.secho(f"Hint: {exc.hint}", fg=typer.colors.YELLOW, err=True)
    else:
        typer.secho(f"{command_name} failed: {exc}", fg=typer.colors.RED, err=True)
    raise typer.Exit(code=1) from exc


@app.command("build")
def build_command(
    input_pdf: Annotated[Path, typer.Argument(help="Path to source PDF.")],
    out: Annotated[Path, typer.Option("--out", help="Output directory.")] = Path("out"),
) -> None:
    """Run the full pipeline."""

    try:
        pipeline = BookvoicePipeline()
        config = BookvoiceConfig(input_pdf=input_pdf, output_dir=out)
        manifest = pipeline.run(config)
    except Exception as exc:
        _exit_with_command_error("build", exc)

    typer.echo(f"Run id: {manifest.run_id}")
    typer.echo(f"Merged audio: {manifest.merged_audio_path}")
    typer.echo(f"Manifest: {manifest.extra.get('manifest_path', '(not written)')}")


@app.command("translate-only")
def translate_only_command(
    input_pdf: Annotated[Path, typer.Argument(help="Path to source PDF.")],
    out: Annotated[Path, typer.Option("--out", help="Output directory.")] = Path("out"),
) -> None:
    """Run translation stages only (stub currently runs full pipeline)."""

    try:
        pipeline = BookvoicePipeline()
        config = BookvoiceConfig(input_pdf=input_pdf, output_dir=out)
        manifest = pipeline.run(config)
    except Exception as exc:
        _exit_with_command_error("translate-only", exc)

    typer.echo(f"[translate-only] Would process: {config.input_pdf}")
    typer.echo(f"[translate-only] Output dir: {config.output_dir}")
    typer.echo(f"[translate-only] Stub run id: {manifest.run_id}")


@app.command("tts-only")
def tts_only_command(
    manifest: Annotated[Path, typer.Argument(help="Path to run manifest JSON.")],
) -> None:
    """Run TTS stage from prior artifacts."""
    typer.echo(f"[tts-only] Would synthesize audio from manifest: {manifest}")


@app.command("resume")
def resume_command(
    manifest: Annotated[Path, typer.Argument(help="Path to run manifest JSON.")],
) -> None:
    """Resume pipeline from an existing manifest."""

    try:
        pipeline = BookvoicePipeline()
        resumed_manifest = pipeline.resume(manifest)
    except Exception as exc:
        _exit_with_command_error("resume", exc)

    typer.echo(f"Run id: {resumed_manifest.run_id}")
    typer.echo(
        f"Resumed from stage: {resumed_manifest.extra.get('resume_next_stage', 'unknown')}"
    )
    typer.echo(f"Merged audio: {resumed_manifest.merged_audio_path}")
    typer.echo(f"Manifest: {resumed_manifest.extra.get('manifest_path', '(not written)')}")


def main() -> None:
    """CLI entrypoint for console scripts."""
    app()


if __name__ == "__main__":
    main()
