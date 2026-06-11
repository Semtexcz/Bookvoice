"""Public Python API for running Bookvoice from another application.

This module is intentionally independent of the Typer CLI so backend workers
and other Python callers can execute the audiobook pipeline without subprocess
wrappers or terminal-specific behavior.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from .config import BookvoiceConfig
from .models.datatypes import Chapter, RunManifest
from .pipeline import BookvoicePipeline

ProgressCallback = Callable[[str, int, int], None]
ChapterList = tuple[list[Chapter], str, str]


def _pipeline(progress_callback: ProgressCallback | None = None) -> BookvoicePipeline:
    """Create a pipeline instance for non-interactive library API calls."""

    return BookvoicePipeline(stage_progress_callback=progress_callback)


def build_audiobook(
    config: BookvoiceConfig,
    progress_callback: ProgressCallback | None = None,
) -> RunManifest:
    """Run the full Bookvoice audiobook pipeline from Python code.

    The caller owns all non-interactive configuration, including source/output
    paths and provider credentials supplied via `BookvoiceConfig`, environment
    variables, or existing runtime configuration mechanisms.
    """

    return _pipeline(progress_callback).run(config)


def run_chapters_only(
    config: BookvoiceConfig,
    progress_callback: ProgressCallback | None = None,
) -> RunManifest:
    """Run chapter extraction and boundary detection from Python code."""

    return _pipeline(progress_callback).run_chapters_only(config)


def run_translate_only(
    config: BookvoiceConfig,
    progress_callback: ProgressCallback | None = None,
) -> RunManifest:
    """Run the pipeline through translation artifacts without audio generation."""

    return _pipeline(progress_callback).run_translate_only(config)


def run_tts_only(
    manifest_path: Path,
    progress_callback: ProgressCallback | None = None,
) -> RunManifest:
    """Replay TTS, merge, package, and manifest stages from an existing manifest."""

    return _pipeline(progress_callback).run_tts_only_from_manifest(manifest_path)


def resume_audiobook(
    manifest_path: Path,
    progress_callback: ProgressCallback | None = None,
) -> RunManifest:
    """Resume an interrupted Bookvoice run from an existing manifest."""

    return _pipeline(progress_callback).resume(manifest_path)


def list_chapters(config: BookvoiceConfig) -> ChapterList:
    """Return detected source chapters without writing pipeline artifacts."""

    return _pipeline().list_chapters_from_source(config)


def list_chapters_from_artifact(chapters_artifact: Path) -> ChapterList:
    """Return chapters and source metadata from a persisted chapters artifact."""

    return _pipeline().list_chapters_from_artifact(chapters_artifact)


def create_build_config(
    input_path: Path,
    output_dir: Path,
    language: str = "cs",
    chapter_selection: str | None = None,
    rewrite_bypass: bool = False,
    max_provider_workers: int = 1,
    extra: dict[str, str] | None = None,
) -> BookvoiceConfig:
    """Create a config for programmatic full-pipeline execution."""

    return BookvoiceConfig(
        input_pdf=input_path,
        output_dir=output_dir,
        language=language,
        chapter_selection=chapter_selection,
        rewrite_bypass=rewrite_bypass,
        max_provider_workers=max_provider_workers,
        extra=dict(extra or {}),
    )


__all__ = [
    "ChapterList",
    "ProgressCallback",
    "build_audiobook",
    "create_build_config",
    "list_chapters",
    "list_chapters_from_artifact",
    "resume_audiobook",
    "run_chapters_only",
    "run_translate_only",
    "run_tts_only",
]
