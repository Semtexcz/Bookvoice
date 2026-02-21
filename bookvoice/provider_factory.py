"""Provider factory helpers for translation, rewrite, and TTS stages.

Responsibilities:
- Resolve provider identifiers to concrete stage implementations.
- Keep orchestration independent from concrete provider class construction.

Notes:
- Only `openai` is implemented at the moment.
- Factory mappings are intentionally explicit to simplify future provider additions.
"""

from __future__ import annotations

from pathlib import Path

from .llm.audio_rewriter import AudioRewriter, Rewriter
from .llm.translator import OpenAITranslator, Translator
from .tts.synthesizer import OpenAITTSSynthesizer, TTSSynthesizer


class ProviderFactory:
    """Factory for provider-backed stage clients used by the pipeline."""

    @staticmethod
    def create_translator(
        provider_id: str,
        model: str,
        api_key: str | None = None,
    ) -> Translator:
        """Create a translator client for a configured provider identifier."""

        if provider_id == "openai":
            return OpenAITranslator(model=model, provider_id=provider_id, api_key=api_key)
        raise ValueError(f"Unsupported translator provider `{provider_id}`.")

    @staticmethod
    def create_rewriter(
        provider_id: str,
        model: str,
        api_key: str | None = None,
    ) -> Rewriter:
        """Create a rewrite client for a configured provider identifier."""

        if provider_id == "openai":
            return AudioRewriter(model=model, provider_id=provider_id, api_key=api_key)
        raise ValueError(f"Unsupported rewriter provider `{provider_id}`.")

    @staticmethod
    def create_tts_synthesizer(
        provider_id: str,
        output_root: Path,
        model: str,
        api_key: str | None = None,
    ) -> TTSSynthesizer:
        """Create a TTS synthesizer client for a configured provider identifier."""

        if provider_id == "openai":
            return OpenAITTSSynthesizer(
                output_root=output_root,
                model=model,
                provider_id=provider_id,
                api_key=api_key,
            )
        raise ValueError(f"Unsupported TTS provider `{provider_id}`.")
