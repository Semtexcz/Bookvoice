"""Deterministic cost-estimation helpers for Bookvoice pipeline.

Responsibilities:
- Accumulate stage-level usage into the shared `CostTracker`.
- Provide stable rounded cost summaries for manifest and CLI output.
"""

from __future__ import annotations

from .models.datatypes import RewriteResult, TranslationResult
from .telemetry.cost_tracker import CostTracker


_TRANSLATE_COST_PER_1K_CHARS_USD = 0.0015
_REWRITE_COST_PER_1K_CHARS_USD = 0.0008
_TTS_COST_PER_1K_CHARS_USD = 0.0150


def add_translation_costs(
    translations: list[TranslationResult], cost_tracker: CostTracker
) -> None:
    """Accumulate deterministic LLM cost estimate for translation stage."""

    for item in translations:
        source_chars = len(item.chunk.text)
        translated_chars = len(item.translated_text)
        billable_chars = max(1, source_chars + translated_chars)
        cost_tracker.add_llm_usage((billable_chars / 1000.0) * _TRANSLATE_COST_PER_1K_CHARS_USD)


def add_rewrite_costs(rewrites: list[RewriteResult], cost_tracker: CostTracker) -> None:
    """Accumulate deterministic LLM cost estimate for rewrite stage."""

    for item in rewrites:
        input_chars = len(item.translation.translated_text)
        output_chars = len(item.rewritten_text)
        billable_chars = max(1, input_chars + output_chars)
        cost_tracker.add_llm_usage((billable_chars / 1000.0) * _REWRITE_COST_PER_1K_CHARS_USD)


def add_tts_costs(rewrites: list[RewriteResult], cost_tracker: CostTracker) -> None:
    """Accumulate deterministic TTS cost estimate for synthesis stage."""

    for item in rewrites:
        billable_chars = max(1, len(item.rewritten_text))
        cost_tracker.add_tts_usage((billable_chars / 1000.0) * _TTS_COST_PER_1K_CHARS_USD)


def rounded_cost_summary(cost_tracker: CostTracker) -> dict[str, float]:
    """Return cost summary rounded for stable JSON and CLI display."""

    summary = cost_tracker.summary()
    llm_cost_usd = round(summary["llm_cost_usd"], 6)
    tts_cost_usd = round(summary["tts_cost_usd"], 6)
    return {
        "llm_cost_usd": llm_cost_usd,
        "tts_cost_usd": tts_cost_usd,
        "total_cost_usd": round(llm_cost_usd + tts_cost_usd, 6),
    }
