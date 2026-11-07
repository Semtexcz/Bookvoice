"""Prompt template library for LLM stages.

Responsibilities:
- Centralize prompt construction for translation and audio rewrite steps.
- Keep prompts versioned and deterministic by template key.
- Apply optional CEFR proficiency guidance without changing legacy prompts.
"""

from __future__ import annotations

from .proficiency import normalize_proficiency_level


def _proficiency_guidance(level: str) -> str:
    """Return the deterministic CEFR guidance block for a normalized level."""

    return (
        f"Target CEFR proficiency level {level} by adjusting vocabulary and sentence "
        "complexity for that level. Preserve meaning, factual information, names, and "
        "numbers. Do not add or remove information."
    )


class PromptLibrary:
    """Build prompt strings for supported LLM tasks."""

    def translation_system_prompt(self) -> str:
        """Return deterministic system prompt for strict translation behavior."""

        return (
            "You are a precise translation assistant. "
            "Return only translated text with no commentary."
        )

    def translate_prompt(
        self,
        source_text: str,
        target_language: str,
        *,
        proficiency_level: str | None = None,
    ) -> str:
        """Return translation prompt text for provider calls."""

        normalized_level = normalize_proficiency_level(proficiency_level)
        prompt = (
            f"Translate the following text into {target_language} while preserving meaning, "
            "tone, and paragraph structure. Output only the translated text.\n\n"
        )
        if normalized_level is not None:
            prompt += f"{_proficiency_guidance(normalized_level)}\n\n"
        return f"{prompt}{source_text}"

    def rewrite_system_prompt(self) -> str:
        """Return deterministic system prompt for narration rewrite behavior."""

        return (
            "You are an expert audiobook narration editor. Rewrite text for natural spoken "
            "delivery while preserving meaning, facts, names, and chronology. "
            "Return only rewritten narration text with no commentary."
        )

    def rewrite_for_audio_prompt(
        self,
        translated_text: str,
        *,
        proficiency_level: str | None = None,
    ) -> str:
        """Return rewrite prompt text for natural spoken narration."""

        normalized_level = normalize_proficiency_level(proficiency_level)
        prompt = (
            "Rewrite the following text for audiobook narration.\n"
            "Requirements:\n"
            "- Keep the same language as the input text.\n"
            "- Preserve all facts, names, numbers, and key details.\n"
            "- Improve listenability with natural spoken rhythm and clear sentence flow.\n"
            "- Prefer concise spoken phrasing and punctuation that supports pauses.\n"
            "- Keep paragraph structure unless a small split improves clarity.\n"
            "- Do not add new information, analysis, or meta commentary.\n"
        )
        if normalized_level is not None:
            prompt += f"- {_proficiency_guidance(normalized_level)}\n"
        return f"{prompt}Output only the rewritten text.\n\n{translated_text}"
