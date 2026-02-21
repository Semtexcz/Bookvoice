"""Stage telemetry helper methods for Bookvoice pipeline.

Responsibilities:
- Provide stage index/total metadata for progress reporting.
- Emit stage start/complete/failure events.
- Wrap stage actions with consistent telemetry hooks.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

_StageResult = TypeVar("_StageResult")


class PipelineTelemetryMixin:
    """Provide stage-telemetry helper methods."""

    _PHASE_SEQUENCE = (
        "extract",
        "clean",
        "split",
        "chunk",
        "translate",
        "rewrite",
        "tts",
        "merge",
        "manifest",
    )

    def _stage_position(self, stage_name: str) -> tuple[int, int] | None:
        """Return 1-based stage index and total stage count for known stages."""

        try:
            index = self._PHASE_SEQUENCE.index(stage_name) + 1
        except ValueError:
            return None
        return index, len(self._PHASE_SEQUENCE)

    def _on_stage_start(self, stage_name: str) -> None:
        """Emit start events to stage progress callback and structured logger."""

        stage_position = self._stage_position(stage_name)
        if stage_position and self._stage_progress_callback is not None:
            self._stage_progress_callback(stage_name, stage_position[0], stage_position[1])
        if self._run_logger is not None:
            self._run_logger.log_stage_start(stage_name)

    def _on_stage_complete(self, stage_name: str) -> None:
        """Emit stage-complete event to the structured logger."""

        if self._run_logger is not None:
            self._run_logger.log_stage_complete(stage_name)

    def _on_stage_failure(self, stage_name: str, exc: Exception) -> None:
        """Emit stage-failure event with sanitized exception metadata."""

        if self._run_logger is not None:
            self._run_logger.log_stage_failure(stage_name, type(exc).__name__)

    def _run_stage(
        self,
        stage_name: str,
        action: Callable[[], _StageResult],
    ) -> _StageResult:
        """Run one named stage and emit start/complete/failure telemetry events."""

        self._on_stage_start(stage_name)
        try:
            result = action()
        except Exception as exc:
            self._on_stage_failure(stage_name, exc)
            raise
        self._on_stage_complete(stage_name)
        return result
