"""Core datatypes shared across Bookvoice modules.

Responsibilities:
- Represent immutable records exchanged between pipeline stages.
- Provide explicit typing for reproducibility and serialization.

Key types:
- `BookMeta`, `Chapter`, `Chunk`, `TranslationResult`, `RewriteResult`,
  `AudioPart`, `ChapterStructureUnit`, `PlannedSegment`, `SegmentPlan`,
  and `RunManifest`.
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
        part_index: Optional 1-based part index aligned with segmented planning.
        part_title: Optional chapter/part title used for deterministic filenames.
        part_id: Optional stable part identifier.
        source_order_indices: Ordered structure-unit order indices that produced this chunk.
        boundary_strategy: Boundary classification (`sentence_complete`, `chapter_end`,
            or `forced_split_no_sentence_boundary`).
    """

    chapter_index: int
    chunk_index: int
    text: str
    char_start: int
    char_end: int
    part_index: int | None = None
    part_title: str | None = None
    part_id: str | None = None
    source_order_indices: tuple[int, ...] = field(default_factory=tuple)
    boundary_strategy: str = "sentence_complete"


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
    part_index: int | None = None
    part_title: str | None = None
    part_id: str | None = None
    source_order_indices: tuple[int, ...] = field(default_factory=tuple)
    provider: str | None = None
    model: str | None = None
    voice: str | None = None


@dataclass(frozen=True, slots=True)
class ChapterStructureUnit:
    """Normalized chapter/subchapter structure unit for downstream audio planning.

    Attributes:
        order_index: 1-based deterministic unit ordering across the full book.
        chapter_index: 1-based chapter index this unit belongs to.
        chapter_title: Normalized chapter title.
        subchapter_index: 1-based subchapter index within chapter, or `None`.
        subchapter_title: Normalized subchapter title, or `None`.
        text: Text payload represented by this planning unit.
        char_start: Inclusive character offset in chapter text.
        char_end: Exclusive character offset in chapter text.
        source: Source for this unit (`pdf_outline` or `text_heuristic`).
    """

    order_index: int
    chapter_index: int
    chapter_title: str
    subchapter_index: int | None
    subchapter_title: str | None
    text: str
    char_start: int
    char_end: int
    source: str


@dataclass(frozen=True, slots=True)
class PlannedSegment:
    """Deterministic segment planned from chapter/subchapter structure units.

    Attributes:
        order_index: 1-based deterministic segment ordering across the full plan.
        chapter_index: 1-based chapter index this segment belongs to.
        segment_index: 0-based segment index within chapter.
        chapter_title: Chapter title associated with this segment.
        text: Planned segment text payload.
        char_start: Inclusive character offset in chapter text.
        char_end: Exclusive character offset in chapter text.
        source_order_indices: Ordered structure-unit order indices merged into segment.
    """

    order_index: int
    chapter_index: int
    segment_index: int
    chapter_title: str
    text: str
    char_start: int
    char_end: int
    source_order_indices: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class SegmentPlan:
    """Deterministic segment plan output for pipeline/TTS consumption.

    Attributes:
        budget_chars: Active per-segment character budget used by planner.
        budget_ceiling_chars: Maximum allowed character budget after clamping.
        segments: Ordered planned segments.
    """

    budget_chars: int
    budget_ceiling_chars: int
    segments: tuple[PlannedSegment, ...]


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
