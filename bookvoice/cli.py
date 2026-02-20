"""Command-line interface for Bookvoice.

Responsibilities:
- Expose user-facing commands for pipeline operations.
- Convert CLI arguments into `BookvoiceConfig` and execute stubs.

Key public functions:
- `build_parser`: construct the argument parser.
- `main`: process CLI arguments and execute command handlers.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from .config import BookvoiceConfig
from .pipeline import BookvoicePipeline


def build_parser() -> argparse.ArgumentParser:
    """Build and return the top-level `argparse` parser."""

    parser = argparse.ArgumentParser(prog="bookvoice", description="Bookvoice CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_cmd = subparsers.add_parser("build", help="Run the full pipeline")
    build_cmd.add_argument("input_pdf", type=Path)
    build_cmd.add_argument("--out", type=Path, default=Path("out"))

    translate_cmd = subparsers.add_parser("translate-only", help="Run translation stages")
    translate_cmd.add_argument("input_pdf", type=Path)
    translate_cmd.add_argument("--out", type=Path, default=Path("out"))

    tts_cmd = subparsers.add_parser("tts-only", help="Run TTS stage from prior artifacts")
    tts_cmd.add_argument("manifest", type=Path)

    resume_cmd = subparsers.add_parser("resume", help="Resume run from manifest")
    resume_cmd.add_argument("manifest", type=Path)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entrypoint.

    Args:
        argv: Optional argv sequence for testing.

    Returns:
        Process exit code.
    """

    parser = build_parser()
    args = parser.parse_args(argv)

    pipeline = BookvoicePipeline()

    if args.command in {"build", "translate-only"}:
        config = BookvoiceConfig(input_pdf=args.input_pdf, output_dir=args.out)
        manifest = pipeline.run(config)
        print(f"[{args.command}] Would process: {config.input_pdf}")
        print(f"[{args.command}] Output dir: {config.output_dir}")
        print(f"[{args.command}] Stub run id: {manifest.run_id}")
        return 0

    if args.command == "tts-only":
        print(f"[tts-only] Would synthesize audio from manifest: {args.manifest}")
        return 0

    if args.command == "resume":
        print(f"[resume] Would resume pipeline using manifest: {args.manifest}")
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
