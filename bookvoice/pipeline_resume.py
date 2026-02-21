"""Resume and manifest helpers for Bookvoice pipeline.

Responsibilities:
- Parse and validate run-manifest payloads.
- Resolve artifact paths for resume mode.
- Detect the next missing stage from persisted artifacts.
"""

from __future__ import annotations

import json
from pathlib import Path

from .errors import PipelineStageError


def manifest_string(payload: dict[str, object], key: str, default_value: str) -> str:
    """Read a non-empty string from manifest extras with deterministic fallback."""

    value = payload.get(key)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return default_value


def manifest_bool(payload: dict[str, object], key: str, default_value: bool) -> bool:
    """Read a boolean value from manifest extras with permissive string parsing."""

    value = payload.get(key)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    return default_value


def load_manifest_payload(manifest_path: Path) -> dict[str, object]:
    """Load and validate the resume manifest payload."""

    if not manifest_path.exists():
        raise PipelineStageError(
            stage="resume-manifest",
            detail=f"Manifest file not found: {manifest_path}",
            hint="Run `bookvoice build` first or pass a valid run manifest path.",
        )
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PipelineStageError(
            stage="resume-manifest",
            detail=f"Manifest is not valid JSON: {manifest_path}",
            hint="Regenerate the manifest by running `bookvoice build`.",
        ) from exc
    if not isinstance(payload, dict):
        raise PipelineStageError(
            stage="resume-manifest",
            detail=f"Manifest root must be a JSON object: {manifest_path}",
            hint="Regenerate the manifest by running `bookvoice build`.",
        )
    return payload


def require_manifest_field(
    payload: dict[str, object], key: str, scope: str = "manifest"
) -> str:
    """Require a non-empty string field from a manifest object."""

    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise PipelineStageError(
            stage="resume-manifest",
            detail=f"Manifest is missing required `{scope}.{key}` field.",
            hint="Regenerate the manifest by running `bookvoice build`.",
        )
    return value


def resolve_run_root(manifest_path: Path, extra: dict[str, object]) -> Path:
    """Resolve run root directory from manifest metadata."""

    raw = extra.get("run_root")
    if isinstance(raw, str) and raw.strip():
        candidate = Path(raw)
        if candidate.is_absolute():
            return candidate
        anchored = manifest_path.parent / candidate
        if anchored.exists():
            return anchored
        return candidate
    return manifest_path.parent


def resolve_merged_path(
    manifest_path: Path, run_root: Path, payload: dict[str, object]
) -> Path:
    """Resolve merged audio path from manifest payload."""

    raw = payload.get("merged_audio_path")
    if isinstance(raw, str) and raw.strip():
        path = Path(raw)
        if path.is_absolute():
            return path
        anchored = manifest_path.parent / path
        if anchored.exists():
            return anchored
        return path
    return run_root / "audio/bookvoice_merged.wav"


def resolve_artifact_path(
    manifest_path: Path,
    run_root: Path,
    extra: dict[str, object],
    key: str,
    default_relative: Path,
) -> Path:
    """Resolve an artifact path from resume metadata with fallback."""

    raw = extra.get(key)
    if isinstance(raw, str) and raw.strip():
        path = Path(raw)
        if path.is_absolute():
            return path
        anchored = manifest_path.parent / path
        if anchored.exists():
            return anchored
        return path
    return run_root / default_relative


def detect_next_stage(
    *,
    raw_text_path: Path,
    clean_text_path: Path,
    chapters_path: Path,
    chunks_path: Path,
    translations_path: Path,
    rewrites_path: Path,
    audio_parts_path: Path,
    merged_path: Path,
) -> str:
    """Detect the first missing artifact stage for resume messaging."""

    if not raw_text_path.exists():
        return "extract"
    if not clean_text_path.exists():
        return "clean"
    if not chapters_path.exists():
        return "split"
    if not chunks_path.exists():
        return "chunk"
    if not translations_path.exists():
        return "translate"
    if not rewrites_path.exists():
        return "rewrite"
    if not audio_parts_path.exists():
        return "tts"
    if not merged_path.exists():
        return "merge"
    return "done"
