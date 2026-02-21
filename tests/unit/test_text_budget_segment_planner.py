"""Unit tests for deterministic text-budget segment planning."""

from __future__ import annotations

from bookvoice.models.datatypes import ChapterStructureUnit
from bookvoice.text.segment_planner import TextBudgetSegmentPlanner


def test_planner_splits_using_paragraph_boundaries_under_budget() -> None:
    """Planner should split oversized units at paragraph boundaries when possible."""

    planner = TextBudgetSegmentPlanner()
    units = [
        ChapterStructureUnit(
            order_index=1,
            chapter_index=1,
            chapter_title="Chapter 1",
            subchapter_index=1,
            subchapter_title="1.1",
            text=f"{'A' * 2000}\n\n{'B' * 2000}\n\n{'C' * 2000}",
            char_start=0,
            char_end=6004,
            source="text_heuristic",
        )
    ]

    plan = planner.plan(units, budget_chars=4500)

    assert plan.budget_chars == 4500
    assert len(plan.segments) == 2
    assert "A" * 2000 in plan.segments[0].text
    assert "B" * 2000 in plan.segments[0].text
    assert plan.segments[0].text.endswith("B" * 2000)
    assert plan.segments[1].text == "C" * 2000


def test_planner_merges_short_subchapters_but_keeps_chapter_boundaries() -> None:
    """Planner should merge short adjacent subchapters only within the same chapter."""

    planner = TextBudgetSegmentPlanner()
    units = [
        ChapterStructureUnit(
            order_index=1,
            chapter_index=1,
            chapter_title="Chapter 1",
            subchapter_index=1,
            subchapter_title="1.1",
            text="Alpha",
            char_start=0,
            char_end=5,
            source="text_heuristic",
        ),
        ChapterStructureUnit(
            order_index=2,
            chapter_index=1,
            chapter_title="Chapter 1",
            subchapter_index=2,
            subchapter_title="1.2",
            text="Beta",
            char_start=6,
            char_end=10,
            source="text_heuristic",
        ),
        ChapterStructureUnit(
            order_index=3,
            chapter_index=2,
            chapter_title="Chapter 2",
            subchapter_index=None,
            subchapter_title=None,
            text="Gamma",
            char_start=0,
            char_end=5,
            source="text_heuristic",
        ),
    ]

    plan = planner.plan(units, budget_chars=100)

    assert [segment.chapter_index for segment in plan.segments] == [1, 2]
    assert plan.segments[0].text == "Alpha\n\nBeta"
    assert plan.segments[0].source_order_indices == (1, 2)
    assert plan.segments[1].text == "Gamma"
    assert plan.segments[1].source_order_indices == (3,)


def test_planner_is_stable_across_repeated_runs_and_clamps_budget_ceiling() -> None:
    """Planner should produce identical output and clamp budget above ceiling."""

    planner = TextBudgetSegmentPlanner()
    units = [
        ChapterStructureUnit(
            order_index=2,
            chapter_index=1,
            chapter_title="Chapter 1",
            subchapter_index=2,
            subchapter_title="1.2",
            text="Second.",
            char_start=8,
            char_end=15,
            source="text_heuristic",
        ),
        ChapterStructureUnit(
            order_index=1,
            chapter_index=1,
            chapter_title="Chapter 1",
            subchapter_index=1,
            subchapter_title="1.1",
            text="First.",
            char_start=0,
            char_end=6,
            source="text_heuristic",
        ),
    ]

    first = planner.plan(units, budget_chars=10000)
    second = planner.plan(units, budget_chars=10000)

    assert first == second
    assert first.budget_chars == planner.TEN_MINUTE_BUDGET_CEILING_CHARS
    assert [segment.text for segment in first.segments] == ["First.\n\nSecond."]
    assert planner.to_chunks(first)[0].chunk_index == 0


def test_planner_to_chunks_uses_ascii_slug_for_part_ids() -> None:
    """Planner chunk identifiers should use deterministic ASCII slugs from chapter titles."""

    planner = TextBudgetSegmentPlanner()
    units = [
        ChapterStructureUnit(
            order_index=1,
            chapter_index=1,
            chapter_title="Český název: Úvod!",
            subchapter_index=None,
            subchapter_title=None,
            text="Text.",
            char_start=0,
            char_end=5,
            source="text_heuristic",
        ),
    ]

    chunks = planner.to_chunks(planner.plan(units, budget_chars=100))

    assert chunks[0].part_id == "001_01_cesky-nazev-uvod"


def test_planner_long_paragraph_split_prefers_sentence_boundary() -> None:
    """Planner should split oversized paragraph at sentence boundary when possible."""

    planner = TextBudgetSegmentPlanner()
    text = "A short sentence. Another short one."
    units = [
        ChapterStructureUnit(
            order_index=1,
            chapter_index=1,
            chapter_title="Chapter 1",
            subchapter_index=1,
            subchapter_title="1.1",
            text=text,
            char_start=0,
            char_end=len(text),
            source="text_heuristic",
        )
    ]

    plan = planner.plan(units, budget_chars=15)

    assert len(plan.segments) == 2
    assert plan.segments[0].text == "A short sentence."
    assert plan.segments[1].text == "Another short one."


def test_planner_long_paragraph_split_avoids_decimal_and_abbreviation_boundaries() -> None:
    """Planner should avoid splitting on abbreviation and decimal periods."""

    planner = TextBudgetSegmentPlanner()
    text = "Dr. Smith measured 3.14 units today. Then he wrote a report."
    units = [
        ChapterStructureUnit(
            order_index=1,
            chapter_index=1,
            chapter_title="Chapter 1",
            subchapter_index=1,
            subchapter_title="1.1",
            text=text,
            char_start=0,
            char_end=len(text),
            source="text_heuristic",
        )
    ]

    plan = planner.plan(units, budget_chars=30)

    assert len(plan.segments) == 2
    assert plan.segments[0].text == "Dr. Smith measured 3.14 units today."
    assert plan.segments[1].text == "Then he wrote a report."
