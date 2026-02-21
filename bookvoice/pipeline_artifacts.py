"""Artifact serialization and loading helpers for Bookvoice pipeline.

Responsibilities:
- Build deterministic JSON payloads persisted by pipeline stages.
- Load artifact JSON payloads into typed dataclass structures.
- Provide manifest payload serialization helpers.
"""

from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path

from .config import ProviderRuntimeConfig
from .errors import PipelineStageError
from .models.datatypes import (
    AudioPart,
    Chapter,
    ChapterStructureUnit,
    Chunk,
    RewriteResult,
    RunManifest,
    TranslationResult,
)


def chapter_artifact_payload(
    chapters: list[Chapter],
    source: str,
    fallback_reason: str,
    chapter_scope: dict[str, str],
    normalized_structure: list[ChapterStructureUnit],
) -> dict[str, object]:
    """Serialize chapter artifacts with extraction metadata."""

    return {
        "chapters": [asdict(chapter) for chapter in chapters],
        "metadata": {
            "source": source,
            "fallback_reason": fallback_reason,
            "chapter_scope": chapter_scope,
            "normalized_structure": [asdict(unit) for unit in normalized_structure],
        },
    }


def chunk_artifact_payload(
    chunks: list[Chunk],
    chapter_scope: dict[str, str],
    planner_metadata: dict[str, object],
) -> dict[str, object]:
    """Build chunk artifact payload with chapter scope and planner metadata."""

    return {
        "chunks": [asdict(chunk) for chunk in chunks],
        "metadata": {
            "chapter_scope": chapter_scope,
            **planner_metadata,
        },
    }


def rewrite_artifact_metadata(
    rewrites: list[RewriteResult],
    runtime_config: ProviderRuntimeConfig,
) -> dict[str, str]:
    """Build rewrite artifact metadata reflecting actual rewrite mode/provider."""

    if rewrites:
        provider = rewrites[0].provider
        model = rewrites[0].model
    elif runtime_config.rewrite_bypass:
        provider = "bypass"
        model = "deterministic-pass-through-v1"
    else:
        provider = runtime_config.rewriter_provider
        model = runtime_config.rewrite_model
    return {
        "provider": provider,
        "model": model,
        "rewrite_bypass": "true" if runtime_config.rewrite_bypass else "false",
    }


def audio_parts_artifact_payload(
    audio_parts: list[AudioPart],
    chapter_scope: dict[str, str],
    runtime_config: ProviderRuntimeConfig,
) -> dict[str, object]:
    """Build deterministic audio-parts artifact payload with provider metadata."""

    return {
        "audio_parts": [
            {
                "chapter_index": item.chapter_index,
                "chunk_index": item.chunk_index,
                "part_index": item.part_index,
                "part_title": item.part_title,
                "part_id": item.part_id,
                "source_order_indices": list(item.source_order_indices),
                "filename": item.path.name,
                "path": str(item.path),
                "duration_seconds": item.duration_seconds,
                "provider": item.provider,
                "model": item.model,
                "voice": item.voice,
            }
            for item in audio_parts
        ],
        "metadata": {
            "chapter_scope": chapter_scope,
            "provider": runtime_config.tts_provider,
            "model": runtime_config.tts_model,
            "voice": runtime_config.tts_voice,
            "chapter_part_map": [
                {
                    "chapter_index": part.chapter_index,
                    "part_index": part.part_index,
                    "part_id": part.part_id,
                    "source_order_indices": list(part.source_order_indices),
                    "filename": part.path.name,
                }
                for part in audio_parts
            ],
        },
    }


def part_mapping_manifest_metadata(audio_parts: list[AudioPart]) -> dict[str, str]:
    """Build compact manifest metadata for chapter/part and source references."""

    chapter_part_map_entries = [
        f"{item.chapter_index}:{item.part_index if item.part_index is not None else item.chunk_index + 1}"
        for item in sorted(audio_parts, key=lambda part: (part.chapter_index, part.chunk_index))
    ]
    part_filename_entries = [
        item.path.name
        for item in sorted(audio_parts, key=lambda part: (part.chapter_index, part.chunk_index))
    ]
    referenced_unit_indices: list[int] = sorted(
        {
            index
            for item in audio_parts
            for index in item.source_order_indices
        }
    )
    return {
        "part_count": str(len(audio_parts)),
        "chapter_part_map_csv": ",".join(chapter_part_map_entries),
        "part_filenames_csv": ",".join(part_filename_entries),
        "part_source_structure_indices_csv": ",".join(
            str(index) for index in referenced_unit_indices
        ),
    }


