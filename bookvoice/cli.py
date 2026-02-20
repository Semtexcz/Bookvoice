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
from typing import Annotated

import typer

from .config import BookvoiceConfig
from .pipeline import BookvoicePipeline

app = typer.Typer(
    name="bookvoice",
    no_args_is_help=True,
    help="Bookvoice CLI.",
)

@app.command("build")
def build_command(
    input_pdf: Annotated[Path, typer.Argument(help="Path to source PDF.")],
    out: Annotated[Path, typer.Option("--out", help="Output directory.")] = Path("out"),
) -> None:
    """Run the full pipeline."""
    pipeline = BookvoicePipeline()
    config = BookvoiceConfig(input_pdf=input_pdf, output_dir=out)
    manifest = pipeline.run(config)
    typer.echo(f"[build] Would process: {config.input_pdf}")
    typer.echo(f"[build] Output dir: {config.output_dir}")
    typer.echo(f"[build] Stub run id: {manifest.run_id}")


@app.command("translate-only")
def translate_only_command(
    input_pdf: Annotated[Path, typer.Argument(help="Path to source PDF.")],
    out: Annotated[Path, typer.Option("--out", help="Output directory.")] = Path("out"),
) -> None:
    """Run translation stages only (stub currently runs full pipeline)."""
    pipeline = BookvoicePipeline()
    config = BookvoiceConfig(input_pdf=input_pdf, output_dir=out)
    manifest = pipeline.run(config)
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
    typer.echo(f"[resume] Would resume pipeline using manifest: {manifest}")


def main() -> None:
    """CLI entrypoint for console scripts."""
    app()


if __name__ == "__main__":
    main()
