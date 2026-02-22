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
import os
from pathlib import Path
from typing import Any, Mapping

from .parsing import (
    normalize_optional_string,
    parse_permissive_boolean,
    parse_required_boolean,
)


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
        return normalize_optional_string(mapping.get(key))

    @staticmethod
    def _normalize_optional_string(value: object) -> str | None:
        """Normalize optional string values by stripping whitespace and empty values."""

        return normalize_optional_string(value)

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

        return parse_required_boolean(value, field_name)


class ConfigLoader:
    """Factory methods for creating `BookvoiceConfig` from external sources."""

    _REQUIRED_YAML_KEYS = frozenset({"input_pdf", "output_dir"})
    _SUPPORTED_YAML_KEYS = frozenset(
        {
            "input_pdf",
            "output_dir",
            "language",
            "provider_translator",
            "provider_rewriter",
            "provider_tts",
            "model_translate",
            "model_rewrite",
            "model_tts",
            "tts_voice",
            "rewrite_bypass",
            "api_key",
            "chunk_size_chars",
            "chapter_selection",
            "resume",
            "extra",
        }
    )
    _RUNTIME_ENV_KEYS = frozenset(
        {
            "BOOKVOICE_PROVIDER_TRANSLATOR",
            "BOOKVOICE_PROVIDER_REWRITER",
            "BOOKVOICE_PROVIDER_TTS",
            "BOOKVOICE_MODEL_TRANSLATE",
            "BOOKVOICE_MODEL_REWRITE",
            "BOOKVOICE_MODEL_TTS",
            "BOOKVOICE_TTS_VOICE",
            "BOOKVOICE_REWRITE_BYPASS",
            "OPENAI_API_KEY",
        }
    )

    @staticmethod
    def from_yaml(path: Path) -> BookvoiceConfig:
        """Create a validated config from a YAML file."""

        path_text = path.read_text(encoding="utf-8")
        payload = ConfigLoader._parse_yaml_payload(path_text, path)

        return ConfigLoader._build_config_from_mapping(payload, source_label=f"YAML `{path}`")

    @staticmethod
    def from_env(env: Mapping[str, str] | None = None) -> BookvoiceConfig:
        """Create a validated config from environment variables."""

        env_map: Mapping[str, str] = os.environ if env is None else env

        input_pdf = ConfigLoader._required_env_path(env_map, "BOOKVOICE_INPUT_PDF")
        output_dir = ConfigLoader._optional_env_path(env_map, "BOOKVOICE_OUTPUT_DIR") or Path("out")
        language = ConfigLoader._optional_env_string(env_map, "BOOKVOICE_LANGUAGE") or "cs"
        chunk_size = ConfigLoader._optional_env_positive_int(
            env_map, "BOOKVOICE_CHUNK_SIZE_CHARS"
        ) or 1800
        chapter_selection = ConfigLoader._optional_env_string(
            env_map, "BOOKVOICE_CHAPTER_SELECTION"
        )
        resume = ConfigLoader._optional_env_boolean(env_map, "BOOKVOICE_RESUME") or False
        provider_translator = (
            ConfigLoader._optional_env_string(env_map, "BOOKVOICE_PROVIDER_TRANSLATOR")
            or "openai"
        )
        provider_rewriter = (
            ConfigLoader._optional_env_string(env_map, "BOOKVOICE_PROVIDER_REWRITER") or "openai"
        )
        provider_tts = (
            ConfigLoader._optional_env_string(env_map, "BOOKVOICE_PROVIDER_TTS") or "openai"
        )
        model_translate = (
            ConfigLoader._optional_env_string(env_map, "BOOKVOICE_MODEL_TRANSLATE")
            or _DEFAULT_TRANSLATION_MODEL
        )
        model_rewrite = (
            ConfigLoader._optional_env_string(env_map, "BOOKVOICE_MODEL_REWRITE")
            or _DEFAULT_REWRITE_MODEL
        )
        model_tts = (
            ConfigLoader._optional_env_string(env_map, "BOOKVOICE_MODEL_TTS")
            or _DEFAULT_TTS_MODEL
        )
        tts_voice = (
            ConfigLoader._optional_env_string(env_map, "BOOKVOICE_TTS_VOICE")
            or _DEFAULT_TTS_VOICE
        )
        rewrite_bypass = (
            ConfigLoader._optional_env_boolean(env_map, "BOOKVOICE_REWRITE_BYPASS") or False
        )
        api_key = ConfigLoader._optional_env_string(env_map, "OPENAI_API_KEY")

        runtime_env = {
            key: value
            for key, value in env_map.items()
            if key in ConfigLoader._RUNTIME_ENV_KEYS
            and normalize_optional_string(value) is not None
        }

        config = BookvoiceConfig(
            input_pdf=input_pdf,
            output_dir=output_dir,
            language=language,
            provider_translator=provider_translator,
            provider_rewriter=provider_rewriter,
            provider_tts=provider_tts,
            model_translate=model_translate,
            model_rewrite=model_rewrite,
            model_tts=model_tts,
            tts_voice=tts_voice,
            rewrite_bypass=rewrite_bypass,
            api_key=api_key,
            chunk_size_chars=chunk_size,
            chapter_selection=chapter_selection,
            resume=resume,
            runtime_sources=RuntimeConfigSources(env=runtime_env),
        )
        config.validate()
        return config

    @staticmethod
    def _parse_yaml_payload(raw_text: str, path: Path) -> Mapping[str, Any]:
        """Parse YAML text and enforce a mapping root payload."""

        try:
            import yaml
            payload = yaml.safe_load(raw_text)
        except ImportError:
            payload = ConfigLoader._parse_simple_yaml_mapping(raw_text, path)

        if payload is None:
            payload = {}
        if not isinstance(payload, Mapping):
            raise ValueError(f"YAML config `{path}` must contain a top-level mapping/object.")
        return payload

    @staticmethod
    def _build_config_from_mapping(payload: Mapping[str, Any], source_label: str) -> BookvoiceConfig:
        """Build a validated config from a normalized mapping payload."""

        ConfigLoader._validate_yaml_keys(payload, source_label)

        input_pdf = ConfigLoader._required_path(payload, "input_pdf", source_label)
        output_dir = ConfigLoader._required_path(payload, "output_dir", source_label)
        language = ConfigLoader._optional_non_empty_string(payload, "language", source_label) or "cs"
        provider_translator = (
            ConfigLoader._optional_non_empty_string(payload, "provider_translator", source_label)
            or "openai"
        )
        provider_rewriter = (
            ConfigLoader._optional_non_empty_string(payload, "provider_rewriter", source_label)
            or "openai"
        )
        provider_tts = (
            ConfigLoader._optional_non_empty_string(payload, "provider_tts", source_label)
            or "openai"
        )
        model_translate = (
            ConfigLoader._optional_non_empty_string(payload, "model_translate", source_label)
            or _DEFAULT_TRANSLATION_MODEL
        )
        model_rewrite = (
            ConfigLoader._optional_non_empty_string(payload, "model_rewrite", source_label)
            or _DEFAULT_REWRITE_MODEL
        )
        model_tts = (
            ConfigLoader._optional_non_empty_string(payload, "model_tts", source_label)
            or _DEFAULT_TTS_MODEL
        )
        tts_voice = (
            ConfigLoader._optional_non_empty_string(payload, "tts_voice", source_label)
            or _DEFAULT_TTS_VOICE
        )
        rewrite_bypass = ConfigLoader._optional_boolean(
            payload,
            "rewrite_bypass",
            source_label,
            default=False,
        )
        api_key = ConfigLoader._optional_non_empty_string(payload, "api_key", source_label)
        chunk_size = ConfigLoader._optional_positive_int(
            payload,
            "chunk_size_chars",
            source_label,
            default=1800,
        )
        chapter_selection = ConfigLoader._optional_non_empty_string(
            payload, "chapter_selection", source_label
        )
        resume = ConfigLoader._optional_boolean(
            payload,
            "resume",
            source_label,
            default=False,
        )
        extra = ConfigLoader._optional_string_map(payload, "extra", source_label)

        config = BookvoiceConfig(
            input_pdf=input_pdf,
            output_dir=output_dir,
            language=language,
            provider_translator=provider_translator,
            provider_rewriter=provider_rewriter,
            provider_tts=provider_tts,
            model_translate=model_translate,
            model_rewrite=model_rewrite,
            model_tts=model_tts,
            tts_voice=tts_voice,
            rewrite_bypass=rewrite_bypass,
            api_key=api_key,
            chunk_size_chars=chunk_size,
            chapter_selection=chapter_selection,
            resume=resume,
            extra=extra,
        )
        config.validate()
        return config

    @staticmethod
    def _validate_yaml_keys(payload: Mapping[str, Any], source_label: str) -> None:
        """Validate supported and required YAML keys."""

        unknown = sorted(set(payload).difference(ConfigLoader._SUPPORTED_YAML_KEYS))
        if unknown:
            key_list = ", ".join(unknown)
            raise ValueError(f"{source_label} includes unsupported key(s): {key_list}.")

        missing = sorted(
            key for key in ConfigLoader._REQUIRED_YAML_KEYS if key not in payload
        )
        if missing:
            key_list = ", ".join(missing)
            raise ValueError(f"{source_label} is missing required key(s): {key_list}.")

    @staticmethod
    def _required_path(payload: Mapping[str, Any], key: str, source_label: str) -> Path:
        """Read a required non-empty path-like field from a payload."""

        value = ConfigLoader._optional_non_empty_string(payload, key, source_label)
        if value is None:
            raise ValueError(f"{source_label} requires non-empty `{key}`.")
        return Path(value)

    @staticmethod
    def _optional_non_empty_string(
        payload: Mapping[str, Any], key: str, source_label: str
    ) -> str | None:
        """Read an optional string field and normalize blank values to `None`."""

        if key not in payload:
            return None
        value = normalize_optional_string(payload[key])
        if value is None:
            return None
        return value

    @staticmethod
    def _optional_positive_int(
        payload: Mapping[str, Any], key: str, source_label: str, default: int
    ) -> int:
        """Read and validate a positive integer payload field."""

        if key not in payload:
            return default

        raw_value = payload[key]
        if isinstance(raw_value, bool):
            raise ValueError(f"{source_label} field `{key}` must be a positive integer.")
        if isinstance(raw_value, int):
            parsed = raw_value
        else:
            normalized = normalize_optional_string(raw_value)
            if normalized is None:
                return default
            try:
                parsed = int(normalized)
            except ValueError as exc:
                raise ValueError(
                    f"{source_label} field `{key}` must be a positive integer."
                ) from exc

        if parsed <= 0:
            raise ValueError(f"{source_label} field `{key}` must be a positive integer.")
        return parsed

    @staticmethod
    def _optional_boolean(
        payload: Mapping[str, Any], key: str, source_label: str, default: bool
    ) -> bool:
        """Read and validate a boolean field from a payload."""

        if key not in payload:
            return default

        raw_value = payload[key]
        parsed = parse_permissive_boolean(raw_value)
        if parsed is None:
            raise ValueError(
                f"{source_label} field `{key}` must be a boolean value "
                "(`true`/`false`, `1`/`0`, `yes`/`no`)."
            )
        return parsed

    @staticmethod
    def _optional_string_map(
        payload: Mapping[str, Any], key: str, source_label: str
    ) -> dict[str, str]:
        """Read an optional mapping with non-empty string keys and values."""

        if key not in payload:
            return {}

        raw = payload[key]
        if raw is None:
            return {}
        if not isinstance(raw, Mapping):
            raise ValueError(f"{source_label} field `{key}` must be a mapping/object.")

        normalized: dict[str, str] = {}
        for raw_key, raw_value in raw.items():
            key_value = normalize_optional_string(raw_key)
            value_value = normalize_optional_string(raw_value)
            if key_value is None:
                raise ValueError(f"{source_label} field `{key}` contains a blank key.")
            if value_value is None:
                raise ValueError(
                    f"{source_label} field `{key}` contains blank value for `{key_value}`."
                )
            normalized[key_value] = value_value
        return normalized

    @staticmethod
    def _required_env_path(env: Mapping[str, str], key: str) -> Path:
        """Read a required non-empty path value from environment mapping."""

        value = ConfigLoader._optional_env_string(env, key)
        if value is None:
            raise ValueError(f"Environment variable `{key}` is required.")
        return Path(value)

    @staticmethod
    def _optional_env_path(env: Mapping[str, str], key: str) -> Path | None:
        """Read an optional path value from environment mapping."""

        value = ConfigLoader._optional_env_string(env, key)
        if value is None:
            return None
        return Path(value)

    @staticmethod
    def _optional_env_string(env: Mapping[str, str], key: str) -> str | None:
        """Read and normalize optional string environment variable values."""

        if key not in env:
            return None
        return normalize_optional_string(env.get(key))

    @staticmethod
    def _optional_env_positive_int(env: Mapping[str, str], key: str) -> int | None:
        """Read an optional positive integer from environment mapping."""

        raw_value = ConfigLoader._optional_env_string(env, key)
        if raw_value is None:
            return None
        try:
            parsed = int(raw_value)
        except ValueError as exc:
            raise ValueError(f"Environment variable `{key}` must be a positive integer.") from exc
        if parsed <= 0:
            raise ValueError(f"Environment variable `{key}` must be a positive integer.")
        return parsed

    @staticmethod
    def _optional_env_boolean(env: Mapping[str, str], key: str) -> bool | None:
        """Read an optional boolean from environment mapping."""

        if key not in env:
            return None
        raw_value = env.get(key)
        parsed = parse_permissive_boolean(raw_value)
        if parsed is None:
            raise ValueError(
                f"Environment variable `{key}` must be a boolean value "
                "(`true`/`false`, `1`/`0`, `yes`/`no`)."
            )
        return parsed

    @staticmethod
    def _parse_simple_yaml_mapping(raw_text: str, path: Path) -> Mapping[str, Any]:
        """Parse a strict YAML subset supporting mappings, scalars, and one-line comments."""

        lines = raw_text.splitlines()
        parsed, next_index = ConfigLoader._parse_simple_yaml_block(
            lines=lines, start_index=0, expected_indent=0, path=path
        )
        trailing_non_empty = any(
            normalize_optional_string(line) is not None for line in lines[next_index:]
        )
        if trailing_non_empty:
            raise ValueError(f"YAML config `{path}` contains invalid trailing content.")
        return parsed

    @staticmethod
    def _parse_simple_yaml_block(
        lines: list[str], start_index: int, expected_indent: int, path: Path
    ) -> tuple[dict[str, Any], int]:
        """Parse one indentation block of a minimal YAML mapping."""

        payload: dict[str, Any] = {}
        index = start_index
        while index < len(lines):
            raw_line = lines[index]
            stripped = raw_line.strip()
            if not stripped or stripped.startswith("#"):
                index += 1
                continue

            indent = len(raw_line) - len(raw_line.lstrip(" "))
            if indent < expected_indent:
                break
            if indent > expected_indent:
                raise ValueError(
                    f"YAML config `{path}` has invalid indentation on line {index + 1}."
                )

            line = raw_line[expected_indent:]
            if ":" not in line:
                raise ValueError(
                    f"YAML config `{path}` has invalid mapping entry on line {index + 1}."
                )
            key_part, value_part = line.split(":", 1)
            key = normalize_optional_string(key_part)
            if key is None:
                raise ValueError(f"YAML config `{path}` has blank key on line {index + 1}.")
            value_text = value_part.strip()
            if not value_text:
                child_payload, child_index = ConfigLoader._parse_simple_yaml_block(
                    lines=lines,
                    start_index=index + 1,
                    expected_indent=expected_indent + 2,
                    path=path,
                )
                if not child_payload:
                    raise ValueError(
                        f"YAML config `{path}` key `{key}` must define a non-empty mapping."
                    )
                payload[key] = child_payload
                index = child_index
                continue

            payload[key] = ConfigLoader._parse_simple_yaml_scalar(value_text)
            index += 1

        return payload, index

    @staticmethod
    def _parse_simple_yaml_scalar(value: str) -> Any:
        """Parse scalar values from the supported YAML subset."""

        if value.startswith('"') and value.endswith('"') and len(value) >= 2:
            return value[1:-1]
        if value.startswith("'") and value.endswith("'") and len(value) >= 2:
            return value[1:-1]

        normalized = value.strip()
        lower = normalized.lower()
        if lower == "true":
            return True
        if lower == "false":
            return False

        if normalized.startswith(("+", "-")):
            digit_part = normalized[1:]
        else:
            digit_part = normalized
        if digit_part.isdigit():
            return int(normalized)

        return normalized
