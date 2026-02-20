"""Deterministic text cleaning rules.

Responsibilities:
- Provide composable cleanup rules for PDF-derived text artifacts.
- Keep preprocessing predictable for reproducibility.
"""

from __future__ import annotations

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


class TextCleaner:
    """Apply a sequence of deterministic cleaner rules."""

    def __init__(self, rules: list[CleanerRule] | None = None) -> None:
        """Initialize with custom rules or default rule sequence."""

        self.rules = rules or [
            RemovePageNumbers(),
            RemoveHeadersFooters(),
            FixHyphenation(),
            NormalizeQuotes(),
            CollapseWhitespace(),
            RemoveFigureRefs(),
        ]

    def clean(self, text: str) -> str:
        """Apply all configured rules in order."""

        current = text
        for rule in self.rules:
            current = rule.apply(current)
        return current
