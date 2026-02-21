"""Translation interfaces and provider integrations.

Responsibilities:
- Define a protocol for chunk translation implementations.
- Provide OpenAI-backed translation implementation with provider/model metadata.
"""

from __future__ import annotations

from typing import Protocol

from ..models.datatypes import Chunk, TranslationResult
from .openai_client import OpenAIChatClient
from .prompts import PromptLibrary


class Translator(Protocol):
    """Protocol for translation providers."""

    def translate(self, chunk: Chunk, target_language: str) -> TranslationResult:
        """Translate one chunk into the target language."""


class OpenAITranslator:
    """OpenAI-backed translator for chunk-level text translation."""

    def __init__(
        self,
        model: str = "gpt-4.1-mini",
        provider_id: str = "openai",
        api_key: str | None = None,
    ) -> None:
        """Initialize translator settings and OpenAI client dependencies."""

        self.model = model
        self.provider_id = provider_id
        self.client = OpenAIChatClient(api_key=api_key)
        self.prompts = PromptLibrary()

    def translate(self, chunk: Chunk, target_language: str) -> TranslationResult:
        """Translate one chunk with OpenAI chat-completions and return stage metadata."""

        translated_text = self.client.chat_completion_text(
            model=self.model,
            system_prompt=self.prompts.translation_system_prompt(),
            user_prompt=self.prompts.translate_prompt(
                source_text=chunk.text,
                target_language=target_language,
            ),
            temperature=0.0,
        )
        return TranslationResult(
            chunk=chunk,
            translated_text=translated_text,
            provider=self.provider_id,
            model=self.model,
        )
