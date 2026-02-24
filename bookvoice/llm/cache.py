"""Deterministic response cache for provider-backed text operations.

Responsibilities:
- Build stable cache keys from provider/model/operation and normalized identity input.
- Reuse cached responses for repeated deterministic prompts within one run.
- Track basic cache telemetry (hits/misses) for manifest diagnostics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
import json
from typing import Any


def _normalize_identity_value(value: Any) -> Any:
    """Normalize identity payload values for stable cache key hashing."""

    if isinstance(value, str):
        return " ".join(value.split())
    if isinstance(value, list | tuple):
        return [_normalize_identity_value(item) for item in value]
    if isinstance(value, dict):
        return {
            str(key): _normalize_identity_value(value[key])
            for key in sorted(value.keys(), key=str)
        }
    return value


@dataclass(slots=True)
class ResponseCache:
    """In-memory deterministic cache keyed by provider/model/operation/input identity."""

    entries: dict[str, str] = field(default_factory=dict)
    hits: int = 0
    misses: int = 0

    @staticmethod
    def make_key(
        *,
        provider: str,
        model: str,
        operation: str,
        input_identity: Any,
    ) -> str:
        """Build deterministic cache key with normalized identity hash suffix."""

        normalized_identity = _normalize_identity_value(input_identity)
        canonical_identity = json.dumps(
            normalized_identity,
            sort_keys=True,
            ensure_ascii=True,
            separators=(",", ":"),
        )
        identity_hash = sha256(canonical_identity.encode("utf-8")).hexdigest()
        normalized_provider = provider.strip().lower()
        normalized_model = model.strip()
        normalized_operation = operation.strip().lower()
        return (
            f"response:{normalized_provider}:{normalized_model}:"
            f"{normalized_operation}:{identity_hash}"
        )

    def get(self, cache_key: str) -> str | None:
        """Return cached response for key and update hit/miss telemetry counters."""

        if cache_key in self.entries:
            self.hits += 1
            return self.entries[cache_key]
        self.misses += 1
        return None

    def set(self, cache_key: str, value: str) -> None:
        """Store a response payload under a cache key."""

        self.entries[cache_key] = value

    def hit_rate(self) -> float:
        """Return cache hit rate for current cache lifecycle."""

        total = self.hits + self.misses
        if total == 0:
            return 0.0
        return self.hits / float(total)
