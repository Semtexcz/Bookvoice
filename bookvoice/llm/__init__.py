"""LLM-facing abstractions for translation and rewriting.

This package defines prompt libraries, provider interfaces, and utility stubs
for rate limiting and cache interactions.
"""

from .audio_rewriter import (
    AudioRewriter,
    DeterministicBypassRewriter,
    ProficiencyAwareRewriter,
    Rewriter,
)
from .cache import ResponseCache
from .proficiency import SUPPORTED_PROFICIENCY_LEVELS, normalize_proficiency_level
from .prompts import PromptLibrary
from .rate_limiter import RateLimiter
from .translator import OpenAITranslator, ProficiencyAwareTranslator, Translator

__all__ = [
    "SUPPORTED_PROFICIENCY_LEVELS",
    "normalize_proficiency_level",
    "PromptLibrary",
    "Translator",
    "ProficiencyAwareTranslator",
    "OpenAITranslator",
    "AudioRewriter",
    "DeterministicBypassRewriter",
    "Rewriter",
    "ProficiencyAwareRewriter",
    "RateLimiter",
    "ResponseCache",
]
