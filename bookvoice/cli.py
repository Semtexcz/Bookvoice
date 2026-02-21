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
from .models.datatypes import Chapter, RunManifest
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


def _echo_cost_summary(manifest: RunManifest) -> None:
    """Print run-level cost summary in USD."""

    typer.echo(f"Cost LLM (USD): {manifest.total_llm_cost_usd:.6f}")
    typer.echo(f"Cost TTS (USD): {manifest.total_tts_cost_usd:.6f}")
    typer.echo(f"Cost Total (USD): {manifest.total_cost_usd:.6f}")


def _echo_chapter_summary(manifest: RunManifest) -> None:
    """Print chapter extraction source and fallback reason when available."""

    source = manifest.extra.get("chapter_source", "unknown")
    fallback_reason = manifest.extra.get("chapter_fallback_reason", "")
    typer.echo(f"Chapter source: {source}")
    if fallback_reason:
        typer.echo(f"Chapter fallback reason: {fallback_reason}")
    selection_label = manifest.extra.get("chapter_scope_label", "all")
    selection_mode = manifest.extra.get("chapter_scope_mode", "all")
    typer.echo(f"Chapter scope: {selection_mode} ({selection_label})")


def _echo_chapter_list(chapters: list[Chapter]) -> None:
    """Print compact deterministic chapter index/title rows."""

    sorted_rows = sorted(
        ((chapter.index, chapter.title) for chapter in chapters),
        key=lambda item: item[0],
    )
    for index, title in sorted_rows:
        typer.echo(f"{index}. {title}")


@app.command("build")
def build_command(
    input_pdf: Annotated[Path, typer.Argument(help="Path to source PDF.")],
    out: Annotated[Path, typer.Option("--out", help="Output directory.")] = Path("out"),
    chapters: Annotated[
        str | None,
        typer.Option(
            "--chapters",
            help=(
                "1-based chapter selection: `5`, `1,3,7`, `2-4`, or mixed `1,3-5`."
            ),
        ),
    ] = None,
) -> None:
    """Run the full pipeline."""

    try:
        pipeline = BookvoicePipeline()
        config = BookvoiceConfig(
            input_pdf=input_pdf,
            output_dir=out,
            chapter_selection=chapters,
        )
        manifest = pipeline.run(config)
    except Exception as exc:
        _exit_with_command_error("build", exc)

    typer.echo(f"Run id: {manifest.run_id}")
    typer.echo(f"Merged audio: {manifest.merged_audio_path}")
    typer.echo(f"Manifest: {manifest.extra.get('manifest_path', '(not written)')}")
    _echo_chapter_summary(manifest)
    _echo_cost_summary(manifest)


@app.command("chapters-only")
def chapters_only_command(
    input_pdf: Annotated[Path, typer.Argument(help="Path to source PDF.")],
    out: Annotated[Path, typer.Option("--out", help="Output directory.")] = Path("out"),
    chapters: Annotated[
        str | None,
        typer.Option(
            "--chapters",
            help=(
                "1-based chapter selection: `5`, `1,3,7`, `2-4`, or mixed `1,3-5`."
            ),
        ),
    ] = None,
) -> None:
    """Run only extract, clean, and chapter split stages."""

    try:
        pipeline = BookvoicePipeline()
        config = BookvoiceConfig(
            input_pdf=input_pdf,
            output_dir=out,
            chapter_selection=chapters,
        )
        manifest = pipeline.run_chapters_only(config)
    except Exception as exc:
        _exit_with_command_error("chapters-only", exc)

    typer.echo(f"Run id: {manifest.run_id}")
    typer.echo(f"Chapters artifact: {manifest.extra.get('chapters', '(not written)')}")
    typer.echo(f"Manifest: {manifest.extra.get('manifest_path', '(not written)')}")
    _echo_chapter_summary(manifest)


@app.command("list-chapters")
def list_chapters_command(
    input_pdf: Annotated[Path | None, typer.Argument(help="Path to source PDF.")] = None,
    chapters_artifact: Annotated[
        Path | None,
        typer.Option(
            "--chapters-artifact",
            help="Path to `text/chapters.json` chapter artifact.",
        ),
    ] = None,
    out: Annotated[
        Path,
        typer.Option("--out", help="Output directory used for extract/clean/split flow."),
    ] = Path("out"),
) -> None:
    """List extracted chapter indices and titles for a PDF or chapters artifact."""

    if (input_pdf is None and chapters_artifact is None) or (
        input_pdf is not None and chapters_artifact is not None
    ):
        _exit_with_command_error(
            "list-chapters",
            PipelineStageError(
                stage="list-chapters-input",
                detail=(
                    "Provide exactly one input source: `<input.pdf>` or "
                    "`--chapters-artifact <path>`."
                ),
                hint="Use `bookvoice list-chapters --help` for usage examples.",
            ),
        )
    try:
        pipeline = BookvoicePipeline()
        if chapters_artifact is not None:
            chapters, source, fallback_reason = pipeline.list_chapters_from_artifact(
                chapters_artifact
            )
        else:
            if input_pdf is None:
                raise PipelineStageError(
                    stage="list-chapters-input",
                    detail="Input PDF path is required when artifact path is not provided.",
                    hint="Provide `<input.pdf>` or use `--chapters-artifact <path>`.",
                )
            config = BookvoiceConfig(input_pdf=input_pdf, output_dir=out)
            chapters, source, fallback_reason = pipeline.list_chapters_from_pdf(config)
    except Exception as exc:
        _exit_with_command_error("list-chapters", exc)

    typer.echo(f"Chapter source: {source or 'unknown'}")
    if fallback_reason:
        typer.echo(f"Chapter fallback reason: {fallback_reason}")
    _echo_chapter_list(chapters)


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
    _echo_chapter_summary(resumed_manifest)
    _echo_cost_summary(resumed_manifest)


def main() -> None:
    """CLI entrypoint for console scripts."""
    app()


if __name__ == "__main__":
    main()