def manifest_payload(manifest: RunManifest) -> dict[str, object]:
    """Serialize a run manifest into a JSON-safe payload."""

    return {
        "run_id": manifest.run_id,
        "config_hash": manifest.config_hash,
        "book": {
            "source_pdf": str(manifest.book.source_pdf),
            "title": manifest.book.title,
            "author": manifest.book.author,
            "language": manifest.book.language,
        },
        "merged_audio_path": str(manifest.merged_audio_path),
        "total_llm_cost_usd": manifest.total_llm_cost_usd,
        "total_tts_cost_usd": manifest.total_tts_cost_usd,
        "total_cost_usd": manifest.total_cost_usd,
        "extra": json.loads(json.dumps(dict(manifest.extra))),
    }


def load_json_object(path: Path) -> dict[str, object]:
    """Load an artifact JSON file and validate object root shape."""

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PipelineStageError(
            stage="resume-artifacts",
            detail=f"Artifact JSON is invalid: {path}",
            hint="Delete the corrupted artifact and run `bookvoice resume` again.",
        ) from exc
    if not isinstance(payload, dict):
        raise PipelineStageError(
            stage="resume-artifacts",
            detail=f"Artifact JSON must be an object: {path}",
            hint="Delete the corrupted artifact and run `bookvoice resume` again.",
        )
    return payload


def load_chapters(path: Path) -> list[Chapter]:
    """Load chapter artifacts from JSON."""

    payload = load_json_object(path)
    items = payload.get("chapters")
    if not isinstance(items, list):
        raise PipelineStageError(
            stage="resume-artifacts",
            detail=f"Artifact missing `chapters` list: {path}",
            hint="Delete chapters artifact and rerun `bookvoice resume`.",
        )
    chapters: list[Chapter] = []
    for item in items:
        if not isinstance(item, dict):
            raise PipelineStageError(
                stage="resume-artifacts",
                detail=f"Malformed chapter item in {path}",
                hint="Delete chapters artifact and rerun `bookvoice resume`.",
            )
        chapters.append(
            Chapter(
                index=int(item["index"]),
                title=str(item["title"]),
                text=str(item["text"]),
            )
        )
    return chapters


def load_chapter_metadata(path: Path) -> dict[str, str]:
    """Load chapter extraction metadata from chapter artifacts."""

    payload = load_json_object(path)
    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        return {"source": "", "fallback_reason": ""}
    source = metadata.get("source")
    fallback_reason = metadata.get("fallback_reason")
    return {
        "source": str(source) if isinstance(source, str) else "",
        "fallback_reason": str(fallback_reason) if isinstance(fallback_reason, str) else "",
    }


def load_normalized_structure(path: Path) -> list[ChapterStructureUnit]:
    """Load normalized structure units from chapter artifact metadata."""

    payload = load_json_object(path)
    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        return []
    raw_units = metadata.get("normalized_structure")
    if not isinstance(raw_units, list):
        return []

    units: list[ChapterStructureUnit] = []
    for item in raw_units:
        if not isinstance(item, dict):
            continue
        units.append(
            ChapterStructureUnit(
                order_index=int(item["order_index"]),
                chapter_index=int(item["chapter_index"]),
                chapter_title=str(item["chapter_title"]),
                subchapter_index=(
                    int(item["subchapter_index"])
                    if item.get("subchapter_index") is not None
                    else None
                ),
                subchapter_title=(
                    str(item["subchapter_title"])
                    if item.get("subchapter_title") is not None
                    else None
                ),
                text=str(item["text"]),
                char_start=int(item["char_start"]),
                char_end=int(item["char_end"]),
                source=str(item["source"]),
            )
        )
    return units


def _chunk_from_payload(payload: dict[str, object]) -> Chunk:
    """Deserialize a chunk payload from artifact JSON."""

    return Chunk(
        chapter_index=int(payload["chapter_index"]),
        chunk_index=int(payload["chunk_index"]),
        text=str(payload["text"]),
        char_start=int(payload["char_start"]),
        char_end=int(payload["char_end"]),
        part_index=(int(payload["part_index"]) if payload.get("part_index") is not None else None),
        part_title=(
            str(payload["part_title"]) if payload.get("part_title") is not None else None
        ),
        part_id=(str(payload["part_id"]) if payload.get("part_id") is not None else None),
        source_order_indices=tuple(int(index) for index in payload.get("source_order_indices", [])),
        boundary_strategy=str(payload.get("boundary_strategy", "sentence_complete")),
    )


def load_chunks(path: Path) -> list[Chunk]:
    """Load chunk artifacts from JSON."""

    payload = load_json_object(path)
    items = payload.get("chunks")
    if not isinstance(items, list):
        raise PipelineStageError(
            stage="resume-artifacts",
            detail=f"Artifact missing `chunks` list: {path}",
            hint="Delete chunks artifact and rerun `bookvoice resume`.",
        )
    chunks: list[Chunk] = []
    for item in items:
        if not isinstance(item, dict):
            raise PipelineStageError(
                stage="resume-artifacts",
                detail=f"Malformed chunk item in {path}",
                hint="Delete chunks artifact and rerun `bookvoice resume`.",
            )
        chunks.append(_chunk_from_payload(item))
    return chunks


