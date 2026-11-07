"""Translation interfaces and provider integrations.

Responsibilities:
- Define a protocol for chunk translation implementations.
- Provide OpenAI-backed translation implementation with provider/model metadata.
"""

from __future__ import annotations

from typing import Protocol

from ..models.datatypes import Chunk, TranslationResult
from .cache import ResponseCache
from .openai_client import OpenAIChatClient
from .proficiency import normalize_proficiency_level
from .prompts import PromptLibrary
from .rate_limiter import RateLimiter


class Translator(Protocol):
    """Protocol for translation providers that do not accept proficiency levels."""

    def translate(self, chunk: Chunk, target_language: str) -> TranslationResult:
        """Translate one chunk into the target language."""


class ProficiencyAwareTranslator(Protocol):
    """Protocol for translation providers that support CEFR proficiency targeting."""

    def translate(
        self,
        chunk: Chunk,
        target_language: str,
        *,
        proficiency_level: str | None = None,
    ) -> TranslationResult:
        """Translate one chunk, optionally targeting a CEFR proficiency level."""


class OpenAITranslator:
    """OpenAI-backed translator for chunk-level text translation."""

    def __init__(
        self,
        model: str = "gpt-4.1-mini",
        provider_id: str = "openai",
        api_key: str | None = None,
        response_cache: ResponseCache | None = None,
        rate_limiter: RateLimiter | None = None,
    ) -> None:
        """Initialize translator settings and OpenAI client dependencies."""

        self.model = model
        self.provider_id = provider_id
        self.cache = response_cache if response_cache is not None else ResponseCache()
        self.client = OpenAIChatClient(api_key=api_key, rate_limiter=rate_limiter)
        self.prompts = PromptLibrary()

    def translate(
        self,
        chunk: Chunk,
        target_language: str,
        *,
        proficiency_level: str | None = None,
    ) -> TranslationResult:
        """Translate one chunk with OpenAI chat-completions and return stage metadata."""

        normalized_level = normalize_proficiency_level(proficiency_level)
        input_identity: dict[str, object] = {
            "target_language": target_language,
            "source_text": chunk.text,
        }
        if normalized_level is not None:
            input_identity["proficiency_level"] = normalized_level
        cache_key = self.cache.make_key(
            provider=self.provider_id,
            model=self.model,
            operation="translate",
            input_identity=input_identity,
        )
        translated_text = self.cache.get(cache_key)
        if translated_text is None:
            translated_text = self.client.chat_completion_text(
                model=self.model,
                system_prompt=self.prompts.translation_system_prompt(),
                user_prompt=self.prompts.translate_prompt(
                    source_text=chunk.text,
                    target_language=target_language,
                    proficiency_level=normalized_level,
                ),
                temperature=0.0,
            )
            self.cache.set(cache_key, translated_text)
        return TranslationResult(
            chunk=chunk,
            translated_text=translated_text,
            provider=self.provider_id,
            model=self.model,
        )

    @property
    def cache_hits(self) -> int:
        """Return translation cache hit count."""

        return self.cache.hits

    @property
    def cache_misses(self) -> int:
        """Return translation cache miss count."""

        return self.cache.misses

    @property
    def retry_attempt_count(self) -> int:
        """Return retry attempt count performed by underlying provider client."""

        return self.client.retry_attempt_count
