"""Translation interfaces and provider stubs.

Responsibilities:
- Define a protocol for chunk translation implementations.
- Provide a placeholder provider class for future OpenAI integration.
"""

from __future__ import annotations

from typing import Protocol

from ..models.datatypes import Chunk, TranslationResult


class Translator(Protocol):
    """Protocol for translation providers."""

    def translate(self, chunk: Chunk, target_language: str) -> TranslationResult:
        """Translate one chunk into the target language."""


class OpenAITranslator:
    """Stub translator for future OpenAI-backed translation."""

    def translate(self, chunk: Chunk, target_language: str) -> TranslationResult:
        """Return a placeholder translation result."""

        _ = target_language
        return TranslationResult(
            chunk=chunk,
            translated_text=chunk.text,
            provider="openai",
            model="stub-model",
        )
