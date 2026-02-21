"""Deterministic slug helpers for filesystem-safe audio identifiers.

Responsibilities:
- Normalize free-form titles into stable ASCII slugs.
- Keep slug behavior locale-independent for reproducible filenames.
"""

from __future__ import annotations

import re
import unicodedata


def slugify_audio_title(value: str) -> str:
    """Return a deterministic filesystem-safe ASCII slug for audio title segments."""

    normalized = unicodedata.normalize("NFKD", value)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    lowered = ascii_only.lower().strip()
    collapsed = re.sub(r"[^a-z0-9]+", "-", lowered)
    slug = collapsed.strip("-")
    return slug or "part"
