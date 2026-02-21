"""Structured run logging utilities.

Responsibilities:
- Emit concise, deterministic phase-level runtime logs.
- Use `loguru` when available, with a safe stdout fallback otherwise.
"""

from __future__ import annotations

import sys
from typing import TextIO

try:
    from loguru import logger as _loguru_logger
except ImportError:
    _loguru_logger = None


def _sanitize_context_value(value: object) -> str:
    """Convert context values into stable, shell-safe tokens."""

    raw = str(value).strip()
    if not raw:
        return "none"
    return "".join(
        character if character.isalnum() or character in {"-", "_", ".", ":", "/"} else "_"
        for character in raw
    )


def _format_context(context: dict[str, object]) -> str:
    """Serialize context key/value pairs in deterministic key order."""

    if not context:
        return ""
    tokens = [
        f"{key}={_sanitize_context_value(context[key])}"
        for key in sorted(context.keys())
    ]
    return " " + " ".join(tokens)


class RunLogger:
    """Emit deterministic phase logs for CLI-observable pipeline activity."""

    def __init__(self, sink: TextIO | None = None) -> None:
        """Initialize logger sink and configure deterministic formatting."""

        self._sink = sink or sys.stdout
        if _loguru_logger is not None:
            _loguru_logger.remove()
            _loguru_logger.add(self._sink, format="{message}", level="INFO", colorize=False)

    def _emit(self, level: str, event: str, stage: str, **context: object) -> None:
        """Emit one structured runtime log line."""

        line = f"[phase] level={level} stage={stage} event={event}{_format_context(context)}"
        if _loguru_logger is not None:
            _loguru_logger.log(level, line)
            return
        print(line, file=self._sink)

    def log_stage_start(self, stage: str) -> None:
        """Emit a stage-start runtime event."""

        self._emit("INFO", "start", stage)

    def log_stage_complete(self, stage: str) -> None:
        """Emit a stage-complete runtime event."""

        self._emit("INFO", "complete", stage)

    def log_stage_failure(self, stage: str, error_type: str) -> None:
        """Emit a stage-failure runtime event without sensitive payload details."""

        self._emit("ERROR", "failure", stage, error_type=error_type)
