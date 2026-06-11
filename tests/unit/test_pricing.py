"""Unit tests for online and fallback pricing resolution."""

from __future__ import annotations

import json
from pathlib import Path

import requests
import pytest

from bookvoice.config import BookvoiceConfig, ProviderRuntimeConfig
from bookvoice.models.datatypes import Chunk, RewriteResult, TranslationResult
from bookvoice.pipeline.costs import (
    add_rewrite_costs,
    add_translation_costs,
    add_tts_costs,
    rounded_cost_summary,
)
from bookvoice.telemetry.cost_tracker import CostTracker
from bookvoice.telemetry.pricing import PricingProvider


class _FakeResponse:
    """Minimal requests response fake for pricing fetch tests."""

    def __init__(self, payload: dict[str, object]) -> None:
        """Initialize fake response bytes from a JSON payload."""

        self.content = json.dumps(payload).encode("utf-8")
        self.status_code = 200

    def raise_for_status(self) -> None:
        """Expose requests-compatible status hook."""


def _runtime_config() -> ProviderRuntimeConfig:
    """Return deterministic runtime model identifiers for pricing tests."""

    return ProviderRuntimeConfig(
        translator_provider="openai",
        rewriter_provider="openai",
        tts_provider="openai",
        translate_model="translate-model",
        rewrite_model="rewrite-model",
        tts_model="tts-model",
        tts_voice="echo",
    )


def _bookvoice_config(tmp_path: Path, pricing_url: str | None = None) -> BookvoiceConfig:
    """Return minimal Bookvoice config with optional pricing URL."""

    extra = {"pricing_url": pricing_url} if pricing_url is not None else {}
    return BookvoiceConfig(
        input_pdf=Path("tests/files/path_only_placeholder.pdf"),
        output_dir=tmp_path,
        extra=extra,
    )


def _sample_usage() -> tuple[list[TranslationResult], list[RewriteResult]]:
    """Return sample translation and rewrite usage with known character counts."""

    chunk = Chunk(
        chapter_index=1,
        chunk_index=0,
        text="abcd",
        char_start=0,
        char_end=4,
    )
    translation = TranslationResult(
        chunk=chunk,
        translated_text="abcdef",
        provider="openai",
        model="translate-model",
    )
    rewrite = RewriteResult(
        translation=translation,
        rewritten_text="abcdefgh",
        provider="openai",
        model="rewrite-model",
    )
    return [translation], [rewrite]


def test_online_pricing_response_drives_cost_calculation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Online pricing should resolve exact model operation rates for cost math."""

    payload: dict[str, object] = {
        "source": "test-pricing",
        "source_url": "https://pricing.example/catalog.json",
        "fetched_at": "2026-06-11T08:00:00+00:00",
        "prices": [
            {
                "provider": "openai",
                "model": "translate-model",
                "operation": "llm_input",
                "unit": "1k_chars",
                "usd": 1.0,
            },
            {
                "provider": "openai",
                "model": "translate-model",
                "operation": "llm_output",
                "unit": "1k_chars",
                "usd": 2.0,
            },
            {
                "provider": "openai",
                "model": "rewrite-model",
                "operation": "llm_input",
                "unit": "1k_chars",
                "usd": 3.0,
            },
            {
                "provider": "openai",
                "model": "rewrite-model",
                "operation": "llm_output",
                "unit": "1k_chars",
                "usd": 4.0,
            },
            {
                "provider": "openai",
                "model": "tts-model",
                "operation": "tts_character",
                "unit": "1k_chars",
                "usd": 5.0,
            },
        ],
    }

    def fake_get(url: str, *, timeout: float | tuple[float, float] | None = None) -> _FakeResponse:
        """Return deterministic online pricing payload."""

        assert url == "https://pricing.example/catalog.json"
        assert timeout is not None
        return _FakeResponse(payload)

    monkeypatch.setattr(requests, "get", fake_get)
    runtime_config = _runtime_config()
    pricing = PricingProvider().resolve(
        config=_bookvoice_config(tmp_path, "https://pricing.example/catalog.json"),
        runtime_config=runtime_config,
        cache_path=tmp_path / "pricing-cache.json",
    )
    translations, rewrites = _sample_usage()
    cost_tracker = CostTracker()

    add_translation_costs(translations, cost_tracker, pricing, runtime_config)
    add_rewrite_costs(rewrites, cost_tracker, pricing, runtime_config)
    add_tts_costs(rewrites, cost_tracker, pricing, runtime_config)
    summary = rounded_cost_summary(cost_tracker)
    metadata = pricing.as_manifest_metadata(runtime_config)

    assert summary["llm_cost_usd"] == 0.066
    assert summary["tts_cost_usd"] == 0.04
    assert summary["total_cost_usd"] == 0.106
    assert metadata["pricing_source_mode"] == "live"
    assert metadata["pricing_source_name"] == "test-pricing"
    assert metadata["pricing_model_translate"] == "translate-model"
    assert (tmp_path / "pricing-cache.json").exists()


def test_pricing_falls_back_to_defaults_when_online_fetch_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pricing resolution should not block runs when online pricing is unavailable."""

    def fake_get(url: str, *, timeout: float | tuple[float, float] | None = None) -> _FakeResponse:
        """Raise a transport error for fallback testing."""

        raise requests.ConnectionError("offline")

    monkeypatch.setattr(requests, "get", fake_get)
    runtime_config = _runtime_config()
    pricing = PricingProvider().resolve(
        config=_bookvoice_config(tmp_path, "https://pricing.example/catalog.json"),
        runtime_config=runtime_config,
    )
    translations, rewrites = _sample_usage()
    cost_tracker = CostTracker()

    add_translation_costs(translations, cost_tracker, pricing, runtime_config)
    add_rewrite_costs(rewrites, cost_tracker, pricing, runtime_config)
    add_tts_costs(rewrites, cost_tracker, pricing, runtime_config)
    summary = rounded_cost_summary(cost_tracker)
    metadata = pricing.as_manifest_metadata(runtime_config)

    assert summary["llm_cost_usd"] == 0.000026
    assert summary["tts_cost_usd"] == 0.00012
    assert metadata["pricing_source_mode"] == "fallback"
    assert metadata["pricing_source_name"] == "bookvoice-default-pricing"
    assert metadata["pricing_fallback_reason"].startswith("online_fetch_failed:")
