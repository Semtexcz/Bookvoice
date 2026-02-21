"""Chapter selection parsing utilities for CLI and pipeline flows.

Responsibilities:
- Parse 1-based chapter selection expressions (`1`, `1,3`, `2-5`, mixed).
- Validate indices against available chapter indices.
- Produce deterministic normalized selection labels.
"""

from __future__ import annotations

from typing import Iterable, Sequence


def parse_chapter_selection(
    selection: str | None, available_indices: Sequence[int]
) -> list[int]:
    """Parse chapter selection expression into sorted unique indices.

    Args:
        selection: User selection string. `None` or blank selects all chapters.
        available_indices: Existing 1-based chapter indices that can be selected.

    Returns:
        Sorted selected chapter indices.

    Raises:
        ValueError: If the selection syntax or bounds are invalid.
    """

    normalized_available = sorted(set(int(index) for index in available_indices))
    if not normalized_available:
        raise ValueError("No chapters are available for selection.")

    if selection is None or not selection.strip():
        return normalized_available

    tokens = [part.strip() for part in selection.split(",")]
    if any(not token for token in tokens):
        raise ValueError(
            "Malformed chapter selection: empty item in list. "
            "Use syntax like `1`, `1,3`, `2-4`, or `1,3-5`."
        )

    selected: list[int] = []
    seen: set[int] = set()
    available_set = set(normalized_available)

    for token in tokens:
        expanded = _expand_token(token, available_set, normalized_available)
        for index in expanded:
            if index in seen:
                raise ValueError(
                    f"Overlapping chapter selection contains duplicate index `{index}`."
                )
            seen.add(index)
            selected.append(index)

    return sorted(selected)


def parse_chapter_indices_csv(
    indices_csv: str | None, available_indices: Sequence[int]
) -> list[int]:
    """Parse stored CSV chapter indices and validate bounds.

    Args:
        indices_csv: Comma-separated positive chapter indices.
        available_indices: Existing 1-based chapter indices that can be selected.

    Returns:
        Sorted selected chapter indices.

    Raises:
        ValueError: If CSV content is malformed or out of bounds.
    """

    normalized_available = sorted(set(int(index) for index in available_indices))
    if not normalized_available:
        raise ValueError("No chapters are available for selection.")
    if indices_csv is None or not indices_csv.strip():
        return normalized_available

    tokens = [part.strip() for part in indices_csv.split(",")]
    if any(not token for token in tokens):
        raise ValueError("Stored chapter index list is malformed.")

    selected: list[int] = []
    seen: set[int] = set()
    available_set = set(normalized_available)
    for token in tokens:
        index = _parse_positive_index(token)
        if index not in available_set:
            raise ValueError(
                f"Stored chapter index `{index}` is out of available bounds "
                f"`{normalized_available[0]}-{normalized_available[-1]}`."
            )
        if index in seen:
            raise ValueError(f"Stored chapter index list contains duplicate `{index}`.")
        seen.add(index)
        selected.append(index)
    return sorted(selected)


def format_chapter_selection(indices: Iterable[int]) -> str:
    """Format selected chapter indices into normalized compact range syntax."""

    ordered = sorted(set(int(index) for index in indices))
    if not ordered:
        return ""

    parts: list[str] = []
    start = ordered[0]
    end = ordered[0]

    for index in ordered[1:]:
        if index == end + 1:
            end = index
            continue
        parts.append(str(start) if start == end else f"{start}-{end}")
        start = index
        end = index
    parts.append(str(start) if start == end else f"{start}-{end}")
    return ",".join(parts)


def _expand_token(
    token: str, available_set: set[int], normalized_available: list[int]
) -> list[int]:
    """Expand one token (`N` or `N-M`) to concrete chapter indices."""

    if "-" not in token:
        index = _parse_positive_index(token)
        _validate_available_index(index, available_set, normalized_available)
        return [index]

    if token.count("-") != 1:
        raise ValueError(
            f"Malformed chapter range `{token}`. Use closed range syntax like `2-4`."
        )

    start_text, end_text = token.split("-", maxsplit=1)
    if not start_text or not end_text:
        raise ValueError(
            f"Malformed chapter range `{token}`. Use closed range syntax like `2-4`."
        )

    start = _parse_positive_index(start_text)
    end = _parse_positive_index(end_text)
    if start > end:
        raise ValueError(
            f"Malformed chapter range `{token}`: range start must be less than or equal to end."
        )

    expanded = list(range(start, end + 1))
    for index in expanded:
        _validate_available_index(index, available_set, normalized_available)
    return expanded


def _parse_positive_index(token: str) -> int:
    """Parse one 1-based positive chapter index token."""

    try:
        value = int(token, 10)
    except ValueError as exc:
        raise ValueError(f"Invalid chapter index `{token}`. Indices must be integers.") from exc
    if value < 1:
        raise ValueError(
            f"Invalid chapter index `{token}`. Indices must be positive and 1-based."
        )
    return value


def _validate_available_index(
    index: int, available_set: set[int], normalized_available: Sequence[int]
) -> None:
    """Validate one chapter index against available chapter bounds."""

    if index in available_set:
        return
    raise ValueError(
        f"Chapter index `{index}` is out of available bounds "
        f"`{normalized_available[0]}-{normalized_available[-1]}`."
    )
