"""Audio-oriented rewrite provider implementations.

Responsibilities:
- Adapt translated text for spoken delivery and listening clarity.
- Preserve chunk identity and provider/model metadata.
"""

from __future__ import annotations

from typing import Protocol

from ..models.datatypes import RewriteResult, TranslationResult
from .cache import ResponseCache
from .openai_client import OpenAIChatClient
from .prompts import PromptLibrary
from .rate_limiter import RateLimiter


class Rewriter(Protocol):
    """Protocol for rewrite providers."""

    def rewrite(self, translation: TranslationResult) -> RewriteResult:
        """Rewrite translated text for audio delivery."""


class AudioRewriter:
    """Rewrite translated text for audiobook narration."""

    def __init__(
        self,
        model: str = "gpt-4.1-mini",
        provider_id: str = "openai",
        api_key: str | None = None,
        response_cache: ResponseCache | None = None,
        rate_limiter: RateLimiter | None = None,
    ) -> None:
        """Initialize OpenAI-backed rewrite settings."""

        self.model = model
        self.provider_id = provider_id
        self.cache = response_cache if response_cache is not None else ResponseCache()
        self.client = OpenAIChatClient(api_key=api_key, rate_limiter=rate_limiter)
        self.prompts = PromptLibrary()

    def rewrite(self, translation: TranslationResult) -> RewriteResult:
        """Rewrite translated text with OpenAI chat-completions."""

        cache_key = self.cache.make_key(
            provider=self.provider_id,
            model=self.model,
            operation="rewrite",
            input_identity={"translated_text": translation.translated_text},
        )
        rewritten_text = self.cache.get(cache_key)
        if rewritten_text is None:
            rewritten_text = self.client.chat_completion_text(
                model=self.model,
                system_prompt=self.prompts.rewrite_system_prompt(),
                user_prompt=self.prompts.rewrite_for_audio_prompt(
                    translated_text=translation.translated_text
                ),
                temperature=0.0,
            )
            self.cache.set(cache_key, rewritten_text)
        return RewriteResult(
            translation=translation,
            rewritten_text=rewritten_text,
            provider=self.provider_id,
            model=self.model,
        )

    @property
    def cache_hits(self) -> int:
        """Return rewrite cache hit count."""

        return self.cache.hits

    @property
    def cache_misses(self) -> int:
        """Return rewrite cache miss count."""

        return self.cache.misses

    @property
    def retry_attempt_count(self) -> int:
        """Return retry attempt count performed by underlying provider client."""

        return self.client.retry_attempt_count


class DeterministicBypassRewriter:
    """Deterministic rewrite bypass that returns translated text unchanged."""

    provider_id = "bypass"
    model = "deterministic-pass-through-v1"

    def rewrite(self, translation: TranslationResult) -> RewriteResult:
        """Return a deterministic pass-through rewrite result for explicit bypass mode."""

        return RewriteResult(
            translation=translation,
            rewritten_text=translation.translated_text,
            provider=self.provider_id,
            model=self.model,
        )
