"""Pipeline orchestration for Bookvoice.

Responsibilities:
- Define the high-level stage order for the audiobook build flow.
- Coordinate stage outputs into a reproducible run manifest.

Key types:
- `BookvoicePipeline`: orchestration facade.
- `RunManifest`: immutable record of run inputs and outputs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from collections.abc import Callable
from pathlib import Path

from ..config import BookvoiceConfig, ProviderRuntimeConfig
from ..errors import PipelineStageError
from ..io.storage import ArtifactStore
from ..models.datatypes import (
    AudioPart,
    Chapter,
    ChapterStructureUnit,
    Chunk,
    RewriteResult,
    RunManifest,
    TranslationResult,
)
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
    rewrite_artifact_payload,
    translation_artifact_payload,
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


@dataclass(slots=True)
class ResumeArtifactPaths:
    """Resolved artifact paths used by the resume flow."""

    raw_text: Path
    clean_text: Path
    chapters: Path
    chunks: Path
    translations: Path
    rewrites: Path
    audio_parts: Path
    merged: Path


@dataclass(slots=True)
class ResumeState:
    """Typed context shared across stage-specific resume helper methods."""

    manifest_path: Path
    run_id: str
    config_hash: str
    extra: dict[str, object]
    config: BookvoiceConfig
    runtime_config: ProviderRuntimeConfig
    store: ArtifactStore
    paths: ResumeArtifactPaths
    next_stage: str
    cost_tracker: CostTracker = field(default_factory=CostTracker)
    chapter_source: str = "unknown"
    chapter_fallback_reason: str = ""
    chapter_scope: dict[str, str] = field(default_factory=dict)
    raw_text: str = ""
    clean_text: str = ""
    chapters: list[Chapter] = field(default_factory=list)
    normalized_structure: list[ChapterStructureUnit] = field(default_factory=list)
    selected_chapters: list[Chapter] = field(default_factory=list)
    chunks: list[Chunk] = field(default_factory=list)
    translations: list[TranslationResult] = field(default_factory=list)
    rewrites: list[RewriteResult] = field(default_factory=list)
    audio_parts: list[AudioPart] = field(default_factory=list)
    reuse_audio_parts: bool = False
    final_merged_path: Path | None = None


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
            translation_artifact_payload(translations, chapter_scope, runtime_config),
        )

        rewrites = self._run_stage(
            "rewrite",
            lambda: self._rewrite_for_audio(translations, config, runtime_config),
        )
        add_rewrite_costs(rewrites, cost_tracker)
        rewrites_path = store.save_json(
            Path("text/rewrites.json"),
            rewrite_artifact_payload(rewrites, chapter_scope, runtime_config),
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

    def run_translate_only(self, config: BookvoiceConfig) -> RunManifest:
        """Run stages through translation and persist deterministic text artifacts."""

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
            translation_artifact_payload(translations, chapter_scope, runtime_config),
        )

        return self._run_stage(
            "manifest",
            lambda: self._write_manifest(
                config=config,
                run_id=run_id,
                config_hash=config_hash,
                merged_audio_path=self._merged_output_path_for_scope(store, chapter_scope),
                artifact_paths={
                    "run_root": str(store.root),
                    "raw_text": str(raw_text_path),
                    "clean_text": str(clean_text_path),
                    "chapters": str(chapters_path),
                    "chunks": str(chunks_path),
                    "translations": str(translations_path),
                    "chapter_source": chapter_source,
                    "chapter_fallback_reason": chapter_fallback_reason,
                    "pipeline_mode": "translate_only",
                    **runtime_config.as_manifest_metadata(),
                    **chapter_scope,
                },
                cost_summary=rounded_cost_summary(cost_tracker),
                store=store,
            ),
        )

    def resume(self, manifest_path: Path) -> RunManifest:
        """Resume a run from an existing manifest and artifacts."""

        state = self._build_resume_state(manifest_path)
        self._load_or_extract_resume_text(state)
        self._load_or_clean_resume_text(state)
        self._load_or_split_resume_chapters(state)
        self._load_or_chunk_resume_artifact(state)
        self._load_or_translate_resume_artifact(state)
        self._load_or_rewrite_resume_artifact(state)
        self._load_or_tts_resume_artifact(state)
        self._load_or_merge_resume_artifact(state)
        return self._write_resume_manifest(state)

    def _build_resume_state(self, manifest_path: Path) -> ResumeState:
        """Create typed resume context with resolved paths and runtime settings."""

        payload = load_manifest_payload(manifest_path)
        run_id = require_manifest_field(payload, "run_id")
        config_hash = require_manifest_field(payload, "config_hash")

        book_payload = payload.get("book")
        if not isinstance(book_payload, dict):
            raise ValueError(
                "Manifest is missing required object `book`; run `bookvoice build` again "
                "or provide a valid manifest."
            )
        source_pdf = Path(require_manifest_field(book_payload, "source_pdf", scope="book"))
        language = require_manifest_field(book_payload, "language", scope="book")

        extra = payload.get("extra")
        normalized_extra = extra if isinstance(extra, dict) else {}
        chapter_source = (
            str(normalized_extra.get("chapter_source"))
            if isinstance(normalized_extra.get("chapter_source"), str)
            else "unknown"
        )
        chapter_fallback_reason = (
            str(normalized_extra.get("chapter_fallback_reason"))
            if isinstance(normalized_extra.get("chapter_fallback_reason"), str)
            else ""
        )

        run_root = resolve_run_root(manifest_path, normalized_extra)
        store = ArtifactStore(run_root)
        config = BookvoiceConfig(
            input_pdf=source_pdf,
            output_dir=run_root.parent,
            language=language,
            provider_translator=manifest_string(normalized_extra, "provider_translator", "openai"),
            provider_rewriter=manifest_string(normalized_extra, "provider_rewriter", "openai"),
            provider_tts=manifest_string(normalized_extra, "provider_tts", "openai"),
            model_translate=manifest_string(normalized_extra, "model_translate", "gpt-4.1-mini"),
            model_rewrite=manifest_string(normalized_extra, "model_rewrite", "gpt-4.1-mini"),
            model_tts=manifest_string(normalized_extra, "model_tts", "gpt-4o-mini-tts"),
            tts_voice=manifest_string(normalized_extra, "tts_voice", "echo"),
            rewrite_bypass=manifest_bool(normalized_extra, "rewrite_bypass", False),
            resume=True,
        )
        runtime_config = self._resolve_runtime_config(config)

        paths = ResumeArtifactPaths(
            raw_text=resolve_artifact_path(
                manifest_path, run_root, normalized_extra, "raw_text", Path("text/raw.txt")
            ),
            clean_text=resolve_artifact_path(
                manifest_path, run_root, normalized_extra, "clean_text", Path("text/clean.txt")
            ),
            chapters=resolve_artifact_path(
                manifest_path, run_root, normalized_extra, "chapters", Path("text/chapters.json")
            ),
            chunks=resolve_artifact_path(
                manifest_path, run_root, normalized_extra, "chunks", Path("text/chunks.json")
            ),
            translations=resolve_artifact_path(
                manifest_path,
                run_root,
                normalized_extra,
                "translations",
                Path("text/translations.json"),
            ),
            rewrites=resolve_artifact_path(
                manifest_path, run_root, normalized_extra, "rewrites", Path("text/rewrites.json")
            ),
            audio_parts=resolve_artifact_path(
                manifest_path, run_root, normalized_extra, "audio_parts", Path("audio/parts.json")
            ),
            merged=resolve_merged_path(manifest_path, run_root, payload),
        )
        next_stage = detect_next_stage(
            raw_text_path=paths.raw_text,
            clean_text_path=paths.clean_text,
            chapters_path=paths.chapters,
            chunks_path=paths.chunks,
            translations_path=paths.translations,
            rewrites_path=paths.rewrites,
            audio_parts_path=paths.audio_parts,
            merged_path=paths.merged,
        )

        return ResumeState(
            manifest_path=manifest_path,
            run_id=run_id,
            config_hash=config_hash,
            extra=normalized_extra,
            config=config,
            runtime_config=runtime_config,
            store=store,
            paths=paths,
            next_stage=next_stage,
            chapter_source=chapter_source,
            chapter_fallback_reason=chapter_fallback_reason,
        )

    def _load_or_extract_resume_text(self, state: ResumeState) -> None:
        """Load existing raw text artifact or rerun extract stage."""

        if state.paths.raw_text.exists():
            state.raw_text = state.paths.raw_text.read_text(encoding="utf-8")
            return

        if not state.config.input_pdf.exists():
            raise ValueError(
                "Cannot resume extract stage: source PDF from manifest does not exist: "
                f"{state.config.input_pdf}"
            )
        state.raw_text = self._extract(state.config)
        state.paths.raw_text = state.store.save_text(Path("text/raw.txt"), state.raw_text)

    def _load_or_clean_resume_text(self, state: ResumeState) -> None:
        """Load existing clean text artifact or rerun clean stage."""

        if state.paths.clean_text.exists():
            state.clean_text = state.paths.clean_text.read_text(encoding="utf-8")
            return

        state.clean_text = self._clean(state.raw_text)
        state.paths.clean_text = state.store.save_text(Path("text/clean.txt"), state.clean_text)

    def _load_or_split_resume_chapters(self, state: ResumeState) -> None:
        """Load chapter artifacts/metadata or rerun split stage and recover scope."""

        if state.paths.chapters.exists():
            state.chapters = load_chapters(state.paths.chapters)
            chapter_metadata = load_chapter_metadata(state.paths.chapters)
            if chapter_metadata["source"]:
                state.chapter_source = chapter_metadata["source"]
            state.chapter_fallback_reason = chapter_metadata["fallback_reason"]
            state.normalized_structure = load_normalized_structure(state.paths.chapters)
        else:
            (
                state.chapters,
                state.chapter_source,
                state.chapter_fallback_reason,
            ) = self._split_chapters(state.clean_text, state.config.input_pdf)
            state.normalized_structure = self._extract_normalized_structure(
                state.chapters,
                state.chapter_source,
                state.config.input_pdf,
            )
            _, state.chapter_scope = self._resolve_resume_chapter_scope(
                state.chapters, state.extra
            )
            state.paths.chapters = state.store.save_json(
                Path("text/chapters.json"),
                chapter_artifact_payload(
                    state.chapters,
                    state.chapter_source,
                    state.chapter_fallback_reason,
                    state.chapter_scope,
                    state.normalized_structure,
                ),
            )

        if not state.normalized_structure:
            state.normalized_structure = self._extract_normalized_structure(
                chapters=state.chapters,
                chapter_source="text_heuristic",
                source_pdf=state.config.input_pdf,
            )
        (
            state.selected_chapters,
            state.chapter_scope,
        ) = self._resolve_resume_chapter_scope(state.chapters, state.extra)

    def _load_or_chunk_resume_artifact(self, state: ResumeState) -> None:
        """Load existing chunk artifact or rerun deterministic chunk planning."""

        if state.paths.chunks.exists():
            state.chunks = load_chunks(state.paths.chunks)
            return

        state.chunks, chunk_metadata = self._chunk(
            state.selected_chapters, state.normalized_structure, state.config
        )
        state.paths.chunks = state.store.save_json(
            Path("text/chunks.json"),
            chunk_artifact_payload(state.chunks, state.chapter_scope, chunk_metadata),
        )

    def _load_or_translate_resume_artifact(self, state: ResumeState) -> None:
        """Load existing translations or rerun translation stage."""

        if state.paths.translations.exists():
            state.translations = load_translations(state.paths.translations)
        else:
            state.translations = self._translate(state.chunks, state.config)
            state.paths.translations = state.store.save_json(
                Path("text/translations.json"),
                translation_artifact_payload(
                    state.translations,
                    state.chapter_scope,
                    state.runtime_config,
                ),
            )
        add_translation_costs(state.translations, state.cost_tracker)

    def _load_or_rewrite_resume_artifact(self, state: ResumeState) -> None:
        """Load existing rewrites or rerun rewrite stage."""

        if state.paths.rewrites.exists():
            state.rewrites = load_rewrites(state.paths.rewrites)
        else:
            state.rewrites = self._rewrite_for_audio(
                state.translations,
                state.config,
                state.runtime_config,
            )
            state.paths.rewrites = state.store.save_json(
                Path("text/rewrites.json"),
                rewrite_artifact_payload(
                    state.rewrites,
                    state.chapter_scope,
                    state.runtime_config,
                ),
            )
        add_rewrite_costs(state.rewrites, state.cost_tracker)

    def _load_or_tts_resume_artifact(self, state: ResumeState) -> None:
        """Load reusable audio parts or rerun TTS when parts/artifacts are missing."""

        if state.paths.audio_parts.exists():
            loaded_parts = load_audio_parts(state.paths.audio_parts)
            if all(part.path.exists() for part in loaded_parts):
                state.audio_parts = loaded_parts
                state.reuse_audio_parts = True
            else:
                state.audio_parts = self._tts(
                    state.rewrites,
                    state.config,
                    state.store,
                    state.runtime_config,
                )
                state.paths.audio_parts = state.store.save_json(
                    Path("audio/parts.json"),
                    audio_parts_artifact_payload(
                        state.audio_parts,
                        state.chapter_scope,
                        state.runtime_config,
                    ),
                )
        else:
            state.audio_parts = self._tts(
                state.rewrites,
                state.config,
                state.store,
                state.runtime_config,
            )
            state.paths.audio_parts = state.store.save_json(
                Path("audio/parts.json"),
                audio_parts_artifact_payload(
                    state.audio_parts,
                    state.chapter_scope,
                    state.runtime_config,
                ),
            )
        add_tts_costs(state.rewrites, state.cost_tracker)

    def _load_or_merge_resume_artifact(self, state: ResumeState) -> None:
        """Reuse merged audio only when audio parts were fully reused."""

        if state.paths.merged.exists() and state.reuse_audio_parts:
            state.final_merged_path = state.paths.merged
            return

        processed = self._postprocess(state.audio_parts, state.config)
        state.final_merged_path = self._merge(
            processed,
            state.config,
            state.store,
            output_path=state.paths.merged,
        )

    def _write_resume_manifest(self, state: ResumeState) -> RunManifest:
        """Write final resume manifest while preserving metadata keys."""

        if state.final_merged_path is None:
            raise PipelineStageError(
                stage="resume-artifacts",
                detail="Resume merge stage did not produce a merged output path.",
                hint="Retry `bookvoice resume` to regenerate downstream artifacts.",
            )
        part_mapping_metadata = part_mapping_manifest_metadata(state.audio_parts)
        return self._write_manifest(
            config=state.config,
            run_id=state.run_id,
            config_hash=state.config_hash,
            merged_audio_path=state.final_merged_path,
            artifact_paths={
                "run_root": str(state.store.root),
                "raw_text": str(state.paths.raw_text),
                "clean_text": str(state.paths.clean_text),
                "chapters": str(state.paths.chapters),
                "chunks": str(state.paths.chunks),
                "translations": str(state.paths.translations),
                "rewrites": str(state.paths.rewrites),
                "audio_parts": str(state.paths.audio_parts),
                "merged_audio_filename": state.final_merged_path.name,
                "resume_next_stage": state.next_stage,
                "chapter_source": state.chapter_source,
                "chapter_fallback_reason": state.chapter_fallback_reason,
                **part_mapping_metadata,
                **state.runtime_config.as_manifest_metadata(),
                **state.chapter_scope,
            },
            cost_summary=rounded_cost_summary(state.cost_tracker),
            store=state.store,
        )
