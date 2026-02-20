"""Voice profile models for synthesis configuration.

Responsibilities:
- Represent provider voice identities and tuning metadata.
- Decouple pipeline logic from provider-specific naming.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class VoiceProfile:
    """Declarative voice profile used by TTS providers.

    Attributes:
        name: Human-readable profile name.
        provider_voice_id: Provider-native voice identifier.
        language: BCP-47 or short language code.
        speaking_rate: Relative speaking rate multiplier.
    """

    name: str
    provider_voice_id: str
    language: str
    speaking_rate: float = 1.0
