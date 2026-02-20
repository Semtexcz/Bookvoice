"""Run logging scaffold.

Responsibilities:
- Provide structured event/error logging APIs for pipeline stages.
- Decouple logging sink implementation from orchestration logic.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Mapping


class RunLogger:
    """Placeholder logger for run events and errors."""

    def log_event(self, name: str, payload: Mapping[str, object] | None = None) -> None:
        """Record a structured informational event."""

        timestamp = datetime.now(timezone.utc).isoformat()
        print(f"{timestamp} [EVENT] {name} payload={dict(payload or {})}")

    def log_error(self, name: str, message: str, payload: Mapping[str, object] | None = None) -> None:
        """Record a structured error event."""

        timestamp = datetime.now(timezone.utc).isoformat()
        print(f"{timestamp} [ERROR] {name} message={message} payload={dict(payload or {})}")
