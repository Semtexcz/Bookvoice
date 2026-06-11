"""Public Python API for running Bookvoice from another application.

This module is intentionally independent of the Typer CLI so backend workers
and other Python callers can execute the audiobook pipeline without subprocess
wrappers or terminal-specific behavior.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from .config import BookvoiceConfig
from .models.datatypes import RunManifest
from .pipeline import BookvoicePipeline

ProgressCallback = Callable[[str, int, int], None]


def build_audiobook(
    config: BookvoiceConfig,
    progress_callback: ProgressCallback | None = None,
) -> RunManifest:
    """Run the full Bookvoice audiobook pipeline from Python code.

    The caller owns all non-interactive configuration, including source/output
    paths and provider credentials supplied via `BookvoiceConfig`, environment
    variables, or existing runtime configuration mechanisms.
    """

    pipeline = BookvoicePipeline(stage_progress_callback=progress_callback)
    return pipeline.run(config)


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


__all__ = ["ProgressCallback", "build_audiobook", "create_build_config"]
