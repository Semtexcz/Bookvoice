"""Runtime configuration and run-identity helpers for Bookvoice pipeline.

Responsibilities:
- Validate pipeline configuration before execution.
- Resolve provider runtime values with precedence rules.
- Compute deterministic configuration hashes and run identifiers.
"""

from __future__ import annotations

from hashlib import sha256
import json
import os

from ..config import BookvoiceConfig, ProviderRuntimeConfig, RuntimeConfigSources
from ..errors import PipelineStageError
from ..io.storage import ArtifactStore


class PipelineRuntimeMixin:
    """Provide runtime/config helper methods for pipeline orchestration."""

    def _prepare_run(self, config: BookvoiceConfig) -> tuple[str, str, ArtifactStore]:
        """Create deterministic run identifiers and artifact storage for a config."""

        self._validate_config(config)
        config_hash = self._config_hash(config)
        run_id = f"run-{config_hash[:12]}"
        store = ArtifactStore(config.output_dir / run_id)
        return run_id, config_hash, store

    def _validate_config(self, config: BookvoiceConfig) -> None:
        """Validate top-level configuration and map failures to stage-aware error."""

        try:
            config.validate()
        except ValueError as exc:
            raise PipelineStageError(
                stage="config",
                detail=str(exc),
                hint="Update provider/model options and rerun the command.",
            ) from exc

    def _resolve_runtime_config(self, config: BookvoiceConfig) -> ProviderRuntimeConfig:
        """Resolve runtime provider settings with deterministic source precedence."""

        try:
            env_source = config.runtime_sources.env or os.environ
            runtime_sources = RuntimeConfigSources(
                cli=config.runtime_sources.cli,
                secure=config.runtime_sources.secure,
                env=env_source,
            )
            return config.resolved_provider_runtime(runtime_sources)
        except ValueError as exc:
            raise PipelineStageError(
                stage="config",
                detail=str(exc),
                hint=(
                    "Set supported provider IDs and non-empty model/voice values in "
                    "CLI, secure storage, environment, or config defaults."
                ),
            ) from exc

    def _config_hash(self, config: BookvoiceConfig) -> str:
        """Compute deterministic hash for run-defining configuration fields."""

        payload = {
            "input_pdf": str(config.input_pdf),
            "output_dir": str(config.output_dir),
            "language": config.language,
            "provider_translator": config.provider_translator,
            "provider_rewriter": config.provider_rewriter,
            "provider_tts": config.provider_tts,
            "model_translate": config.model_translate,
            "model_rewrite": config.model_rewrite,
            "model_tts": config.model_tts,
            "tts_voice": config.tts_voice,
            "rewrite_bypass": config.rewrite_bypass,
            "chunk_size_chars": config.chunk_size_chars,
            "chapter_selection": config.chapter_selection,
            "resume": config.resume,
            "extra": dict(config.extra),
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return sha256(canonical.encode("utf-8")).hexdigest()
