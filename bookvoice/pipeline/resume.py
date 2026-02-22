"""Resume and manifest helpers for Bookvoice pipeline.

Responsibilities:
- Parse and validate run-manifest payloads.
- Resolve artifact paths for resume mode.
- Detect the next missing stage from persisted artifacts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path

from ..errors import PipelineStageError
from .artifacts import load_audio_parts, load_chunks, load_rewrites, load_translations
from ..parsing import normalize_optional_string, parse_permissive_boolean


@dataclass(frozen=True, slots=True)
class ResumeArtifactStatus:
    """Resolved presence metadata for one resume-critical artifact path."""

    key: str
    path: Path
    exists: bool
    stage: str


@dataclass(frozen=True, slots=True)
class ResumeArtifactConsistencyReport:
    """Resume preflight consistency classification and diagnostics."""

    status: str
    next_stage: str
    issue_count: int
    diagnostics: tuple[str, ...] = field(default_factory=tuple)

    def as_manifest_metadata(self) -> dict[str, str]:
        """Return lightweight debug metadata persisted in resume manifest extras."""

        return {
            "resume_validation_status": self.status,
            "resume_validation_next_stage": self.next_stage,
            "resume_validation_issue_count": str(self.issue_count),
            "resume_validation_diagnostics": " || ".join(self.diagnostics),
        }


def manifest_string(payload: dict[str, object], key: str, default_value: str) -> str:
    """Read a non-empty string from manifest extras with deterministic fallback."""

    value = normalize_optional_string(payload.get(key))
    return value if value is not None else default_value


def manifest_bool(payload: dict[str, object], key: str, default_value: bool) -> bool:
    """Read a boolean value from manifest extras with permissive string parsing."""

    parsed = parse_permissive_boolean(payload.get(key))
    return parsed if parsed is not None else default_value


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
    packaged_path: Path,
    packaging_enabled: bool,
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
    if packaging_enabled and not packaged_path.exists():
        return "package"
    return "done"


def _chunk_signature(chapter_index: int, chunk_index: int, part_id: str | None) -> str:
    """Build stable chunk identity used for cross-artifact consistency checks."""

    part_token = part_id if part_id is not None else "-"
    return f"{chapter_index}:{chunk_index}:{part_token}"


def _critical_artifact_statuses(
    *,
    chapters_path: Path,
    chunks_path: Path,
    translations_path: Path,
    rewrites_path: Path,
    audio_parts_path: Path,
) -> list[ResumeArtifactStatus]:
    """Build deterministic status rows for critical resume artifact chain."""

    return [
        ResumeArtifactStatus(
            key="chapters",
            path=chapters_path,
            exists=chapters_path.exists(),
            stage="split",
        ),
        ResumeArtifactStatus(
            key="chunks",
            path=chunks_path,
            exists=chunks_path.exists(),
            stage="chunk",
        ),
        ResumeArtifactStatus(
            key="translations",
            path=translations_path,
            exists=translations_path.exists(),
            stage="translate",
        ),
        ResumeArtifactStatus(
            key="rewrites",
            path=rewrites_path,
            exists=rewrites_path.exists(),
            stage="rewrite",
        ),
        ResumeArtifactStatus(
            key="audio_parts",
            path=audio_parts_path,
            exists=audio_parts_path.exists(),
            stage="tts",
        ),
    ]


def _validate_chain_topology(statuses: list[ResumeArtifactStatus]) -> tuple[str, ...]:
    """Detect non-recoverable mixed missing/stale artifact chain states."""

    first_missing_index: int | None = None
    for index, status in enumerate(statuses):
        if not status.exists:
            first_missing_index = index
            break
    if first_missing_index is None:
        return tuple()

    stale_downstream = [status for status in statuses[first_missing_index + 1 :] if status.exists]
    if not stale_downstream:
        return tuple()

    missing = statuses[first_missing_index]
    diagnostics = [
        (
            "Mixed resume artifact state: missing "
            f"`{missing.key}` at `{missing.path}` but downstream artifact exists."
        )
    ]
    diagnostics.extend(
        f"Stale downstream artifact `{status.key}` at `{status.path}`."
        for status in stale_downstream
    )
    diagnostics.append(
        "Manual cleanup required: delete stale downstream artifacts and rerun `bookvoice resume`."
    )
    return tuple(diagnostics)


def _validate_payload_alignment(
    *,
    chunks_path: Path,
    translations_path: Path,
    rewrites_path: Path,
    audio_parts_path: Path,
) -> tuple[str, ...]:
    """Detect non-recoverable cross-artifact payload mismatches."""

    diagnostics: list[str] = []

    if chunks_path.exists() and translations_path.exists():
        chunks = load_chunks(chunks_path)
        translations = load_translations(translations_path)
        chunk_signatures = [
            _chunk_signature(item.chapter_index, item.chunk_index, item.part_id)
            for item in chunks
        ]
        translation_signatures = [
            _chunk_signature(
                item.chunk.chapter_index,
                item.chunk.chunk_index,
                item.chunk.part_id,
            )
            for item in translations
        ]
        if chunk_signatures != translation_signatures:
            diagnostics.append(
                "Chunk/translation mismatch between "
                f"`{chunks_path}` and `{translations_path}` (count/order mismatch)."
            )

    if translations_path.exists() and rewrites_path.exists():
        translations = load_translations(translations_path)
        rewrites = load_rewrites(rewrites_path)
        translation_signatures = [
            _chunk_signature(
                item.chunk.chapter_index,
                item.chunk.chunk_index,
                item.chunk.part_id,
            )
            for item in translations
        ]
        rewrite_signatures = [
            _chunk_signature(
                item.translation.chunk.chapter_index,
                item.translation.chunk.chunk_index,
                item.translation.chunk.part_id,
            )
            for item in rewrites
        ]
        if translation_signatures != rewrite_signatures:
            diagnostics.append(
                "Translation/rewrite mismatch between "
                f"`{translations_path}` and `{rewrites_path}` (count/order mismatch)."
            )

    if rewrites_path.exists() and audio_parts_path.exists():
        rewrites = load_rewrites(rewrites_path)
        audio_parts = load_audio_parts(audio_parts_path)
        rewrite_signatures = [
            _chunk_signature(
                item.translation.chunk.chapter_index,
                item.translation.chunk.chunk_index,
                item.translation.chunk.part_id,
            )
            for item in rewrites
        ]
        audio_signatures = [
            _chunk_signature(item.chapter_index, item.chunk_index, item.part_id)
            for item in audio_parts
        ]
        if rewrite_signatures != audio_signatures:
            diagnostics.append(
                "Rewrite/audio mismatch between "
                f"`{rewrites_path}` and `{audio_parts_path}` (count/order mismatch)."
            )

    if diagnostics:
        diagnostics.append(
            "Manual cleanup required: remove mismatched artifacts from the first inconsistent stage "
            "and all downstream stages, then rerun `bookvoice resume`."
        )
    return tuple(diagnostics)


def validate_resume_artifact_consistency(
    *,
    raw_text_path: Path,
    clean_text_path: Path,
    chapters_path: Path,
    chunks_path: Path,
    translations_path: Path,
    rewrites_path: Path,
    audio_parts_path: Path,
    merged_path: Path,
    packaged_path: Path,
    packaging_enabled: bool,
) -> ResumeArtifactConsistencyReport:
    """Validate resume-critical artifact consistency before replay begins."""

    next_stage = detect_next_stage(
        raw_text_path=raw_text_path,
        clean_text_path=clean_text_path,
        chapters_path=chapters_path,
        chunks_path=chunks_path,
        translations_path=translations_path,
        rewrites_path=rewrites_path,
        audio_parts_path=audio_parts_path,
        merged_path=merged_path,
        packaged_path=packaged_path,
        packaging_enabled=packaging_enabled,
    )

    statuses = _critical_artifact_statuses(
        chapters_path=chapters_path,
        chunks_path=chunks_path,
        translations_path=translations_path,
        rewrites_path=rewrites_path,
        audio_parts_path=audio_parts_path,
    )
    chain_diagnostics = _validate_chain_topology(statuses)
    alignment_diagnostics = _validate_payload_alignment(
        chunks_path=chunks_path,
        translations_path=translations_path,
        rewrites_path=rewrites_path,
        audio_parts_path=audio_parts_path,
    )
    diagnostics = chain_diagnostics + alignment_diagnostics
    if diagnostics:
        return ResumeArtifactConsistencyReport(
            status="non_recoverable",
            next_stage=next_stage,
            issue_count=len(diagnostics),
            diagnostics=diagnostics,
        )
    return ResumeArtifactConsistencyReport(
        status="recoverable",
        next_stage=next_stage,
        issue_count=0,
    )


def ensure_recoverable_resume_state(
    report: ResumeArtifactConsistencyReport,
) -> None:
    """Raise actionable resume diagnostics for non-recoverable states."""

    if report.status == "recoverable":
        return
    detail = " | ".join(report.diagnostics)
    raise PipelineStageError(
        stage="resume-validation",
        detail=detail,
        hint=(
            "Resolve artifact inconsistencies manually, then rerun `bookvoice resume`. "
            "See diagnostic paths above."
        ),
    )
