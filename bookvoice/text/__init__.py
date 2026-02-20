"""Text preprocessing and segmentation components.

This package provides deterministic cleanup, normalization, and chunking
building blocks used before LLM and TTS stages.
"""

from .chunking import Chunker
from .cleaners import (
    CollapseWhitespace,
    FixHyphenation,
    NormalizeQuotes,
    RemoveFigureRefs,
    RemoveHeadersFooters,
    RemovePageNumbers,
    TextCleaner,
)
from .normalizer import TextNormalizer

__all__ = [
    "TextCleaner",
    "TextNormalizer",
    "Chunker",
    "RemovePageNumbers",
    "RemoveHeadersFooters",
    "FixHyphenation",
    "NormalizeQuotes",
    "CollapseWhitespace",
    "RemoveFigureRefs",
]
