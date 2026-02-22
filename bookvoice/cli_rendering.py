"""CLI output and error rendering helpers.

This module centralizes user-facing CLI presentation for command diagnostics,
chapter summaries, chapter listing rows, and run cost summaries.
"""

from __future__ import annotations

from typing import NoReturn

import typer

from .errors import PipelineStageError
from .models.datatypes import Chapter, RunManifest


def exit_with_command_error(command_name: str, exc: Exception) -> NoReturn:
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


def echo_cost_summary(manifest: RunManifest) -> None:
    """Print run-level cost summary in USD."""

    typer.echo(f"Cost LLM (USD): {manifest.total_llm_cost_usd:.6f}")
    typer.echo(f"Cost TTS (USD): {manifest.total_tts_cost_usd:.6f}")
    typer.echo(f"Cost Total (USD): {manifest.total_cost_usd:.6f}")


def echo_chapter_summary(manifest: RunManifest) -> None:
    """Print chapter extraction metadata and selected chapter scope."""

    source = manifest.extra.get("chapter_source", "unknown")
    fallback_reason = manifest.extra.get("chapter_fallback_reason", "")
    typer.echo(f"Chapter source: {source}")
    if fallback_reason:
        typer.echo(f"Chapter fallback reason: {fallback_reason}")
    selection_label = manifest.extra.get("chapter_scope_label", "all")
    selection_mode = manifest.extra.get("chapter_scope_mode", "all")
    typer.echo(f"Chapter scope: {selection_mode} ({selection_label})")


def echo_chapter_source(source: str | None, fallback_reason: str) -> None:
    """Print chapter extraction source and optional fallback reason."""

    typer.echo(f"Chapter source: {source or 'unknown'}")
    if fallback_reason:
        typer.echo(f"Chapter fallback reason: {fallback_reason}")


def echo_chapter_list(chapters: list[Chapter]) -> None:
    """Print compact deterministic chapter index/title rows."""

    sorted_rows = sorted(
        ((chapter.index, chapter.title) for chapter in chapters),
        key=lambda item: item[0],
    )
    for index, title in sorted_rows:
        typer.echo(f"{index}. {title}")
