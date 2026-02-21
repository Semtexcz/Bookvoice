"""Configuration model and loaders for Bookvoice.

Responsibilities:
- Define runtime configuration as a typed dataclass.
- Provide deterministic precedence resolution for runtime provider/model settings.
- Provide loader entry points for file- and environment-based configuration.

Key types:
- `BookvoiceConfig`: normalized runtime settings for a pipeline run.
- `ProviderRuntimeConfig`: resolved provider/model runtime values.
- `RuntimeConfigSources`: optional value sources for precedence resolution.
- `ConfigLoader`: static construction helpers for `BookvoiceConfig`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping


_DEFAULT_TRANSLATION_MODEL = "gpt-4.1-mini"
_DEFAULT_REWRITE_MODEL = "gpt-4.1-mini"
_DEFAULT_TTS_MODEL = "gpt-4o-mini-tts"
_DEFAULT_TTS_VOICE = "echo"
_SUPPORTED_PROVIDER_IDS = frozenset({"openai"})


@dataclass(frozen=True, slots=True)
class RuntimeConfigSources:
    """Source mappings used for deterministic runtime value precedence.

    Attributes:
        cli: Values explicitly provided by CLI arguments.
        secure: Values loaded from secure local credential storage.
        env: Values loaded from environment variables.
    """

    cli: Mapping[str, str] = field(default_factory=dict)
    secure: Mapping[str, str] = field(default_factory=dict)
    env: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ProviderRuntimeConfig:
    """Resolved runtime provider and model identifiers for one run.

    Attributes:
        translator_provider: Provider identifier for translation stage.
        rewriter_provider: Provider identifier for rewrite stage.
        tts_provider: Provider identifier for TTS stage.
        translate_model: Model identifier for translation stage.
        rewrite_model: Model identifier for rewrite stage.
        tts_model: Model identifier for TTS stage.
        tts_voice: Voice identifier for TTS stage.
        rewrite_bypass: Whether rewrite stage should run deterministic pass-through mode.
        api_key: Optional provider API key (resolved but not persisted in artifacts).
    """

    translator_provider: str
    rewriter_provider: str
    tts_provider: str
    translate_model: str
    rewrite_model: str
    tts_model: str
    tts_voice: str
    rewrite_bypass: bool = False
    api_key: str | None = None

    def as_manifest_metadata(self) -> dict[str, str]:
        """Return non-secret runtime metadata safe to persist in artifacts/manifest."""

        return {
            "provider_translator": self.translator_provider,
            "provider_rewriter": self.rewriter_provider,
            "provider_tts": self.tts_provider,
            "model_translate": self.translate_model,
            "model_rewrite": self.rewrite_model,
            "model_tts": self.tts_model,
            "tts_voice": self.tts_voice,
            "rewrite_bypass": "true" if self.rewrite_bypass else "false",
        }


@dataclass(slots=True)
class BookvoiceConfig:
    """Runtime configuration for one pipeline run.

    Attributes:
        input_pdf: Path to the source PDF.
        output_dir: Output directory for generated artifacts.
        language: Target language code, defaulting to Czech (`cs`).
        provider_translator: Translator provider identifier.
        provider_rewriter: Rewrite provider identifier.
        provider_tts: TTS provider identifier.
        model_translate: Translation model identifier.
        model_rewrite: Rewrite model identifier.
        model_tts: TTS model identifier.
        tts_voice: TTS voice identifier.
        rewrite_bypass: Explicit rewrite bypass mode using deterministic pass-through output.
        api_key: Optional API key for provider calls.
        chunk_size_chars: Target chunk size in characters.
        chapter_selection: Optional 1-based chapter selection expression.
        resume: Whether pipeline should attempt to resume from artifacts.
        runtime_sources: Optional runtime source overrides injected by CLI.
        extra: Additional metadata for future extensions.
    """

    input_pdf: Path
    output_dir: Path
    language: str = "cs"
    provider_translator: str = "openai"
    provider_rewriter: str = "openai"
    provider_tts: str = "openai"
    model_translate: str = _DEFAULT_TRANSLATION_MODEL
    model_rewrite: str = _DEFAULT_REWRITE_MODEL
    model_tts: str = _DEFAULT_TTS_MODEL
    tts_voice: str = _DEFAULT_TTS_VOICE
    rewrite_bypass: bool = False
    api_key: str | None = None
    chunk_size_chars: int = 1800
    chapter_selection: str | None = None
    resume: bool = False
    runtime_sources: RuntimeConfigSources = field(default_factory=RuntimeConfigSources)
    extra: dict[str, str] = field(default_factory=dict)

    def validate(self) -> None:
        """Validate runtime configuration values before pipeline execution."""

        self._validate_provider_id(self.provider_translator, "provider_translator")
        self._validate_provider_id(self.provider_rewriter, "provider_rewriter")
        self._validate_provider_id(self.provider_tts, "provider_tts")
        self._require_non_empty(self.model_translate, "model_translate")
        self._require_non_empty(self.model_rewrite, "model_rewrite")
        self._require_non_empty(self.model_tts, "model_tts")
        self._require_non_empty(self.tts_voice, "tts_voice")
        if self.chunk_size_chars <= 0:
            raise ValueError("`chunk_size_chars` must be a positive integer.")

    def resolved_provider_runtime(
        self, sources: RuntimeConfigSources | None = None
    ) -> ProviderRuntimeConfig:
        """Resolve provider and model settings with deterministic source precedence.

        Precedence for each key is:
        `cli` > `secure` > `env` > config field default.
        """

        resolved_sources = sources if sources is not None else RuntimeConfigSources()

        translator_provider = self._resolve_runtime_value(
            key="provider_translator",
            env_key="BOOKVOICE_PROVIDER_TRANSLATOR",
            default_value=self.provider_translator,
            sources=resolved_sources,
        )
        rewriter_provider = self._resolve_runtime_value(
            key="provider_rewriter",
            env_key="BOOKVOICE_PROVIDER_REWRITER",
            default_value=self.provider_rewriter,
            sources=resolved_sources,
        )
        tts_provider = self._resolve_runtime_value(
            key="provider_tts",
            env_key="BOOKVOICE_PROVIDER_TTS",
            default_value=self.provider_tts,
            sources=resolved_sources,
        )
        translate_model = self._resolve_runtime_value(
            key="model_translate",
            env_key="BOOKVOICE_MODEL_TRANSLATE",
            default_value=self.model_translate,
            sources=resolved_sources,
        )
        rewrite_model = self._resolve_runtime_value(
            key="model_rewrite",
            env_key="BOOKVOICE_MODEL_REWRITE",
            default_value=self.model_rewrite,
            sources=resolved_sources,
        )
        tts_model = self._resolve_runtime_value(
            key="model_tts",
            env_key="BOOKVOICE_MODEL_TTS",
            default_value=self.model_tts,
            sources=resolved_sources,
        )
        tts_voice = self._resolve_runtime_value(
            key="tts_voice",
            env_key="BOOKVOICE_TTS_VOICE",
            default_value=self.tts_voice,
            sources=resolved_sources,
        )
        rewrite_bypass = self._resolve_runtime_bool(
            key="rewrite_bypass",
            env_key="BOOKVOICE_REWRITE_BYPASS",
            default_value=self.rewrite_bypass,
            sources=resolved_sources,
        )
        api_key = self._resolve_optional_runtime_value(
            key="api_key",
            env_key="OPENAI_API_KEY",
            default_value=self.api_key,
            sources=resolved_sources,
        )

        resolved = ProviderRuntimeConfig(
            translator_provider=translator_provider,
            rewriter_provider=rewriter_provider,
            tts_provider=tts_provider,
            translate_model=translate_model,
            rewrite_model=rewrite_model,
            tts_model=tts_model,
            tts_voice=tts_voice,
            rewrite_bypass=rewrite_bypass,
            api_key=api_key,
        )
        self._validate_provider_id(resolved.translator_provider, "provider_translator")
        self._validate_provider_id(resolved.rewriter_provider, "provider_rewriter")
        self._validate_provider_id(resolved.tts_provider, "provider_tts")
        self._require_non_empty(resolved.translate_model, "model_translate")
        self._require_non_empty(resolved.rewrite_model, "model_rewrite")
        self._require_non_empty(resolved.tts_model, "model_tts")
        self._require_non_empty(resolved.tts_voice, "tts_voice")
        return resolved

    def _resolve_runtime_value(
        self,
        key: str,
        env_key: str,
        default_value: str | None,
        sources: RuntimeConfigSources,
    ) -> str:
        """Resolve a runtime value from sources in deterministic precedence order."""

        cli_value = self._normalized_lookup(sources.cli, key)
        if cli_value is not None:
            return cli_value

        secure_value = self._normalized_lookup(sources.secure, key)
        if secure_value is not None:
            return secure_value

        env_value = self._normalized_lookup(sources.env, env_key)
        if env_value is not None:
            return env_value

        normalized_default = self._normalize_optional_string(default_value)
        if normalized_default is None:
            raise ValueError(
                f"`{key}` could not be resolved from CLI, secure storage, env, or defaults."
            )
        return normalized_default

    def _resolve_optional_runtime_value(
        self,
        key: str,
        env_key: str,
        default_value: str | None,
        sources: RuntimeConfigSources,
    ) -> str | None:
        """Resolve an optional runtime value from sources in deterministic order."""

        cli_value = self._normalized_lookup(sources.cli, key)
        if cli_value is not None:
            return cli_value

        secure_value = self._normalized_lookup(sources.secure, key)
        if secure_value is not None:
            return secure_value

        env_value = self._normalized_lookup(sources.env, env_key)
        if env_value is not None:
            return env_value

        return self._normalize_optional_string(default_value)

    def _resolve_runtime_bool(
        self,
        key: str,
        env_key: str,
        default_value: bool,
        sources: RuntimeConfigSources,
    ) -> bool:
        """Resolve a boolean runtime value from sources in deterministic precedence order."""

        cli_value = self._normalized_lookup(sources.cli, key)
        if cli_value is not None:
            return self._parse_boolean_value(cli_value, key)

        secure_value = self._normalized_lookup(sources.secure, key)
        if secure_value is not None:
            return self._parse_boolean_value(secure_value, key)

        env_value = self._normalized_lookup(sources.env, env_key)
        if env_value is not None:
            return self._parse_boolean_value(env_value, key)

        return bool(default_value)

    @staticmethod
    def _normalized_lookup(mapping: Mapping[str, str], key: str) -> str | None:
        """Return a stripped mapping value for a key or `None` when missing/blank."""

        if key not in mapping:
            return None
        return BookvoiceConfig._normalize_optional_string(mapping.get(key))

    @staticmethod
    def _normalize_optional_string(value: object) -> str | None:
        """Normalize optional string values by stripping whitespace and empty values."""

        if value is None:
            return None
        text = str(value).strip()
        if not text:
            return None
        return text

    @staticmethod
    def _validate_provider_id(provider_id: str, field_name: str) -> None:
        """Validate provider identifiers against currently supported providers."""

        if provider_id not in _SUPPORTED_PROVIDER_IDS:
            supported = ", ".join(sorted(_SUPPORTED_PROVIDER_IDS))
            raise ValueError(
                f"Unsupported `{field_name}` value `{provider_id}`; supported: {supported}."
            )

    @staticmethod
    def _require_non_empty(value: str, field_name: str) -> None:
        """Validate that runtime string fields are not empty."""

        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"`{field_name}` must be a non-empty string.")

    @staticmethod
    def _parse_boolean_value(value: str, field_name: str) -> bool:
        """Parse a runtime boolean value from canonical textual forms."""

        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
        raise ValueError(
            f"`{field_name}` must be a boolean value (`true`/`false`, `1`/`0`, `yes`/`no`)."
        )


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

        _ = path
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