def load_translations(path: Path) -> list[TranslationResult]:
    """Load translation artifacts from JSON."""

    payload = load_json_object(path)
    items = payload.get("translations")
    if not isinstance(items, list):
        raise PipelineStageError(
            stage="resume-artifacts",
            detail=f"Artifact missing `translations` list: {path}",
            hint="Delete translations artifact and rerun `bookvoice resume`.",
        )

    translations: list[TranslationResult] = []
    for item in items:
        if not isinstance(item, dict):
            raise PipelineStageError(
                stage="resume-artifacts",
                detail=f"Malformed translation item in {path}",
                hint="Delete translations artifact and rerun `bookvoice resume`.",
            )
        chunk_payload = item.get("chunk")
        if not isinstance(chunk_payload, dict):
            raise PipelineStageError(
                stage="resume-artifacts",
                detail=f"Translation item missing `chunk` object in {path}",
                hint="Delete translations artifact and rerun `bookvoice resume`.",
            )
        translations.append(
            TranslationResult(
                chunk=_chunk_from_payload(chunk_payload),
                translated_text=str(item["translated_text"]),
                provider=str(item["provider"]),
                model=str(item["model"]),
            )
        )
    return translations


def load_rewrites(path: Path) -> list[RewriteResult]:
    """Load rewrite artifacts from JSON."""

    payload = load_json_object(path)
    items = payload.get("rewrites")
    if not isinstance(items, list):
        raise PipelineStageError(
            stage="resume-artifacts",
            detail=f"Artifact missing `rewrites` list: {path}",
            hint="Delete rewrites artifact and rerun `bookvoice resume`.",
        )

    rewrites: list[RewriteResult] = []
    for item in items:
        if not isinstance(item, dict):
            raise PipelineStageError(
                stage="resume-artifacts",
                detail=f"Malformed rewrite item in {path}",
                hint="Delete rewrites artifact and rerun `bookvoice resume`.",
            )
        translation_payload = item.get("translation")
        if not isinstance(translation_payload, dict):
            raise PipelineStageError(
                stage="resume-artifacts",
                detail=f"Rewrite item missing `translation` object in {path}",
                hint="Delete rewrites artifact and rerun `bookvoice resume`.",
            )
        chunk_payload = translation_payload.get("chunk")
        if not isinstance(chunk_payload, dict):
            raise PipelineStageError(
                stage="resume-artifacts",
                detail=f"Rewrite translation missing `chunk` object in {path}",
                hint="Delete rewrites artifact and rerun `bookvoice resume`.",
            )

        translation = TranslationResult(
            chunk=_chunk_from_payload(chunk_payload),
            translated_text=str(translation_payload["translated_text"]),
            provider=str(translation_payload["provider"]),
            model=str(translation_payload["model"]),
        )
        rewrites.append(
            RewriteResult(
                translation=translation,
                rewritten_text=str(item["rewritten_text"]),
                provider=str(item["provider"]),
                model=str(item["model"]),
            )
        )
    return rewrites


def load_audio_parts(path: Path) -> list[AudioPart]:
    """Load synthesized audio part artifacts from JSON."""

    payload = load_json_object(path)
    items = payload.get("audio_parts")
    if not isinstance(items, list):
        raise PipelineStageError(
            stage="resume-artifacts",
            detail=f"Artifact missing `audio_parts` list: {path}",
            hint="Delete audio parts artifact and rerun `bookvoice resume`.",
        )

    audio_parts: list[AudioPart] = []
    for item in items:
        if not isinstance(item, dict):
            raise PipelineStageError(
                stage="resume-artifacts",
                detail=f"Malformed audio part item in {path}",
                hint="Delete audio parts artifact and rerun `bookvoice resume`.",
            )
        audio_parts.append(
            AudioPart(
                chapter_index=int(item["chapter_index"]),
                chunk_index=int(item["chunk_index"]),
                path=Path(str(item["path"])),
                duration_seconds=float(item["duration_seconds"]),
                part_index=(int(item["part_index"]) if item.get("part_index") is not None else None),
                part_title=(
                    str(item["part_title"]) if item.get("part_title") is not None else None
                ),
                part_id=(str(item["part_id"]) if item.get("part_id") is not None else None),
                source_order_indices=tuple(int(index) for index in item.get("source_order_indices", [])),
                provider=str(item["provider"]) if isinstance(item.get("provider"), str) else None,
                model=str(item["model"]) if isinstance(item.get("model"), str) else None,
                voice=str(item["voice"]) if isinstance(item.get("voice"), str) else None,
            )
        )
    return audio_parts
