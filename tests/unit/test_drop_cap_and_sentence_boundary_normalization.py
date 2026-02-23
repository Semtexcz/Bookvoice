"""Unit tests for drop-cap and sentence-boundary normalization behavior."""

from __future__ import annotations

from bookvoice.models.datatypes import Chunk
from bookvoice.text.chunking import SentenceBoundaryRepairer
from bookvoice.text.cleaners import TextCleaner


def test_drop_cap_merges_single_letter_with_following_word() -> None:
    """Cleaner should merge a standalone drop-cap line into the next word."""

    cleaner = TextCleaner()
    report = cleaner.clean_with_report("E\nVERY MOMENT IN BUSINESS MATTERS.")

    assert report.cleaned_text == "EVERY MOMENT IN BUSINESS MATTERS."
    assert report.drop_cap_merges_count == 1


def test_drop_cap_merges_when_next_word_is_after_blank_line() -> None:
    """Cleaner should merge drop-cap with one optional blank line before next text line."""

    cleaner = TextCleaner()
    report = cleaner.clean_with_report("E\n\nVERY MOMENT IN BUSINESS MATTERS.")

    assert report.cleaned_text == "EVERY MOMENT IN BUSINESS MATTERS."
    assert report.drop_cap_merges_count == 1


def test_drop_cap_merge_avoids_heading_and_list_false_positives() -> None:
    """Cleaner should keep heading/list marker patterns unchanged."""

    cleaner = TextCleaner()

    heading_report = cleaner.clean_with_report("A\nCHAPTER ONE")
    assert heading_report.cleaned_text == "A\nCHAPTER ONE"
    assert heading_report.drop_cap_merges_count == 0

    list_report = cleaner.clean_with_report("1.\nA\nALPHA item")
    assert list_report.cleaned_text == "1.\nA\nALPHA item"
    assert list_report.drop_cap_merges_count == 0


def test_sentence_boundary_repair_stitches_quote_fragment_continuation() -> None:
    """Repairer should move minimal continuation text to close split quoted sentence."""

    previous_text = 'He asked this question: "What'
    next_text = 'important truth about markets?" Then he paused.'
    previous = Chunk(
        chapter_index=1,
        chunk_index=0,
        text=previous_text,
        char_start=0,
        char_end=len(previous_text),
    )
    current = Chunk(
        chapter_index=1,
        chunk_index=1,
        text=next_text,
        char_start=len(previous_text),
        char_end=len(previous_text) + len(next_text),
    )

    report = SentenceBoundaryRepairer(max_extension_chars=80).repair(
        chunks=[previous, current],
        target_size=60,
    )

    assert report.sentence_boundary_repairs_count == 1
    assert report.chunks[0].text.endswith('important truth about markets?" ')
    assert report.chunks[0].boundary_strategy == "sentence_boundary_repaired"
    assert report.chunks[1].text.startswith("Then he paused.")
    assert report.chunks[1].char_start == report.chunks[0].char_end
