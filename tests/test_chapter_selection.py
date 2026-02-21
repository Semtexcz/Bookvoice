"""Unit tests for chapter selection parser utilities."""

import pytest

from bookvoice.text.chapter_selection import (
    format_chapter_selection,
    parse_chapter_indices_csv,
    parse_chapter_selection,
)


def test_parse_chapter_selection_supports_single_list_and_range() -> None:
    """Parser should support single index, comma list, and closed range syntax."""

    available = [1, 2, 3, 4, 5]
    assert parse_chapter_selection("3", available) == [3]
    assert parse_chapter_selection("5,1,3", available) == [1, 3, 5]
    assert parse_chapter_selection("2-4", available) == [2, 3, 4]


def test_parse_chapter_selection_rejects_malformed_or_overlapping_ranges() -> None:
    """Parser should reject malformed and overlapping chapter selection expressions."""

    available = [1, 2, 3, 4, 5]
    with pytest.raises(ValueError, match="Malformed chapter range"):
        parse_chapter_selection("4-2", available)
    with pytest.raises(ValueError, match="Overlapping chapter selection"):
        parse_chapter_selection("1-3,3-4", available)


def test_parse_chapter_selection_rejects_out_of_bounds_indices() -> None:
    """Parser should reject out-of-bound chapter indices with clear diagnostics."""

    available = [1, 2, 3, 4, 5]
    with pytest.raises(ValueError, match="positive and 1-based"):
        parse_chapter_selection("0", available)
    with pytest.raises(ValueError, match="out of available bounds"):
        parse_chapter_selection("6", available)


def test_parse_chapter_indices_csv_and_format_selection() -> None:
    """CSV parser and formatter should preserve deterministic scope representation."""

    available = [1, 2, 3, 4, 5]
    assert parse_chapter_indices_csv("5,3,4", available) == [3, 4, 5]
    assert format_chapter_selection([1, 2, 3, 5]) == "1-3,5"
