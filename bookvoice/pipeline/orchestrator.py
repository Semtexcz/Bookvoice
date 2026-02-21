"""Pipeline orchestration for Bookvoice.

Responsibilities:
- Define the high-level stage order for the audiobook build flow.
- Coordinate stage outputs into a reproducible run manifest.

Key types:
- `BookvoicePipeline`: orchestration facade.
- `RunManifest`: immutable record of run inputs and outputs.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path

from ..config import BookvoiceConfig
from ..errors import PipelineStageError
from ..io.storage import ArtifactStore
from ..models.datatypes import Chapter, RunManifest
from ..telemetry.cost_tracker import CostTracker
from ..telemetry.logger import RunLogger
from .artifacts import (
    audio_parts_artifact_payload,
    chapter_artifact_payload,
    chunk_artifact_payload,
    load_audio_parts,
    load_chapter_metadata,
    load_chapters,
    load_chunks,
    load_normalized_structure,
    load_rewrites,
    load_translations,
    part_mapping_manifest_metadata,
    rewrite_artifact_metadata,
)
from .chapter_scope import PipelineChapterScopeMixin
from .costs import (
    add_rewrite_costs,
    add_translation_costs,
    add_tts_costs,
    rounded_cost_summary,
)
from .execution import PipelineExecutionMixin
from .manifesting import PipelineManifestMixin
from .resume import (
    detect_next_stage,
    load_manifest_payload,
    manifest_bool,
    manifest_string,
    require_manifest_field,
    resolve_artifact_path,
    resolve_merged_path,
    resolve_run_root,
)
from .runtime import PipelineRuntimeMixin
from .telemetry import PipelineTelemetryMixin


class BookvoicePipeline(
    PipelineRuntimeMixin,
    PipelineChapterScopeMixin,
    PipelineExecutionMixin,
    PipelineManifestMixin,
    PipelineTelemetryMixin,
):
    """Coordinate all stages for a single Bookvoice run."""

    def __init__(
        self,
        run_logger: RunLogger | None = None,
        stage_progress_callback: Callable[[str, int, int], None] | None = None,
    ) -> None:
        """Initialize optional runtime logging and progress reporting hooks."""

        self._run_logger = run_logger
        self._stage_progress_callback = stage_progress_callback

    def list_chapters_from_pdf(
        self, config: BookvoiceConfig
    ) -> tuple[list[Chapter], str, str]:
        """List chapters by running extract/clean/split without writing artifacts."""

        raw_text = self._extract(config)
        clean_text = self._clean(raw_text)
        return self._split_chapters(clean_text, config.input_pdf)

    def list_chapters_from_artifact(
        self, chapters_artifact: Path
    ) -> tuple[list[Chapter], str, str]:
        """List chapters and metadata from an existing chapter artifact JSON file."""

        if not chapters_artifact.exists():
            raise PipelineStageError(
                stage="chapters-artifact",
                detail=f"Chapters artifact not found: {chapters_artifact}",
                hint=(
                    "Run `bookvoice chapters-only <input.pdf>` first or provide "
                    "a valid `text/chapters.json` path."
                ),
            )

        try:
            chapters = load_chapters(chapters_artifact)
            metadata = load_chapter_metadata(chapters_artifact)
        except PipelineStageError as exc:
            raise PipelineStageError(
                stage="chapters-artifact",
                detail=exc.detail,
                hint=(
                    "Ensure the file is a valid `text/chapters.json` artifact "
                    "and rerun the command."
                ),
            ) from exc
        except Exception as exc:
            raise PipelineStageError(
                stage="chapters-artifact",
                detail=f"Failed to parse chapters artifact `{chapters_artifact}`: {exc}",
                hint=(
                    "Ensure the file is a valid `text/chapters.json` artifact "
                    "and rerun the command."
                ),
            ) from exc

        return chapters, metadata["source"], metadata["fallback_reason"]

    def run(self, config: BookvoiceConfig) -> RunManifest:
        """Run the full pipeline and return a manifest."""

        run_id, config_hash, store = self._prepare_run(config)
        runtime_config = self._resolve_runtime_config(config)
        cost_tracker = CostTracker()

        raw_text = self._run_stage("extract", lambda: self._extract(config))
        raw_text_path = store.save_text(Path("text/raw.txt"), raw_text)

        clean_text = self._run_stage("clean", lambda: self._clean(raw_text))
        clean_text_path = store.save_text(Path("text/clean.txt"), clean_text)

        chapters, chapter_source, chapter_fallback_reason = self._run_stage(
            "split",
            lambda: self._split_chapters(clean_text, config.input_pdf),
        )
        normalized_structure = self._extract_normalized_structure(
            chapters, chapter_source, config.input_pdf
        )
        selected_chapters, chapter_scope = self._resolve_chapter_scope(
            chapters, config.chapter_selection
        )
        chapters_path = store.save_json(
            Path("text/chapters.json"),
            chapter_artifact_payload(
                chapters,
                chapter_source,
                chapter_fallback_reason,
                chapter_scope,
                normalized_structure,
            ),
        )

        chunks, chunk_metadata = self._run_stage(
            "chunk",
            lambda: self._chunk(selected_chapters, normalized_structure, config),
        )
        chunks_path = store.save_json(
            Path("text/chunks.json"),
            chunk_artifact_payload(chunks, chapter_scope, chunk_metadata),
        )

        translations = self._run_stage("translate", lambda: self._translate(chunks, config))
        add_translation_costs(translations, cost_tracker)
        translations_path = store.save_json(
            Path("text/translations.json"),
            {
                "translations": [
                    {
                        "chunk": asdict(item.chunk),
                        "translated_text": item.translated_text,
                        "provider": item.provider,
                        "model": item.model,
                    }
                    for item in translations
                ],
                "metadata": {
                    "chapter_scope": chapter_scope,
                    "provider": runtime_config.translator_provider,
                    "model": runtime_config.translate_model,
                },
            },
        )

        rewrites = self._run_stage(
            "rewrite",
            lambda: self._rewrite_for_audio(translations, config, runtime_config),
        )
        add_rewrite_costs(rewrites, cost_tracker)
        rewrites_path = store.save_json(
            Path("text/rewrites.json"),
            {
                "rewrites": [
                    {
                        "translation": {
                            "chunk": asdict(item.translation.chunk),
                            "translated_text": item.translation.translated_text,
                            "provider": item.translation.provider,
                            "model": item.translation.model,
                        },
                        "rewritten_text": item.rewritten_text,
                        "provider": item.provider,
                        "model": item.model,
                    }
                    for item in rewrites
                ],
                "metadata": {
                    "chapter_scope": chapter_scope,
                    **rewrite_artifact_metadata(rewrites, runtime_config),
                },
            },
        )

        audio_parts = self._run_stage(
            "tts",
            lambda: self._tts(rewrites, config, store, runtime_config),
        )
        add_tts_costs(rewrites, cost_tracker)
        audio_parts_path = store.save_json(
            Path("audio/parts.json"),
            audio_parts_artifact_payload(audio_parts, chapter_scope, runtime_config),
        )
        part_mapping_metadata = part_mapping_manifest_metadata(audio_parts)

        merged_path = self._run_stage(
            "merge",
            lambda: self._merge(
                self._postprocess(audio_parts, config),
                config,
                store,
                output_path=self._merged_output_path_for_scope(store, chapter_scope),
            ),
        )

        manifest = self._run_stage(
            "manifest",
            lambda: self._write_manifest(
                config=config,
                run_id=run_id,
                config_hash=config_hash,
                merged_audio_path=merged_path,
                artifact_paths={
                    "run_root": str(store.root),
                    "raw_text": str(raw_text_path),
                    "clean_text": str(clean_text_path),
                    "chapters": str(chapters_path),
                    "chunks": str(chunks_path),
                    "translations": str(translations_path),
                    "rewrites": str(rewrites_path),
                    "audio_parts": str(audio_parts_path),
                    "merged_audio_filename": merged_path.name,
                    "chapter_source": chapter_source,
                    "chapter_fallback_reason": chapter_fallback_reason,
                    **part_mapping_metadata,
                    **runtime_config.as_manifest_metadata(),
                    **chapter_scope,
                },
                cost_summary=rounded_cost_summary(cost_tracker),
                store=store,
            ),
        )
        return manifest

    def run_chapters_only(self, config: BookvoiceConfig) -> RunManifest:
        """Run only extract/clean/split stages and persist chapter artifacts."""

        run_id, config_hash, store = self._prepare_run(config)
        runtime_config = self._resolve_runtime_config(config)

        raw_text = self._extract(config)
        raw_text_path = store.save_text(Path("text/raw.txt"), raw_text)

        clean_text = self._clean(raw_text)
        clean_text_path = store.save_text(Path("text/clean.txt"), clean_text)

        chapters, chapter_source, chapter_fallback_reason = self._split_chapters(
            clean_text, config.input_pdf
        )
        _, chapter_scope = self._resolve_chapter_scope(chapters, config.chapter_selection)
        chapters_path = store.save_json(
            Path("text/chapters.json"),
            chapter_artifact_payload(
                chapters,
                chapter_source,
                chapter_fallback_reason,
                chapter_scope,
                self._extract_normalized_structure(chapters, chapter_source, config.input_pdf),
            ),
        )

        return self._write_manifest(
            config=config,
            run_id=run_id,
            config_hash=config_hash,
            merged_audio_path=self._merged_output_path_for_scope(store, chapter_scope),
            artifact_paths={
                "run_root": str(store.root),
                "raw_text": str(raw_text_path),
                "clean_text": str(clean_text_path),
                "chapters": str(chapters_path),
                "chapter_source": chapter_source,
                "chapter_fallback_reason": chapter_fallback_reason,
                "pipeline_mode": "chapters_only",
                **runtime_config.as_manifest_metadata(),
                **chapter_scope,
            },
            cost_summary={"llm_cost_usd": 0.0, "tts_cost_usd": 0.0, "total_cost_usd": 0.0},
            store=store,
        )

    def resume(self, manifest_path: Path) -> RunManifest:
        """Resume a run from an existing manifest and artifacts."""

        payload = load_manifest_payload(manifest_path)
        run_id = require_manifest_field(payload, "run_id")
        config_hash = require_manifest_field(payload, "config_hash")

        book_payload = payload.get("book")
        if not isinstance(book_payload, dict):
            raise ValueError(
                "Manifest is missing required object `book`; run `bookvoice build` again "
                "or provide a valid manifest."
            )
        source_pdf_value = require_manifest_field(book_payload, "source_pdf", scope="book")
        language_value = require_manifest_field(book_payload, "language", scope="book")

        source_pdf = Path(source_pdf_value)
        language = str(language_value)

        extra = payload.get("extra")
        if not isinstance(extra, dict):
            extra = {}
        chapter_source = (
            str(extra.get("chapter_source"))
            if isinstance(extra.get("chapter_source"), str)
            else "unknown"
        )
        chapter_fallback_reason = (
            str(extra.get("chapter_fallback_reason"))
            if isinstance(extra.get("chapter_fallback_reason"), str)
            else ""
        )
        cost_tracker = CostTracker()

        run_root = resolve_run_root(manifest_path, extra)
        store = ArtifactStore(run_root)
        config = BookvoiceConfig(
            input_pdf=source_pdf,
            output_dir=run_root.parent,
            language=language,
            provider_translator=manifest_string(extra, "provider_translator", "openai"),
            provider_rewriter=manifest_string(extra, "provider_rewriter", "openai"),
            provider_tts=manifest_string(extra, "provider_tts", "openai"),
            model_translate=manifest_string(extra, "model_translate", "gpt-4.1-mini"),
            model_rewrite=manifest_string(extra, "model_rewrite", "gpt-4.1-mini"),
            model_tts=manifest_string(extra, "model_tts", "gpt-4o-mini-tts"),
            tts_voice=manifest_string(extra, "tts_voice", "echo"),
            rewrite_bypass=manifest_bool(extra, "rewrite_bypass", False),
            resume=True,
        )
        runtime_config = self._resolve_runtime_config(config)

        raw_text_path = resolve_artifact_path(
            manifest_path, run_root, extra, "raw_text", Path("text/raw.txt")
        )
        clean_text_path = resolve_artifact_path(
            manifest_path, run_root, extra, "clean_text", Path("text/clean.txt")
        )
        chapters_path = resolve_artifact_path(
            manifest_path, run_root, extra, "chapters", Path("text/chapters.json")
        )
        chunks_path = resolve_artifact_path(
            manifest_path, run_root, extra, "chunks", Path("text/chunks.json")
        )
        translations_path = resolve_artifact_path(
            manifest_path, run_root, extra, "translations", Path("text/translations.json")
        )
        rewrites_path = resolve_artifact_path(
            manifest_path, run_root, extra, "rewrites", Path("text/rewrites.json")
        )
        audio_parts_path = resolve_artifact_path(
            manifest_path, run_root, extra, "audio_parts", Path("audio/parts.json")
        )
        merged_path = resolve_merged_path(manifest_path, run_root, payload)

        next_stage = detect_next_stage(
            raw_text_path=raw_text_path,
            clean_text_path=clean_text_path,
            chapters_path=chapters_path,
            chunks_path=chunks_path,
            translations_path=translations_path,
            rewrites_path=rewrites_path,
            audio_parts_path=audio_parts_path,
            merged_path=merged_path,
        )

        if raw_text_path.exists():
            raw_text = raw_text_path.read_text(encoding="utf-8")
        else:
            if not source_pdf.exists():
                raise ValueError(
                    "Cannot resume extract stage: source PDF from manifest does not exist: "
                    f"{source_pdf}"
                )
            raw_text = self._extract(config)
            raw_text_path = store.save_text(Path("text/raw.txt"), raw_text)

        if clean_text_path.exists():
            clean_text = clean_text_path.read_text(encoding="utf-8")
        else:
            clean_text = self._clean(raw_text)
            clean_text_path = store.save_text(Path("text/clean.txt"), clean_text)

        if chapters_path.exists():
            chapters = load_chapters(chapters_path)
            chapter_metadata = load_chapter_metadata(chapters_path)
            if chapter_metadata["source"]:
                chapter_source = chapter_metadata["source"]
            chapter_fallback_reason = chapter_metadata["fallback_reason"]
            normalized_structure = load_normalized_structure(chapters_path)
        else:
            chapters, chapter_source, chapter_fallback_reason = self._split_chapters(
                clean_text, config.input_pdf
            )
            normalized_structure = self._extract_normalized_structure(
                chapters, chapter_source, config.input_pdf
            )
            _, chapter_scope = self._resolve_resume_chapter_scope(chapters, extra)
            chapters_path = store.save_json(
                Path("text/chapters.json"),
                chapter_artifact_payload(
                    chapters,
                    chapter_source,
                    chapter_fallback_reason,
                    chapter_scope,
                    normalized_structure,
                ),
            )

        if not normalized_structure:
            normalized_structure = self._extract_normalized_structure(
                chapters=chapters,
                chapter_source="text_heuristic",
                source_pdf=config.input_pdf,
            )
        selected_chapters, chapter_scope = self._resolve_resume_chapter_scope(chapters, extra)

        if chunks_path.exists():
            chunks = load_chunks(chunks_path)
        else:
            chunks, chunk_metadata = self._chunk(selected_chapters, normalized_structure, config)
            chunks_path = store.save_json(
                Path("text/chunks.json"),
                chunk_artifact_payload(chunks, chapter_scope, chunk_metadata),
            )

        if translations_path.exists():
            translations = load_translations(translations_path)
        else:
            translations = self._translate(chunks, config)
            translations_path = store.save_json(
                Path("text/translations.json"),
                {
                    "translations": [
                        {
                            "chunk": asdict(item.chunk),
                            "translated_text": item.translated_text,
                            "provider": item.provider,
                            "model": item.model,
                        }
                        for item in translations
                    ],
                    "metadata": {
                        "chapter_scope": chapter_scope,
                        "provider": runtime_config.translator_provider,
                        "model": runtime_config.translate_model,
                    },
                },
            )
        add_translation_costs(translations, cost_tracker)

        if rewrites_path.exists():
            rewrites = load_rewrites(rewrites_path)
        else:
            rewrites = self._rewrite_for_audio(translations, config, runtime_config)
            rewrites_path = store.save_json(
                Path("text/rewrites.json"),
                {
                    "rewrites": [
                        {
                            "translation": {
                                "chunk": asdict(item.translation.chunk),
                                "translated_text": item.translation.translated_text,
                                "provider": item.translation.provider,
                                "model": item.translation.model,
                            },
                            "rewritten_text": item.rewritten_text,
                            "provider": item.provider,
                            "model": item.model,
                        }
                        for item in rewrites
                    ],
                    "metadata": {
                        "chapter_scope": chapter_scope,
                        **rewrite_artifact_metadata(rewrites, runtime_config),
                    },
                },
            )
        add_rewrite_costs(rewrites, cost_tracker)

        reuse_audio_parts = False
        if audio_parts_path.exists():
            loaded_parts = load_audio_parts(audio_parts_path)
            if all(part.path.exists() for part in loaded_parts):
                audio_parts = loaded_parts
                reuse_audio_parts = True
            else:
                audio_parts = self._tts(rewrites, config, store, runtime_config)
                audio_parts_path = store.save_json(
                    Path("audio/parts.json"),
                    audio_parts_artifact_payload(audio_parts, chapter_scope, runtime_config),
                )
        else:
            audio_parts = self._tts(rewrites, config, store, runtime_config)
            audio_parts_path = store.save_json(
                Path("audio/parts.json"),
                audio_parts_artifact_payload(audio_parts, chapter_scope, runtime_config),
            )
        add_tts_costs(rewrites, cost_tracker)
        part_mapping_metadata = part_mapping_manifest_metadata(audio_parts)

        if merged_path.exists() and reuse_audio_parts:
            final_merged_path = merged_path
        else:
            processed = self._postprocess(audio_parts, config)
            final_merged_path = self._merge(
                processed,
                config,
                store,
                output_path=merged_path,
            )

        return self._write_manifest(
            config=config,
            run_id=run_id,
            config_hash=config_hash,
            merged_audio_path=final_merged_path,
            artifact_paths={
                "run_root": str(store.root),
                "raw_text": str(raw_text_path),
                "clean_text": str(clean_text_path),
                "chapters": str(chapters_path),
                "chunks": str(chunks_path),
                "translations": str(translations_path),
                "rewrites": str(rewrites_path),
                "audio_parts": str(audio_parts_path),
                "merged_audio_filename": final_merged_path.name,
                "resume_next_stage": next_stage,
                "chapter_source": chapter_source,
                "chapter_fallback_reason": chapter_fallback_reason,
                **part_mapping_metadata,
                **runtime_config.as_manifest_metadata(),
                **chapter_scope,
            },
            cost_summary=rounded_cost_summary(cost_tracker),
            store=store,
        )
