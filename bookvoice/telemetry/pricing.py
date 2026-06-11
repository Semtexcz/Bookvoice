"""Model pricing resolution for run cost accounting.

Responsibilities:
- Represent provider/model operation prices with source metadata.
- Fetch optional online pricing JSON without blocking pipeline execution.
- Provide deterministic default pricing when online pricing is unavailable.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any, Mapping

import requests

from ..config import BookvoiceConfig, ProviderRuntimeConfig

PricingOperation = str

LLM_INPUT_OPERATION = "llm_input"
LLM_OUTPUT_OPERATION = "llm_output"
TTS_CHARACTER_OPERATION = "tts_character"

_DEFAULT_SOURCE_NAME = "bookvoice-default-pricing"
_DEFAULT_SOURCE_URL = "builtin://bookvoice/default-pricing"
_PRICING_TIMEOUT_SECONDS = 5.0


@dataclass(frozen=True, slots=True)
class ModelPrice:
    """Resolved model price for one provider/model/operation tuple."""

    provider: str
    model: str
    operation: PricingOperation
    unit: str
    usd: float

    @property
    def key(self) -> tuple[str, str, PricingOperation]:
        """Return lookup key for catalog indexing."""

        return (self.provider, self.model, self.operation)


@dataclass(frozen=True, slots=True)
class PricingCatalog:
    """Lookup catalog for provider/model operation prices."""

    prices: Mapping[tuple[str, str, PricingOperation], ModelPrice]
    source_mode: str
    source_name: str
    source_url: str
    fetched_at: str
    resolved_at: str
    fallback_reason: str = ""

    def price_for(
        self,
        *,
        provider: str,
        model: str,
        operation: PricingOperation,
    ) -> ModelPrice:
        """Return a model price or a zero-price placeholder when missing."""

        found = self.prices.get((provider, model, operation))
        if found is not None:
            return found
        return ModelPrice(
            provider=provider,
            model=model,
            operation=operation,
            unit="1k_chars",
            usd=0.0,
        )

    def as_manifest_metadata(self, runtime_config: ProviderRuntimeConfig) -> dict[str, str]:
        """Return pricing source and exact runtime model metadata for manifest extras."""

        return {
            "pricing_source_mode": self.source_mode,
            "pricing_source_name": self.source_name,
            "pricing_source_url": self.source_url,
            "pricing_source_fetched_at": self.fetched_at,
            "pricing_resolved_at": self.resolved_at,
            "pricing_fallback_reason": self.fallback_reason,
            "pricing_provider_translate": runtime_config.translator_provider,
            "pricing_provider_rewrite": runtime_config.rewriter_provider,
            "pricing_provider_tts": runtime_config.tts_provider,
            "pricing_model_translate": runtime_config.translate_model,
            "pricing_model_rewrite": runtime_config.rewrite_model,
            "pricing_model_tts": runtime_config.tts_model,
            "pricing_operations": ",".join(
                (LLM_INPUT_OPERATION, LLM_OUTPUT_OPERATION, TTS_CHARACTER_OPERATION)
            ),
        }


class PricingProvider:
    """Resolve run pricing from an optional online source with deterministic fallback."""

    def resolve(
        self,
        *,
        config: BookvoiceConfig,
        runtime_config: ProviderRuntimeConfig,
        cache_path: Path | None = None,
    ) -> PricingCatalog:
        """Resolve pricing catalog for the configured runtime models."""

        pricing_url = self._pricing_url(config)
        if pricing_url is None:
            return self._default_catalog(
                runtime_config=runtime_config,
                fallback_reason="pricing_url_not_configured",
            )

        try:
            catalog = self._fetch_online_catalog(
                pricing_url=pricing_url,
                runtime_config=runtime_config,
            )
            if cache_path is not None:
                self._write_cache(cache_path, catalog)
            return catalog
        except Exception as exc:
            cached = self._load_cached_catalog(cache_path, runtime_config) if cache_path else None
            if cached is not None:
                return cached
            return self._default_catalog(
                runtime_config=runtime_config,
                fallback_reason=f"online_fetch_failed:{type(exc).__name__}",
                source_url=pricing_url,
            )

    @staticmethod
    def _pricing_url(config: BookvoiceConfig) -> str | None:
        """Return configured online pricing URL from normalized config extras."""

        value = config.extra.get("pricing_url")
        if not isinstance(value, str) or not value.strip():
            return None
        return value.strip()

    def _fetch_online_catalog(
        self,
        *,
        pricing_url: str,
        runtime_config: ProviderRuntimeConfig,
    ) -> PricingCatalog:
        """Fetch and parse an online pricing catalog."""

        response = requests.get(pricing_url, timeout=_PRICING_TIMEOUT_SECONDS)
        response.raise_for_status()
        payload = json.loads(bytes(response.content).decode("utf-8"))
        if not isinstance(payload, Mapping):
            raise ValueError("Pricing response root must be an object.")

        prices = self._parse_prices(payload, runtime_config)
        source_name = self._optional_payload_string(payload, "source") or "online-pricing"
        fetched_at = self._optional_payload_string(payload, "fetched_at") or self._utc_now()
        source_url = self._optional_payload_string(payload, "source_url") or pricing_url
        return PricingCatalog(
            prices=prices,
            source_mode="live",
            source_name=source_name,
            source_url=source_url,
            fetched_at=fetched_at,
            resolved_at=self._utc_now(),
        )

    def _parse_prices(
        self,
        payload: Mapping[str, Any],
        runtime_config: ProviderRuntimeConfig,
    ) -> dict[tuple[str, str, PricingOperation], ModelPrice]:
        """Parse online prices and merge missing runtime prices from defaults."""

        prices_payload = payload.get("prices")
        if not isinstance(prices_payload, list):
            raise ValueError("Pricing response must include a `prices` list.")

        parsed: dict[tuple[str, str, PricingOperation], ModelPrice] = {}
        for raw_item in prices_payload:
            if not isinstance(raw_item, Mapping):
                raise ValueError("Pricing response `prices` entries must be objects.")
            price = self._parse_price_item(raw_item)
            parsed[price.key] = price

        defaults = self._default_prices(runtime_config)
        for key, price in defaults.items():
            parsed.setdefault(key, price)
        return parsed

    @staticmethod
    def _parse_price_item(item: Mapping[str, Any]) -> ModelPrice:
        """Parse one price item from online JSON."""

        provider = PricingProvider._required_payload_string(item, "provider")
        model = PricingProvider._required_payload_string(item, "model")
        operation = PricingProvider._required_payload_string(item, "operation")
        unit = PricingProvider._required_payload_string(item, "unit")
        usd_raw = item.get("usd")
        if isinstance(usd_raw, bool):
            raise ValueError("Pricing item `usd` must be numeric.")
        try:
            usd = float(usd_raw)
        except (TypeError, ValueError) as exc:
            raise ValueError("Pricing item `usd` must be numeric.") from exc
        if usd < 0.0:
            raise ValueError("Pricing item `usd` must be non-negative.")
        return ModelPrice(
            provider=provider,
            model=model,
            operation=operation,
            unit=unit,
            usd=usd,
        )

    def _default_catalog(
        self,
        *,
        runtime_config: ProviderRuntimeConfig,
        fallback_reason: str,
        source_url: str = _DEFAULT_SOURCE_URL,
    ) -> PricingCatalog:
        """Return deterministic built-in pricing for the exact runtime models."""

        return PricingCatalog(
            prices=self._default_prices(runtime_config),
            source_mode="fallback",
            source_name=_DEFAULT_SOURCE_NAME,
            source_url=source_url,
            fetched_at="",
            resolved_at=self._utc_now(),
            fallback_reason=fallback_reason,
        )

    @staticmethod
    def _default_prices(
        runtime_config: ProviderRuntimeConfig,
    ) -> dict[tuple[str, str, PricingOperation], ModelPrice]:
        """Return default rates matching the previous deterministic estimator."""

        translate_rate = 0.0015
        rewrite_rate = 0.0008
        tts_rate = 0.0150
        prices = [
            ModelPrice(
                provider=runtime_config.translator_provider,
                model=runtime_config.translate_model,
                operation=LLM_INPUT_OPERATION,
                unit="1k_chars",
                usd=translate_rate,
            ),
            ModelPrice(
                provider=runtime_config.translator_provider,
                model=runtime_config.translate_model,
                operation=LLM_OUTPUT_OPERATION,
                unit="1k_chars",
                usd=translate_rate,
            ),
            ModelPrice(
                provider=runtime_config.rewriter_provider,
                model=runtime_config.rewrite_model,
                operation=LLM_INPUT_OPERATION,
                unit="1k_chars",
                usd=rewrite_rate,
            ),
            ModelPrice(
                provider=runtime_config.rewriter_provider,
                model=runtime_config.rewrite_model,
                operation=LLM_OUTPUT_OPERATION,
                unit="1k_chars",
                usd=rewrite_rate,
            ),
            ModelPrice(
                provider=runtime_config.tts_provider,
                model=runtime_config.tts_model,
                operation=TTS_CHARACTER_OPERATION,
                unit="1k_chars",
                usd=tts_rate,
            ),
        ]
        return {price.key: price for price in prices}

    @staticmethod
    def _write_cache(cache_path: Path, catalog: PricingCatalog) -> None:
        """Persist last-known online pricing metadata for fallback reuse."""

        cache_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "source": catalog.source_name,
            "source_url": catalog.source_url,
            "fetched_at": catalog.fetched_at,
            "prices": [
                {
                    "provider": price.provider,
                    "model": price.model,
                    "operation": price.operation,
                    "unit": price.unit,
                    "usd": price.usd,
                }
                for price in catalog.prices.values()
            ],
        }
        cache_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _load_cached_catalog(
        self,
        cache_path: Path | None,
        runtime_config: ProviderRuntimeConfig,
    ) -> PricingCatalog | None:
        """Load cached last-known pricing when online pricing cannot be fetched."""

        if cache_path is None or not cache_path.exists():
            return None
        try:
            payload = json.loads(cache_path.read_text(encoding="utf-8"))
            if not isinstance(payload, Mapping):
                return None
            prices = self._parse_prices(payload, runtime_config)
            return PricingCatalog(
                prices=prices,
                source_mode="fallback",
                source_name=self._optional_payload_string(payload, "source") or "cached-pricing",
                source_url=self._optional_payload_string(payload, "source_url") or str(cache_path),
                fetched_at=self._optional_payload_string(payload, "fetched_at") or "",
                resolved_at=self._utc_now(),
                fallback_reason="cached_last_known_pricing",
            )
        except Exception:
            return None

    @staticmethod
    def _required_payload_string(payload: Mapping[str, Any], key: str) -> str:
        """Read a required non-empty string from a JSON payload object."""

        value = PricingProvider._optional_payload_string(payload, key)
        if value is None:
            raise ValueError(f"Pricing payload requires non-empty `{key}`.")
        return value

    @staticmethod
    def _optional_payload_string(payload: Mapping[str, Any], key: str) -> str | None:
        """Read an optional normalized string from a JSON payload object."""

        value = payload.get(key)
        if not isinstance(value, str):
            return None
        stripped = value.strip()
        return stripped or None

    @staticmethod
    def _utc_now() -> str:
        """Return the current UTC timestamp for pricing metadata."""

        return datetime.now(UTC).replace(microsecond=0).isoformat()
