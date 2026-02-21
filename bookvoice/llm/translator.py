"""Translation interfaces and provider stubs.

Responsibilities:
- Define a protocol for chunk translation implementations.
- Provide a placeholder OpenAI implementation that preserves provider/model metadata.
"""

from __future__ import annotations

from typing import Protocol

from ..models.datatypes import Chunk, TranslationResult


class Translator(Protocol):
    """Protocol for translation providers."""

    def translate(self, chunk: Chunk, target_language: str) -> TranslationResult:
        """Translate one chunk into the target language."""


class OpenAITranslator:
    """Stub translator for OpenAI-backed translation integration."""

    def __init__(
        self,
        model: str = "gpt-4.1-mini",
        provider_id: str = "openai",
        api_key: str | None = None,
    ) -> None:
        """Initialize translator settings for deterministic metadata output."""

        self.model = model
        self.provider_id = provider_id
        self.api_key = api_key

    def translate(self, chunk: Chunk, target_language: str) -> TranslationResult:
        """Return a placeholder translation result while preserving model metadata."""

        _ = target_language
        _ = self.api_key
        return TranslationResult(
            chunk=chunk,
            translated_text=chunk.text,
            provider=self.provider_id,
            model=self.model,
        )
