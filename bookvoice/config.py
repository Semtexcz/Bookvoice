"""Configuration model and loaders for Bookvoice.

Responsibilities:
- Define runtime configuration as a typed dataclass.
- Provide loader entry points for file- and environment-based configuration.

Key types:
- `BookvoiceConfig`: normalized runtime settings for a pipeline run.
- `ConfigLoader`: static construction helpers for `BookvoiceConfig`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping


@dataclass(slots=True)
class BookvoiceConfig:
    """Runtime configuration for one pipeline run.

    Attributes:
        input_pdf: Path to the source PDF.
        output_dir: Output directory for generated artifacts.
        language: Target language code, defaulting to Czech (`cs`).
        provider_translator: Planned translator provider identifier.
        provider_tts: Planned TTS provider identifier.
        chunk_size_chars: Target chunk size in characters.
        resume: Whether pipeline should attempt to resume from artifacts.
    """

    input_pdf: Path
    output_dir: Path
    language: str = "cs"
    provider_translator: str = "openai"
    provider_tts: str = "openai"
    chunk_size_chars: int = 1800
    resume: bool = False
    extra: dict[str, str] = field(default_factory=dict)


class ConfigLoader:
    """Factory methods for creating `BookvoiceConfig`.

    Real parsing logic is intentionally deferred to future implementation.
    """

    @staticmethod
    def from_yaml(path: Path) -> BookvoiceConfig:
        """Create a config from a YAML file.

        Note:
            YAML parsing is planned for a future optional dependency.

        Args:
            path: Path to a future YAML config file.

        Returns:
            A placeholder `BookvoiceConfig` instance.
        """

        return BookvoiceConfig(input_pdf=Path("input.pdf"), output_dir=Path("out"))

    @staticmethod
    def from_env(env: Mapping[str, str] | None = None) -> BookvoiceConfig:
        """Create a config from environment variables.

        Args:
            env: Optional environment mapping. If omitted, `os.environ` will be
                used in a future implementation.

        Returns:
            A placeholder `BookvoiceConfig` instance.
        """

        _ = env
        return BookvoiceConfig(input_pdf=Path("input.pdf"), output_dir=Path("out"))
