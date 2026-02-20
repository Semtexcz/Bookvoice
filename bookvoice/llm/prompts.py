"""Prompt template library for LLM stages.

Responsibilities:
- Centralize prompt construction for translation and audio rewrite steps.
- Keep prompts versioned and deterministic by template key.
"""

from __future__ import annotations


class PromptLibrary:
    """Build prompt strings for supported LLM tasks."""

    def translate_prompt(self, source_text: str, target_language: str) -> str:
        """Return translation prompt text for future provider calls."""

        return (
            f"Translate the following text into {target_language} while preserving meaning.\n\n"
            f"{source_text}"
        )

    def rewrite_for_audio_prompt(self, translated_text: str) -> str:
        """Return rewrite prompt text for natural spoken narration."""

        return (
            "Rewrite the following text for natural audiobook narration in Czech.\n\n"
            f"{translated_text}"
        )
