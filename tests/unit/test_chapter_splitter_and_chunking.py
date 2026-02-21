from pathlib import Path

from bookvoice.config import BookvoiceConfig
from bookvoice.io.chapter_splitter import ChapterSplitter
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
    chapter_text = "abcdefghijklmnopqrstuvwxyz"
    chunker = Chunker()

    chunks = chunker.to_chunks(
        chapters=[Chapter(index=1, title="Chapter 1", text=chapter_text)],
        target_size=8,
    )

    assert [(chunk.chunk_index, chunk.char_start, chunk.char_end) for chunk in chunks] == [
        (0, 0, 8),
        (1, 8, 16),
        (2, 16, 24),
        (3, 24, 26),
    ]
    assert all(len(chunk.text) <= 8 for chunk in chunks)
    assert "".join(chunk.text for chunk in chunks) == chapter_text


def test_chunker_resets_chunk_index_per_chapter() -> None:
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


def test_pipeline_translation_and_tts_keep_chunk_identity() -> None:
    pipeline = BookvoicePipeline()
    config = BookvoiceConfig(input_pdf=Path("in.pdf"), output_dir=Path("out"))
    chunk = Chunk(chapter_index=1, chunk_index=0, text="Text", char_start=0, char_end=4)

    translations = pipeline._translate([chunk], config)
    rewrites = pipeline._rewrite_for_audio(translations, config)

    assert translations[0].chunk is chunk
    assert rewrites[0].translation.chunk is chunk
