"""Core datatypes shared across Bookvoice modules.

Responsibilities:
- Represent immutable records exchanged between pipeline stages.
- Provide explicit typing for reproducibility and serialization.

Key types:
- `BookMeta`, `Chapter`, `Chunk`, `TranslationResult`, `RewriteResult`,
  `AudioPart`, and `RunManifest`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping


@dataclass(frozen=True, slots=True)
class BookMeta:
    """Metadata describing the source book.

    Attributes:
        source_pdf: Path to input PDF.
        title: Human-readable title.
        author: Optional author name.
        language: Primary source language code.
    """

    source_pdf: Path
    title: str
    author: str | None
    language: str


@dataclass(frozen=True, slots=True)
class Chapter:
    """A chapter extracted from source text.

    Attributes:
        index: 1-based chapter index.
        title: Chapter title or inferred label.
        text: Full chapter text.
    """

    index: int
    title: str
    text: str


@dataclass(frozen=True, slots=True)
class Chunk:
    """A bounded text segment derived from a chapter.

    Attributes:
        chapter_index: 1-based chapter index.
        chunk_index: 0-based chunk index within chapter.
        text: Chunk text content.
        char_start: Inclusive character offset in chapter.
        char_end: Exclusive character offset in chapter.
    """

    chapter_index: int
    chunk_index: int
    text: str
    char_start: int
    char_end: int


@dataclass(frozen=True, slots=True)
class TranslationResult:
    """Translation output for one chunk."""

    chunk: Chunk
    translated_text: str
    provider: str
    model: str


@dataclass(frozen=True, slots=True)
class RewriteResult:
    """Audio-oriented rewrite output for one translated chunk."""

    translation: TranslationResult
    rewritten_text: str
    provider: str
    model: str


@dataclass(frozen=True, slots=True)
class AudioPart:
    """Metadata for one synthesized audio artifact."""

    chapter_index: int
    chunk_index: int
    path: Path
    duration_seconds: float


@dataclass(frozen=True, slots=True)
class RunManifest:
    """Deterministic record of a Bookvoice pipeline run.

    Attributes:
        run_id: Stable run identifier.
        config_hash: Hash of canonical run configuration.
        book: Source book metadata.
        merged_audio_path: Final merged output path.
        total_llm_cost_usd: Accumulated LLM usage cost.
        total_tts_cost_usd: Accumulated TTS usage cost.
        total_cost_usd: Total run cost estimate.
        extra: Additional implementation-specific metadata.
    """

    run_id: str
    config_hash: str
    book: BookMeta
    merged_audio_path: Path
    total_llm_cost_usd: float
    total_tts_cost_usd: float
    total_cost_usd: float
    extra: Mapping[str, str] = field(default_factory=dict)
