"""Rate limiting abstraction for provider calls.

Responsibilities:
- Provide a single hook to enforce provider request pacing.
- Keep retry/rate-limit policy independent from provider adapters.
"""

from __future__ import annotations


class RateLimiter:
    """Placeholder rate limiter for external API calls."""

    def acquire(self, key: str) -> None:
        """Acquire permission for a request key.

        Future implementation may block/sleep or raise on quota limits.
        """

        _ = key
        return None
