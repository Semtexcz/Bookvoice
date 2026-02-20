"""LLM-facing abstractions for translation and rewriting.

This package defines prompt libraries, provider interfaces, and utility stubs
for rate limiting and cache interactions.
"""

from .audio_rewriter import AudioRewriter
from .cache import ResponseCache
from .prompts import PromptLibrary
from .rate_limiter import RateLimiter
from .translator import OpenAITranslator, Translator

__all__ = [
    "PromptLibrary",
    "Translator",
    "OpenAITranslator",
    "AudioRewriter",
    "RateLimiter",
    "ResponseCache",
]
