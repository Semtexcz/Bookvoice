from pathlib import Path

import pytest

from bookvoice.config import BookvoiceConfig
from bookvoice.io.chapter_splitter import ChapterSplitter
from bookvoice.llm.openai_client import OpenAIChatClient
from bookvoice.models.datatypes import Chapter, Chunk
from bookvoice.pipeline import BookvoicePipeline
from bookvoice.text.chunking import Chunker


def test_chapter_splitter_returns_empty_for_blank_text() -> None:
    splitter = ChapterSplitter()
    assert splitter.split(" \n\t ") == []


def test_chapter_splitter_splits_common_heading_format_deterministically() -> None:
    text = (
        "CHAPTER 1\n"
        "Alpha line.\n"
        "\n"
        "CHAPTER 2: Beta\n"
        "Beta line.\n"
    )
    splitter = ChapterSplitter()

    chapters = splitter.split(text)

    assert [chapter.index for chapter in chapters] == [1, 2]
    assert [chapter.title for chapter in chapters] == ["CHAPTER 1", "CHAPTER 2: Beta"]
    assert [chapter.text for chapter in chapters] == ["Alpha line.", "Beta line."]


def test_chunker_generates_bounded_chunks_with_stable_offsets() -> None:
    """Chunker should preserve deterministic offsets and text reassembly."""

    chapter_text = "alpha beta gamma delta epsilon zeta eta theta iota kappa"
    chunker = Chunker()

    chunks = chunker.to_chunks(
        chapters=[Chapter(index=1, title="Chapter 1", text=chapter_text)],
        target_size=8,
    )

    assert chunks[0].char_start == 0
    for previous, current in zip(chunks, chunks[1:]):
        assert current.char_start == previous.char_end
        assert current.chunk_index == previous.chunk_index + 1
    assert any(
        chunk.boundary_strategy == "forced_split_no_sentence_boundary" for chunk in chunks[:-1]
    )
    assert "".join(chunk.text for chunk in chunks) == chapter_text


def test_chunker_resets_chunk_index_per_chapter() -> None:
    """Chunk indices should be chapter-local and reset for each chapter."""

    chunker = Chunker()
    chapters = [
        Chapter(index=1, title="Chapter 1", text="abcdef"),
        Chapter(index=2, title="Chapter 2", text="123456"),
    ]

    chunks = chunker.to_chunks(chapters=chapters, target_size=3)

    assert [(chunk.chapter_index, chunk.chunk_index) for chunk in chunks] == [
        (1, 0),
        (1, 1),
        (2, 0),
        (2, 1),
    ]


def test_chunker_prefers_period_before_other_sentence_endings() -> None:
    """Chunker should prefer period boundaries over exclamation/question marks."""

    chunker = Chunker()
    text = "One short sentence. Another one! Final question?"

    chunks = chunker.to_chunks(
        chapters=[Chapter(index=1, title="Chapter 1", text=text)],
        target_size=24,
    )

    assert chunks[0].text == "One short sentence. "
    assert chunks[0].boundary_strategy == "sentence_complete"


def test_chunker_extends_to_next_sentence_boundary_within_safety_margin() -> None:
    """Chunker should extend beyond target size to finish a sentence when needed."""

    chunker = Chunker()
    text = f"{'x' * 25}. Tail sentence."

    chunks = chunker.to_chunks(
        chapters=[Chapter(index=1, title="Chapter 1", text=text)],
        target_size=20,
    )

    assert chunks[0].text == f"{'x' * 25}. "
    assert len(chunks[0].text) > 20
    assert chunks[0].boundary_strategy == "sentence_complete"


def test_chunker_avoids_abbreviation_and_decimal_false_sentence_boundaries() -> None:
    """Chunker should not split at abbreviation or decimal period characters."""

    chunker = Chunker()
    text = "Dr. Smith measured 3.14 units today. He documented results."

    chunks = chunker.to_chunks(
        chapters=[Chapter(index=1, title="Chapter 1", text=text)],
        target_size=28,
    )

    assert chunks[0].text == "Dr. Smith measured 3.14 units today. "
    assert chunks[0].boundary_strategy == "sentence_complete"


def test_chunker_marks_forced_fallback_for_no_punctuation_text() -> None:
    """Chunker should mark forced fallback splits when no sentence boundary exists."""

    chunker = Chunker()
    text = "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu"

    chunks = chunker.to_chunks(
        chapters=[Chapter(index=1, title="Chapter 1", text=text)],
        target_size=18,
    )

    assert any(
        chunk.boundary_strategy == "forced_split_no_sentence_boundary" for chunk in chunks[:-1]
    )
    assert chunks[-1].boundary_strategy == "chapter_end"
    assert "".join(chunk.text for chunk in chunks) == text


def test_pipeline_translation_and_tts_keep_chunk_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pipeline translation/rewrite should preserve the original chunk identity."""

    def _mock_chat_completion(self, **kwargs: object) -> str:
        """Return deterministic provider text to avoid network calls in unit tests."""

        _ = self
        _ = kwargs
        return "mocked text"

    monkeypatch.setattr(OpenAIChatClient, "chat_completion_text", _mock_chat_completion)

    pipeline = BookvoicePipeline()
    config = BookvoiceConfig(input_pdf=Path("in.pdf"), output_dir=Path("out"))
    chunk = Chunk(chapter_index=1, chunk_index=0, text="Text", char_start=0, char_end=4)

    translations = pipeline._translate([chunk], config)
    rewrites = pipeline._rewrite_for_audio(translations, config)

    assert translations[0].chunk is chunk
    assert rewrites[0].translation.chunk is chunk


def test_pipeline_fallback_chunk_part_id_uses_title_slug() -> None:
    """Fallback chunk decoration should use chapter-part-title deterministic identifiers."""

    pipeline = BookvoicePipeline()
    chunks = [
        Chunk(chapter_index=1, chunk_index=0, text="Alpha", char_start=0, char_end=5),
    ]
    chapters = [
        Chapter(index=1, title="Český název: Úvod!", text="Alpha"),
    ]

    decorated = pipeline._decorate_chunks_with_part_metadata(chunks, chapters)

    assert decorated[0].part_id == "001_01_cesky-nazev-uvod"
