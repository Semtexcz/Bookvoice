"""Audio-oriented rewrite provider implementations.

Responsibilities:
- Adapt translated text for spoken delivery and listening clarity.
- Preserve chunk identity and provider/model metadata.
"""

from __future__ import annotations

from typing import Protocol

from ..models.datatypes import RewriteResult, TranslationResult
from .openai_client import OpenAIChatClient
from .prompts import PromptLibrary


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
        """Initialize OpenAI-backed rewrite settings."""

        self.model = model
        self.provider_id = provider_id
        self.client = OpenAIChatClient(api_key=api_key)
        self.prompts = PromptLibrary()

    def rewrite(self, translation: TranslationResult) -> RewriteResult:
        """Rewrite translated text with OpenAI chat-completions."""

        rewritten_text = self.client.chat_completion_text(
            model=self.model,
            system_prompt=self.prompts.rewrite_system_prompt(),
            user_prompt=self.prompts.rewrite_for_audio_prompt(
                translated_text=translation.translated_text
            ),
            temperature=0.0,
        )
        return RewriteResult(
            translation=translation,
            rewritten_text=rewritten_text,
            provider=self.provider_id,
            model=self.model,
        )


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
