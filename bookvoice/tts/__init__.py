"""Text-to-speech provider abstractions.

This package contains voice profile types and synthesizer interfaces used by the
pipeline TTS stage.
"""

from .synthesizer import OpenAITTSSynthesizer, TTSSynthesizer
from .voices import VoiceProfile

__all__ = ["VoiceProfile", "TTSSynthesizer", "OpenAITTSSynthesizer"]
