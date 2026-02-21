"""Prompt template library for LLM stages.

Responsibilities:
- Centralize prompt construction for translation and audio rewrite steps.
- Keep prompts versioned and deterministic by template key.
"""

from __future__ import annotations


class PromptLibrary:
    """Build prompt strings for supported LLM tasks."""

    def translation_system_prompt(self) -> str:
        """Return deterministic system prompt for strict translation behavior."""

        return (
            "You are a precise translation assistant. "
            "Return only translated text with no commentary."
        )

    def translate_prompt(self, source_text: str, target_language: str) -> str:
        """Return translation prompt text for provider calls."""

        return (
            f"Translate the following text into {target_language} while preserving meaning, "
            "tone, and paragraph structure. Output only the translated text.\n\n"
            f"{source_text}"
        )

    def rewrite_system_prompt(self) -> str:
        """Return deterministic system prompt for narration rewrite behavior."""

        return (
            "You rewrite text for audiobook narration. "
            "Return only rewritten narration text with no commentary."
        )

    def rewrite_for_audio_prompt(self, translated_text: str) -> str:
        """Return rewrite prompt text for natural spoken narration."""

        return (
            "Rewrite the following text to sound natural when read aloud while preserving "
            "meaning, facts, and names. Keep the same language as the input text. "
            "Output only the rewritten text.\n\n"
            f"{translated_text}"
        )
