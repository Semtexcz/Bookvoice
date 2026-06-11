"""Structured run logging utilities.

Responsibilities:
- Emit concise, deterministic phase-level runtime logs.
- Use `loguru` when available, with a safe stdout fallback otherwise.
"""

from __future__ import annotations

import sys
import time
from collections.abc import Callable
from typing import Any, TextIO

_loguru_logger: Any | None
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

    def __init__(
        self,
        sink: TextIO | None = None,
        clock: Callable[[], float] | None = None,
    ) -> None:
        """Initialize logger sink and configure deterministic formatting."""

        self._sink = sink or sys.stdout
        self._clock = clock or time.monotonic
        self._run_started_at = self._clock()
        self._stage_started_at: dict[str, float] = {}
        if _loguru_logger is not None:
            _loguru_logger.remove()
            _loguru_logger.add(self._sink, format="{message}", level="INFO", colorize=False)

    @staticmethod
    def _format_seconds(seconds: float) -> str:
        """Format elapsed seconds as a compact deterministic token."""

        return f"{max(0.0, seconds):.3f}s"

    def _emit(self, level: str, event: str, stage: str, **context: object) -> None:
        """Emit one structured runtime log line."""

        elapsed_seconds = self._clock() - self._run_started_at
        timed_context = {"elapsed": self._format_seconds(elapsed_seconds), **context}
        line = (
            f"[phase] level={level} stage={stage} event={event}"
            f"{_format_context(timed_context)}"
        )
        if _loguru_logger is not None:
            _loguru_logger.log(level, line)
            return
        print(line, file=self._sink)

    def log_stage_start(self, stage: str) -> None:
        """Emit a stage-start runtime event."""

        self._stage_started_at[stage] = self._clock()
        self._emit("INFO", "start", stage)

    def log_stage_complete(self, stage: str) -> None:
        """Emit a stage-complete runtime event."""

        completed_at = self._clock()
        started_at = self._stage_started_at.pop(stage, completed_at)
        duration_seconds = completed_at - started_at
        self._emit(
            "INFO",
            "complete",
            stage,
            duration=self._format_seconds(duration_seconds),
        )

    def log_stage_failure(self, stage: str, error_type: str) -> None:
        """Emit a stage-failure runtime event without sensitive payload details."""

        failed_at = self._clock()
        started_at = self._stage_started_at.pop(stage, failed_at)
        duration_seconds = failed_at - started_at
        self._emit(
            "ERROR",
            "failure",
            stage,
            duration=self._format_seconds(duration_seconds),
            error_type=error_type,
        )

    def log_provider_activity(self, stage: str, item_index: int, item_total: int) -> None:
        """Emit a secret-safe activity pulse for a long provider-backed item."""

        self._emit(
            "INFO",
            "activity",
            stage,
            item=f"{item_index}/{item_total}",
        )
