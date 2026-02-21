"""Audio-oriented rewrite stage scaffold.

Responsibilities:
- Adapt translated text for spoken delivery and listening clarity.
- Preserve chunk identity for deterministic downstream synthesis.
"""

from __future__ import annotations

from typing import Protocol

from ..models.datatypes import RewriteResult, TranslationResult


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
    ) -> None:
        """Initialize rewriter settings for deterministic metadata output."""

        self.model = model
        self.provider_id = provider_id
        self.api_key = api_key

    def rewrite(self, translation: TranslationResult) -> RewriteResult:
        """Return a placeholder rewrite result while preserving model metadata."""

        _ = self.api_key
        return RewriteResult(
            translation=translation,
            rewritten_text=translation.translated_text,
            provider=self.provider_id,
            model=self.model,
        )
