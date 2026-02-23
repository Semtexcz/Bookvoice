"""Deterministic text cleaning rules.

Responsibilities:
- Provide composable cleanup rules for PDF-derived text artifacts.
- Keep preprocessing predictable for reproducibility.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Protocol


class CleanerRule(Protocol):
    """Protocol for text cleaning rules."""

    def apply(self, text: str) -> str:
        """Apply a single cleaning transformation."""


class RemovePageNumbers:
    """Remove isolated numeric page markers from text."""

    def apply(self, text: str) -> str:
        """Apply page-number cleanup rule."""

        return re.sub(r"(?m)^\s*\d+\s*$", "", text)


class RemoveHeadersFooters:
    """Remove repeated header/footer lines.

    Future implementation should infer repetitive patterns by frequency.
    """

    def apply(self, text: str) -> str:
        """Apply header/footer cleanup rule."""

        return text


class FixHyphenation:
    """Repair line-break hyphenation artifacts."""

    def apply(self, text: str) -> str:
        """Join words split with hyphen + newline."""

        return re.sub(r"(\w)-\n(\w)", r"\1\2", text)


class NormalizeQuotes:
    """Normalize mixed quote characters."""

    def apply(self, text: str) -> str:
        """Convert selected Unicode quotes to ASCII equivalents."""

        return text.replace("“", '"').replace("”", '"').replace("’", "'")


class CollapseWhitespace:
    """Normalize repeated whitespace to single spaces/newlines."""

    def apply(self, text: str) -> str:
        """Collapse consecutive spaces and strip line tails."""

        text = re.sub(r"[ \t]+", " ", text)
        return re.sub(r"[ \t]+\n", "\n", text)


class RemoveFigureRefs:
    """Remove inline figure reference placeholders.

    Future implementation should support locale-specific figure patterns.
    """

    def apply(self, text: str) -> str:
        """Apply figure-reference cleanup rule."""

        return re.sub(r"\[(?:fig(?:ure)?\.?\s*\d+)\]", "", text, flags=re.IGNORECASE)


class MergeDropCapInitials:
    """Merge decorative drop-cap initials split from their first word."""

    _SINGLE_UPPERCASE_RE = re.compile(r"^[A-Z]$")
    _NEXT_WORD_RE = re.compile(r"^(\s*)([A-Z]{3,})(.*)$")
    _HEADING_RE = re.compile(r"^[A-Z][A-Z\s'\"&\-]*$")
    _LIST_MARKER_RE = re.compile(r"^(?:\d+[.)]|[A-Za-z][.)]|[-*])$")

    def __init__(self) -> None:
        """Initialize rule state with deterministic merge counter."""

        self.last_merge_count = 0

    def apply(self, text: str) -> str:
        """Merge matching drop-cap patterns while tracking applied merge count."""

        merged_text, merge_count = self._merge_drop_caps(text)
        self.last_merge_count = merge_count
        return merged_text

    def _merge_drop_caps(self, text: str) -> tuple[str, int]:
        """Return text with merged drop-caps and the number of applied merges."""

        lines = text.split("\n")
        merged_lines: list[str] = []
        merge_count = 0
        index = 0

        while index < len(lines):
            current = lines[index]
            current_stripped = current.strip()
            if not self._SINGLE_UPPERCASE_RE.fullmatch(current_stripped):
                merged_lines.append(current)
                index += 1
                continue

            next_index, next_line = self._next_non_empty_line(lines, index + 1)
            if next_index is None or next_line is None:
                merged_lines.append(current)
                index += 1
                continue

            if next_index - index > 2:
                merged_lines.append(current)
                index += 1
                continue

            if self._is_heading_like(next_line) or self._is_likely_list_context(lines, index):
                merged_lines.append(current)
                index += 1
                continue

            next_match = self._NEXT_WORD_RE.match(next_line)
            if next_match is None:
                merged_lines.append(current)
                index += 1
                continue

            leading, first_word, tail = next_match.groups()
            merged_lines.append(f"{leading}{current_stripped}{first_word}{tail}")
            merge_count += 1
            index = next_index + 1

        return "\n".join(merged_lines), merge_count

    def _next_non_empty_line(self, lines: list[str], start: int) -> tuple[int | None, str | None]:
        """Return the next non-empty line index/value after `start`."""

        for index in range(start, len(lines)):
            if lines[index].strip():
                return index, lines[index]
        return None, None

    def _is_heading_like(self, line: str) -> bool:
        """Return whether a candidate next line looks like a short all-caps heading."""

        stripped = line.strip()
        if not stripped:
            return False
        words = [word for word in stripped.split() if any(char.isalpha() for char in word)]
        if not words or len(words) > 2:
            return False
        return bool(self._HEADING_RE.fullmatch(stripped))

    def _is_likely_list_context(self, lines: list[str], index: int) -> bool:
        """Return whether context indicates a list/section marker instead of drop-cap text."""

        previous = ""
        for backward in range(index - 1, -1, -1):
            if lines[backward].strip():
                previous = lines[backward].strip()
                break
        following = ""
        for forward in range(index + 1, len(lines)):
            if lines[forward].strip():
                following = lines[forward].strip()
                break

        if previous and self._LIST_MARKER_RE.fullmatch(previous):
            return True
        if following and re.match(r"^(?:\d+[.)]|[A-Za-z][.)]|[-*])\s+", following):
            return True
        return False


@dataclass(frozen=True, slots=True)
class TextCleaningReport:
    """Structured output of deterministic text cleanup and normalization."""

    cleaned_text: str
    drop_cap_merges_count: int


class TextCleaner:
    """Apply a sequence of deterministic cleaner rules."""

    def __init__(self, rules: list[CleanerRule] | None = None) -> None:
        """Initialize with custom rules or default rule sequence."""

        drop_cap_rule = MergeDropCapInitials()
        self.rules = rules or [
            RemovePageNumbers(),
            RemoveHeadersFooters(),
            FixHyphenation(),
            drop_cap_rule,
            NormalizeQuotes(),
            CollapseWhitespace(),
            RemoveFigureRefs(),
        ]
        self._drop_cap_rule = next(
            (rule for rule in self.rules if isinstance(rule, MergeDropCapInitials)),
            None,
        )

    def clean_with_report(self, text: str) -> TextCleaningReport:
        """Apply all configured rules and return cleaned text with diagnostics."""

        current = text
        for rule in self.rules:
            current = rule.apply(current)
        drop_cap_merges_count = (
            self._drop_cap_rule.last_merge_count
            if self._drop_cap_rule is not None
            else 0
        )
        return TextCleaningReport(
            cleaned_text=current,
            drop_cap_merges_count=drop_cap_merges_count,
        )

    def clean(self, text: str) -> str:
        """Apply all configured rules in order."""

        return self.clean_with_report(text).cleaned_text
