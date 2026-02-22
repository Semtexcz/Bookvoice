"""Shared parsing helpers for runtime and manifest value normalization."""

from __future__ import annotations


_TRUE_BOOLEAN_TOKENS = frozenset({"1", "true", "yes", "on"})
_FALSE_BOOLEAN_TOKENS = frozenset({"0", "false", "no", "off"})


def normalize_optional_string(value: object) -> str | None:
    """Normalize an optional value to a stripped non-empty string.

    Args:
        value: Arbitrary input value.

    Returns:
        Stripped string value, or `None` when the value is empty after trimming.
    """

    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text


def parse_permissive_boolean(value: object) -> bool | None:
    """Parse a permissive boolean token and return `None` for invalid values."""

    if isinstance(value, bool):
        return value

    normalized = normalize_optional_string(value)
    if normalized is None:
        return None

    token = normalized.lower()
    if token in _TRUE_BOOLEAN_TOKENS:
        return True
    if token in _FALSE_BOOLEAN_TOKENS:
        return False
    return None


def parse_required_boolean(value: str, field_name: str) -> bool:
    """Parse a required runtime boolean value from accepted textual tokens.

    Args:
        value: Text value to parse.
        field_name: Field name for an actionable validation error message.

    Raises:
        ValueError: If the token is not one of the accepted boolean values.
    """

    parsed = parse_permissive_boolean(value)
    if parsed is not None:
        return parsed

    raise ValueError(
        f"`{field_name}` must be a boolean value (`true`/`false`, `1`/`0`, `yes`/`no`)."
    )
