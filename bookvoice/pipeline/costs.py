"""Model-aware cost-estimation helpers for Bookvoice pipeline.

Responsibilities:
- Accumulate stage-level usage into the shared `CostTracker`.
- Provide stable rounded cost summaries for manifest and CLI output.
"""

from __future__ import annotations

from ..config import ProviderRuntimeConfig
from ..models.datatypes import RewriteResult, TranslationResult
from ..telemetry.cost_tracker import CostTracker
from ..telemetry.pricing import (
    LLM_INPUT_OPERATION,
    LLM_OUTPUT_OPERATION,
    TTS_CHARACTER_OPERATION,
    PricingCatalog,
)


def add_translation_costs(
    translations: list[TranslationResult],
    cost_tracker: CostTracker,
    pricing: PricingCatalog,
    runtime_config: ProviderRuntimeConfig,
) -> None:
    """Accumulate LLM cost estimate for translation stage."""

    input_price = pricing.price_for(
        provider=runtime_config.translator_provider,
        model=runtime_config.translate_model,
        operation=LLM_INPUT_OPERATION,
    )
    output_price = pricing.price_for(
        provider=runtime_config.translator_provider,
        model=runtime_config.translate_model,
        operation=LLM_OUTPUT_OPERATION,
    )

    for item in translations:
        source_chars = max(1, len(item.chunk.text))
        translated_chars = max(1, len(item.translated_text))
        cost_tracker.add_llm_usage((source_chars / 1000.0) * input_price.usd)
        cost_tracker.add_llm_usage((translated_chars / 1000.0) * output_price.usd)


def add_rewrite_costs(
    rewrites: list[RewriteResult],
    cost_tracker: CostTracker,
    pricing: PricingCatalog,
    runtime_config: ProviderRuntimeConfig,
) -> None:
    """Accumulate LLM cost estimate for rewrite stage."""

    input_price = pricing.price_for(
        provider=runtime_config.rewriter_provider,
        model=runtime_config.rewrite_model,
        operation=LLM_INPUT_OPERATION,
    )
    output_price = pricing.price_for(
        provider=runtime_config.rewriter_provider,
        model=runtime_config.rewrite_model,
        operation=LLM_OUTPUT_OPERATION,
    )

    for item in rewrites:
        input_chars = max(1, len(item.translation.translated_text))
        output_chars = max(1, len(item.rewritten_text))
        cost_tracker.add_llm_usage((input_chars / 1000.0) * input_price.usd)
        cost_tracker.add_llm_usage((output_chars / 1000.0) * output_price.usd)


def add_tts_costs(
    rewrites: list[RewriteResult],
    cost_tracker: CostTracker,
    pricing: PricingCatalog,
    runtime_config: ProviderRuntimeConfig,
) -> None:
    """Accumulate TTS cost estimate for synthesis stage."""

    price = pricing.price_for(
        provider=runtime_config.tts_provider,
        model=runtime_config.tts_model,
        operation=TTS_CHARACTER_OPERATION,
    )

    for item in rewrites:
        billable_chars = max(1, len(item.rewritten_text))
        cost_tracker.add_tts_usage((billable_chars / 1000.0) * price.usd)


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
