"""Domain exceptions for pipeline and CLI diagnostics."""

from __future__ import annotations


class PipelineStageError(RuntimeError):
    """Raised when a specific pipeline stage fails."""

    def __init__(
        self,
        *,
        stage: str,
        detail: str,
        hint: str | None = None,
    ) -> None:
        """Initialize a stage-scoped pipeline error."""

        super().__init__(detail)
        self.stage = stage
        self.detail = detail
        self.hint = hint
