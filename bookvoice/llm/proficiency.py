"""CEFR proficiency-level normalization for LLM output control.

Responsibilities:
- Define the CEFR labels that translation and audio rewriting accept.
- Normalize caller input case-insensitively and reject unsupported values.
"""

from __future__ import annotations

SUPPORTED_PROFICIENCY_LEVELS: tuple[str, ...] = (
    "A0",
    "A1",
    "A2",
    "B1",
    "B2",
    "C1",
    "C2",
)

_SUPPORTED_LEVELS = frozenset(SUPPORTED_PROFICIENCY_LEVELS)


def normalize_proficiency_level(proficiency_level: str | None) -> str | None:
    """Return the normalized CEFR label, or ``None`` when no level was supplied.

    Normalization ignores letter case and surrounding whitespace. Unsupported values
    raise ``ValueError`` with every accepted label in the message.
    """

    if proficiency_level is None:
        return None

    normalized = proficiency_level.strip().upper()
    if normalized not in _SUPPORTED_LEVELS:
        supported = ", ".join(SUPPORTED_PROFICIENCY_LEVELS)
        raise ValueError(
            f"Unsupported proficiency level {proficiency_level!r}; expected one of: "
            f"{supported}."
        )
    return normalized
