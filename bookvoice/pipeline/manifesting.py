"""Manifest-writing helpers for Bookvoice pipeline.

Responsibilities:
- Build the typed `RunManifest` record for a completed run.
- Persist manifest payload to deterministic artifact path.
- Map unexpected failures to stage-aware manifest errors.
"""

from __future__ import annotations

from pathlib import Path

from ..config import BookvoiceConfig
from ..errors import PipelineStageError
from ..io.storage import ArtifactStore
from ..models.datatypes import BookMeta, RunManifest
from .artifacts import manifest_payload


class PipelineManifestMixin:
    """Provide run-manifest serialization and persistence helpers."""

    def _write_manifest(
        self,
        config: BookvoiceConfig,
        run_id: str,
        config_hash: str,
        merged_audio_path: Path,
        artifact_paths: dict[str, str],
        cost_summary: dict[str, float],
        store: ArtifactStore,
    ) -> RunManifest:
        """Build and persist a run manifest with deterministic identifiers."""

        try:
            meta = BookMeta(
                source_pdf=config.input_pdf,
                title=config.input_pdf.stem,
                author=None,
                language=config.language,
            )
            manifest = RunManifest(
                run_id=run_id,
                config_hash=config_hash,
                book=meta,
                merged_audio_path=merged_audio_path,
                total_llm_cost_usd=cost_summary["llm_cost_usd"],
                total_tts_cost_usd=cost_summary["tts_cost_usd"],
                total_cost_usd=cost_summary["total_cost_usd"],
                extra=artifact_paths,
            )
            manifest_path = store.save_json(Path("run_manifest.json"), manifest_payload(manifest))
            return RunManifest(
                run_id=manifest.run_id,
                config_hash=manifest.config_hash,
                book=manifest.book,
                merged_audio_path=manifest.merged_audio_path,
                total_llm_cost_usd=manifest.total_llm_cost_usd,
                total_tts_cost_usd=manifest.total_tts_cost_usd,
                total_cost_usd=manifest.total_cost_usd,
                extra={**manifest.extra, "manifest_path": str(manifest_path)},
            )
        except PipelineStageError:
            raise
        except Exception as exc:
            raise PipelineStageError(
                stage="manifest",
                detail=f"Failed to write run manifest: {exc}",
                hint="Verify output directory is writable.",
            ) from exc
