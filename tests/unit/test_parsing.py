"""Unit tests for shared runtime and manifest parsing helpers."""

import pytest

from bookvoice.parsing import (
    normalize_optional_string,
    parse_permissive_boolean,
    parse_required_boolean,
)


def test_normalize_optional_string_handles_blank_values() -> None:
    """Normalization should return `None` for `None` and blank textual values."""

    assert normalize_optional_string(None) is None
    assert normalize_optional_string("") is None
    assert normalize_optional_string("   ") is None


def test_normalize_optional_string_strips_non_blank_values() -> None:
    """Normalization should return stripped content for non-empty values."""

    assert normalize_optional_string("  value  ") == "value"
    assert normalize_optional_string(42) == "42"


@pytest.mark.parametrize(
    ("token", "expected"),
    [
        ("TrUe", True),
        ("  ON ", True),
        ("YeS", True),
        ("FALSE", False),
        (" oFf ", False),
        ("nO", False),
    ],
)
def test_parse_permissive_boolean_accepts_mixed_case_tokens(
    token: str, expected: bool
) -> None:
    """Permissive parsing should accept valid tokens case-insensitively."""

    assert parse_permissive_boolean(token) is expected


@pytest.mark.parametrize("value", ["", "   ", "maybe", "2", object()])
def test_parse_permissive_boolean_returns_none_for_invalid_tokens(value: object) -> None:
    """Permissive parsing should return `None` for invalid or blank inputs."""

    assert parse_permissive_boolean(value) is None


def test_parse_required_boolean_raises_for_invalid_token() -> None:
    """Strict boolean parsing should keep the existing validation message."""

    with pytest.raises(
        ValueError,
        match=(
            r"`rewrite_bypass` must be a boolean value "
            r"\(`true`/`false`, `1`/`0`, `yes`/`no`\)\."
        ),
    ):
        parse_required_boolean("maybe", "rewrite_bypass")
