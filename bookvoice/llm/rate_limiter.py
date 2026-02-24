"""Rate limiting abstraction for provider calls.

Responsibilities:
- Provide a single hook to enforce provider request pacing.
- Keep retry/rate-limit policy independent from provider adapters.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from time import monotonic, sleep
from typing import Callable


@dataclass(slots=True)
class RateLimiter:
    """Simple per-key minimum-interval limiter used around provider requests."""

    min_interval_seconds: float = 0.05
    clock: Callable[[], float] = monotonic
    sleeper: Callable[[float], None] = sleep
    _next_allowed_at: dict[str, float] = field(default_factory=dict)

    def acquire(self, key: str) -> None:
        """Block until request key is allowed under deterministic interval policy."""

        if self.min_interval_seconds <= 0.0:
            return
        now = self.clock()
        next_allowed = self._next_allowed_at.get(key, 0.0)
        wait_seconds = next_allowed - now
        if wait_seconds > 0.0:
            self.sleeper(wait_seconds)
            now = self.clock()
        self._next_allowed_at[key] = now + self.min_interval_seconds
