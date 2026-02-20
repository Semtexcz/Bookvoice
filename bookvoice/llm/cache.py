"""Response cache abstraction for LLM calls.

Responsibilities:
- Define get/set interface for content-addressed response reuse.
- Support deterministic replay of expensive stage outputs.
"""

from __future__ import annotations


class ResponseCache:
    """Placeholder cache for model responses."""

    def get(self, cache_key: str) -> str | None:
        """Return cached response for key if present."""

        _ = cache_key
        return None

    def set(self, cache_key: str, value: str) -> None:
        """Store a response payload under a cache key."""

        _ = (cache_key, value)
        return None
