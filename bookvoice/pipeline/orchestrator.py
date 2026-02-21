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
from hashlib import sha256
import json
import os
from pathlib import Path
from typing import TypeVar

from ..audio.merger import AudioMerger
from ..audio.postprocess import AudioPostProcessor
from ..config import BookvoiceConfig, ProviderRuntimeConfig, RuntimeConfigSources
from ..errors import PipelineStageError
from ..io.chapter_splitter import ChapterSplitter
from ..io.pdf_outline_extractor import PdfOutlineChapterExtractor
from ..io.pdf_text_extractor import PdfTextExtractor
from ..io.storage import ArtifactStore
from ..llm.audio_rewriter import DeterministicBypassRewriter
from ..llm.openai_client import OpenAIProviderError
from ..models.datatypes import (
    AudioPart,
    BookMeta,
    Chapter,
    ChapterStructureUnit,
    Chunk,
    RewriteResult,
    RunManifest,
    TranslationResult,
)
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
    manifest_payload,
    part_mapping_manifest_metadata,
    rewrite_artifact_metadata,
)
from .costs import (
    add_rewrite_costs,
    add_translation_costs,
    add_tts_costs,
    rounded_cost_summary,
)
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
from ..provider_factory import ProviderFactory
from ..text.chapter_selection import (
    format_chapter_selection,
    parse_chapter_indices_csv,
    parse_chapter_selection,
)
from ..text.chunking import Chunker
from ..text.cleaners import TextCleaner
from ..text.segment_planner import TextBudgetSegmentPlanner
from ..text.slug import slugify_audio_title
from ..text.structure import ChapterStructureNormalizer
from ..telemetry.cost_tracker import CostTracker
from ..telemetry.logger import RunLogger
from ..tts.voices import VoiceProfile

_StageResult = TypeVar("_StageResult")


class BookvoicePipeline:
    """Coordinate all stages for a single Bookvoice run."""

    _PHASE_SEQUENCE = (
        "extract",
        "clean",
        "split",
        "chunk",
        "translate",
        "rewrite",
        "tts",
        "merge",
        "manifest",
    )

    def __init__(
        self,
        run_logger: RunLogger | None = None,
        stage_progress_callback: Callable[[str, int, int], None] | None = None,
    ) -> None:
        """Initialize optional runtime logging and progress reporting hooks."""

        self._run_logger = run_logger
        self._stage_progress_callback = stage_progress_callback

    def _prepare_run(self, config: BookvoiceConfig) -> tuple[str, str, ArtifactStore]:
        """Create deterministic run identifiers and artifact storage for a config."""

        self._validate_config(config)
        config_hash = self._config_hash(config)
        run_id = f"run-{config_hash[:12]}"
        store = ArtifactStore(config.output_dir / run_id)
        return run_id, config_hash, store

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
            normalized_structure = ChapterStructureNormalizer().from_chapters(
                chapters=chapters,
                source="text_heuristic",
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

    def _extract(self, config: BookvoiceConfig) -> str:
        """Extract raw text from the configured PDF input."""

        try:
            extractor = PdfTextExtractor()
            return extractor.extract(config.input_pdf)
        except PipelineStageError:
            raise
        except Exception as exc:
            raise PipelineStageError(
                stage="extract",
                detail=f"Failed to extract text from PDF `{config.input_pdf}`: {exc}",
                hint="Verify the input file exists and `pdftotext` is installed.",
            ) from exc

    def _clean(self, raw_text: str) -> str:
        """Apply deterministic cleanup and normalization rules."""

        try:
            cleaner = TextCleaner()
            return cleaner.clean(raw_text).strip()
        except PipelineStageError:
            raise
        except Exception as exc:
            raise PipelineStageError(
                stage="clean",
                detail=f"Failed to normalize extracted text: {exc}",
                hint="Inspect `text/raw.txt` and verify it contains readable UTF-8 text.",
            ) from exc

    def _split_chapters(
        self, text: str, source_pdf: Path
    ) -> tuple[list[Chapter], str, str]:
        """Split chapters using PDF outline first, then deterministic text fallback."""

        fallback_reason = "outline_invalid"
        try:
            outline_result = PdfOutlineChapterExtractor().extract(source_pdf)
            if outline_result.chapters:
                return outline_result.chapters, "pdf_outline", ""
            fallback_reason = outline_result.status
        except Exception:
            fallback_reason = "outline_invalid"

        try:
            splitter = ChapterSplitter()
            chapters = splitter.split(text)
            return chapters, "text_heuristic", fallback_reason
        except PipelineStageError:
            raise
        except Exception as exc:
            raise PipelineStageError(
                stage="split",
                detail=f"Failed to split chapters: {exc}",
                hint="Inspect cleaned text formatting in `text/clean.txt` and PDF outline metadata.",
            ) from exc

    def _extract_normalized_structure(
        self,
        chapters: list[Chapter],
        chapter_source: str,
        source_pdf: Path,
    ) -> list[ChapterStructureUnit]:
        """Extract deterministic chapter/subchapter structure for downstream planning."""

        if chapter_source == "pdf_outline":
            try:
                outline_structure = PdfOutlineChapterExtractor().extract_structure(source_pdf)
                if outline_structure.units:
                    return outline_structure.units
            except Exception:
                pass

        return ChapterStructureNormalizer().from_chapters(
            chapters=chapters,
            source="text_heuristic",
        )

    def _resolve_chapter_scope(
        self, chapters: list[Chapter], chapter_selection: str | None
    ) -> tuple[list[Chapter], dict[str, str]]:
        """Resolve selected chapters for a run from chapter selection expression."""

        available_indices = [chapter.index for chapter in chapters]
        try:
            selected_indices = parse_chapter_selection(chapter_selection, available_indices)
        except ValueError as exc:
            raise PipelineStageError(
                stage="chapter-selection",
                detail=str(exc),
                hint=(
                    "Use `--chapters` syntax like `5`, `1,3,7`, `2-4`, or mixed `1,3-5`."
                ),
            ) from exc

        chapter_scope = self._build_chapter_scope_metadata(
            available_indices=available_indices,
            selected_indices=selected_indices,
            selection_input=chapter_selection,
        )
        selected_set = set(selected_indices)
        selected_chapters = sorted(
            (chapter for chapter in chapters if chapter.index in selected_set),
            key=lambda chapter: chapter.index,
        )
        return selected_chapters, chapter_scope

    def _resolve_resume_chapter_scope(
        self, chapters: list[Chapter], extra: dict[str, object]
    ) -> tuple[list[Chapter], dict[str, str]]:
        """Resolve selected chapters for resume from persisted manifest metadata."""

        available_indices = [chapter.index for chapter in chapters]
        selected_indices = available_indices
        selection_input = ""

        raw_indices_csv = extra.get("chapter_scope_indices_csv")
        if isinstance(raw_indices_csv, str) and raw_indices_csv.strip():
            try:
                selected_indices = parse_chapter_indices_csv(raw_indices_csv, available_indices)
            except ValueError as exc:
                raise PipelineStageError(
                    stage="resume-artifacts",
                    detail=f"Invalid chapter scope metadata in manifest: {exc}",
                    hint="Regenerate run artifacts or rerun `bookvoice build`.",
                ) from exc
            selection_input = format_chapter_selection(selected_indices)
        else:
            raw_selection_input = extra.get("chapter_scope_selection_input")
            if (
                isinstance(raw_selection_input, str)
                and raw_selection_input.strip()
                and raw_selection_input.strip().lower() != "all"
            ):
                selection_input = raw_selection_input.strip()
                try:
                    selected_indices = parse_chapter_selection(selection_input, available_indices)
                except ValueError as exc:
                    raise PipelineStageError(
                        stage="resume-artifacts",
                        detail=f"Invalid chapter scope metadata in manifest: {exc}",
                        hint="Regenerate run artifacts or rerun `bookvoice build`.",
                    ) from exc

        chapter_scope = self._build_chapter_scope_metadata(
            available_indices=available_indices,
            selected_indices=selected_indices,
            selection_input=selection_input or None,
        )
        selected_set = set(selected_indices)
        selected_chapters = sorted(
            (chapter for chapter in chapters if chapter.index in selected_set),
            key=lambda chapter: chapter.index,
        )
        return selected_chapters, chapter_scope

    def _build_chapter_scope_metadata(
        self,
        available_indices: list[int],
        selected_indices: list[int],
        selection_input: str | None,
    ) -> dict[str, str]:
        """Build string metadata describing selected chapter scope for artifacts."""

        available_unique = sorted(set(int(index) for index in available_indices))
        selected_unique = sorted(set(int(index) for index in selected_indices))
        is_all_scope = selected_unique == available_unique
        selection_label = "all" if is_all_scope else format_chapter_selection(selected_unique)
        return {
            "chapter_scope_mode": "all" if is_all_scope else "selected",
            "chapter_scope_label": selection_label,
            "chapter_scope_selection_input": (
                "all"
                if is_all_scope
                else (selection_input.strip() if isinstance(selection_input, str) else "")
            ),
            "chapter_scope_indices_csv": ",".join(str(index) for index in selected_unique),
            "chapter_scope_available_indices_csv": ",".join(
                str(index) for index in available_unique
            ),
            "chapter_scope_selected_count": str(len(selected_unique)),
            "chapter_scope_available_count": str(len(available_unique)),
        }

    def _chunk(
        self,
        chapters: list[Chapter],
        normalized_structure: list[ChapterStructureUnit],
        config: BookvoiceConfig,
    ) -> tuple[list[Chunk], dict[str, object]]:
        """Plan deterministic chapter parts from structure units."""

        try:
            selected_units = self._selected_structure_units(chapters, normalized_structure)
            planner = TextBudgetSegmentPlanner()

            if selected_units:
                plan = planner.plan(selected_units, budget_chars=config.chunk_size_chars)
                chunks = planner.to_chunks(plan)
                metadata = {
                    "planner": {
                        "strategy": "text_budget_segment_planner",
                        "budget_chars": plan.budget_chars,
                        "budget_ceiling_chars": plan.budget_ceiling_chars,
                        "segment_count": len(plan.segments),
                        "source_structure_unit_count": len(selected_units),
                        "source_structure_order_indices": [
                            unit.order_index for unit in selected_units
                        ],
                    }
                }
                return chunks, metadata

            fallback_chunks = self._decorate_chunks_with_part_metadata(
                chunks=Chunker().to_chunks(chapters, target_size=config.chunk_size_chars),
                chapters=chapters,
            )
            fallback_metadata = {
                "planner": {
                    "strategy": "chunker_fallback",
                    "budget_chars": config.chunk_size_chars,
                    "budget_ceiling_chars": config.chunk_size_chars,
                    "segment_count": len(fallback_chunks),
                    "source_structure_unit_count": 0,
                    "source_structure_order_indices": [],
                }
            }
            return fallback_chunks, fallback_metadata
        except PipelineStageError:
            raise
        except Exception as exc:
            raise PipelineStageError(
                stage="chunk",
                detail=f"Failed to chunk chapters: {exc}",
                hint="Verify chapter artifacts are well-formed and chunk size is positive.",
            ) from exc

    def _selected_structure_units(
        self,
        chapters: list[Chapter],
        normalized_structure: list[ChapterStructureUnit],
    ) -> list[ChapterStructureUnit]:
        """Filter normalized structure units to currently selected chapters."""

        selected_indices = {chapter.index for chapter in chapters}
        units = [unit for unit in normalized_structure if unit.chapter_index in selected_indices]
        return sorted(units, key=lambda item: (item.chapter_index, item.order_index))

    def _decorate_chunks_with_part_metadata(
        self,
        chunks: list[Chunk],
        chapters: list[Chapter],
    ) -> list[Chunk]:
        """Attach deterministic part metadata when chunker fallback is used."""

        chapter_titles = {chapter.index: chapter.title for chapter in chapters}
        decorated: list[Chunk] = []
        for chunk in chunks:
            part_title = chapter_titles.get(chunk.chapter_index, f"Chapter {chunk.chapter_index}")
            part_index = chunk.chunk_index + 1
            part_slug = slugify_audio_title(part_title)
            decorated.append(
                Chunk(
                    chapter_index=chunk.chapter_index,
                    chunk_index=chunk.chunk_index,
                    text=chunk.text,
                    char_start=chunk.char_start,
                    char_end=chunk.char_end,
                    part_index=part_index,
                    part_title=part_title,
                    part_id=f"{chunk.chapter_index:03d}_{part_index:02d}_{part_slug}",
                    source_order_indices=tuple(),
                    boundary_strategy=chunk.boundary_strategy,
                )
            )
        return decorated

    def _translate(
        self, chunks: list[Chunk], config: BookvoiceConfig
    ) -> list[TranslationResult]:
        """Translate chunks into target-language text."""

        try:
            runtime_config = self._resolve_runtime_config(config)
            translator = ProviderFactory.create_translator(
                provider_id=runtime_config.translator_provider,
                model=runtime_config.translate_model,
                api_key=runtime_config.api_key,
            )
            return [
                translator.translate(chunk, target_language=config.language)
                for chunk in chunks
            ]
        except OpenAIProviderError as exc:
            raise PipelineStageError(
                stage="translate",
                detail=str(exc),
                hint=(
                    "Verify `OPENAI_API_KEY` or `bookvoice credentials`, then confirm "
                    "the translation model/provider configuration."
                ),
            ) from exc
        except PipelineStageError:
            raise
        except Exception as exc:
            raise PipelineStageError(
                stage="translate",
                detail=f"Failed to translate chunks: {exc}",
                hint="Check translator provider configuration and language settings.",
            ) from exc

    def _rewrite_for_audio(
        self,
        translations: list[TranslationResult],
        config: BookvoiceConfig,
        runtime_config: ProviderRuntimeConfig | None = None,
    ) -> list[RewriteResult]:
        """Rewrite translated text for natural spoken delivery."""

        try:
            resolved_runtime = (
                runtime_config
                if runtime_config is not None
                else self._resolve_runtime_config(config)
            )
            if resolved_runtime.rewrite_bypass:
                bypass_rewriter = DeterministicBypassRewriter()
                return [bypass_rewriter.rewrite(translation) for translation in translations]
            rewriter = ProviderFactory.create_rewriter(
                provider_id=resolved_runtime.rewriter_provider,
                model=resolved_runtime.rewrite_model,
                api_key=resolved_runtime.api_key,
            )
            return [rewriter.rewrite(translation) for translation in translations]
        except OpenAIProviderError as exc:
            raise PipelineStageError(
                stage="rewrite",
                detail=str(exc),
                hint=(
                    "Verify API key/model settings, or rerun with `--rewrite-bypass` for "
                    "deterministic pass-through rewrite output."
                ),
            ) from exc
        except PipelineStageError:
            raise
        except Exception as exc:
            raise PipelineStageError(
                stage="rewrite",
                detail=f"Failed to rewrite translated text for audio: {exc}",
                hint="Check translator outputs and rewrite provider configuration.",
            ) from exc

    def _tts(
        self,
        rewrites: list[RewriteResult],
        config: BookvoiceConfig,
        store: ArtifactStore,
        runtime_config: ProviderRuntimeConfig | None = None,
    ) -> list[AudioPart]:
        """Synthesize audio parts for rewritten text chunks."""

        try:
            resolved_runtime = (
                runtime_config
                if runtime_config is not None
                else self._resolve_runtime_config(config)
            )
            voice = VoiceProfile(
                name=resolved_runtime.tts_voice,
                provider_voice_id=resolved_runtime.tts_voice,
                language=config.language,
                speaking_rate=1.0,
            )
            synthesizer = ProviderFactory.create_tts_synthesizer(
                provider_id=resolved_runtime.tts_provider,
                output_root=store.root / "audio/chunks",
                model=resolved_runtime.tts_model,
                api_key=resolved_runtime.api_key,
            )
            return [synthesizer.synthesize(item, voice) for item in rewrites]
        except OpenAIProviderError as exc:
            raise PipelineStageError(
                stage="tts",
                detail=str(exc),
                hint=(
                    "Verify `OPENAI_API_KEY` or `bookvoice credentials`, then confirm "
                    "the TTS model/voice/provider configuration."
                ),
            ) from exc
        except PipelineStageError:
            raise
        except Exception as exc:
            raise PipelineStageError(
                stage="tts",
                detail=f"Failed to synthesize audio parts: {exc}",
                hint="Check TTS provider configuration and output directory permissions.",
            ) from exc

    def _postprocess(
        self, audio_parts: list[AudioPart], config: BookvoiceConfig
    ) -> list[AudioPart]:
        """Apply postprocessing to synthesized audio parts."""

        try:
            _ = config
            postprocessor = AudioPostProcessor()
            processed: list[AudioPart] = []
            for part in audio_parts:
                normalized = postprocessor.normalize(part.path)
                trimmed = postprocessor.trim_silence(normalized)
                processed.append(
                    AudioPart(
                        chapter_index=part.chapter_index,
                        chunk_index=part.chunk_index,
                        path=trimmed,
                        duration_seconds=part.duration_seconds,
                        part_index=part.part_index,
                        part_title=part.part_title,
                        part_id=part.part_id,
                        source_order_indices=part.source_order_indices,
                        provider=part.provider,
                        model=part.model,
                        voice=part.voice,
                    )
                )
            return processed
        except PipelineStageError:
            raise
        except Exception as exc:
            raise PipelineStageError(
                stage="postprocess",
                detail=f"Failed to postprocess synthesized audio: {exc}",
                hint="Verify generated chunk WAV files are readable.",
            ) from exc

    def _merge(
        self,
        audio_parts: list[AudioPart],
        config: BookvoiceConfig,
        store: ArtifactStore,
        output_path: Path | None = None,
    ) -> Path:
        """Merge chapter or book-level audio outputs."""

        try:
            _ = config
            merger = AudioMerger()
            return merger.merge(
                audio_parts,
                output_path=(
                    output_path
                    if output_path is not None
                    else store.root / "audio/bookvoice_merged.wav"
                ),
            )
        except PipelineStageError:
            raise
        except Exception as exc:
            raise PipelineStageError(
                stage="merge",
                detail=f"Failed to merge audio outputs: {exc}",
                hint="Check synthesized part files and output directory permissions.",
            ) from exc

    def _merged_output_path_for_scope(
        self, store: ArtifactStore, chapter_scope: dict[str, str]
    ) -> Path:
        """Compute deterministic merged output path for full or selected scope."""

        scope_mode = chapter_scope.get("chapter_scope_mode", "all")
        if scope_mode == "all":
            return store.root / "audio/bookvoice_merged.wav"
        indices_csv = chapter_scope.get("chapter_scope_indices_csv", "")
        suffix = (
            indices_csv.replace(",", "_")
            if indices_csv
            else chapter_scope.get("chapter_scope_label", "selected").replace(",", "_")
        )
        return store.root / f"audio/bookvoice_merged.chapters_{suffix}.wav"

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

    def _stage_position(self, stage_name: str) -> tuple[int, int] | None:
        """Return 1-based stage index and total stage count for known stages."""

        try:
            index = self._PHASE_SEQUENCE.index(stage_name) + 1
        except ValueError:
            return None
        return index, len(self._PHASE_SEQUENCE)

    def _on_stage_start(self, stage_name: str) -> None:
        """Emit start events to stage progress callback and structured logger."""

        stage_position = self._stage_position(stage_name)
        if stage_position and self._stage_progress_callback is not None:
            self._stage_progress_callback(stage_name, stage_position[0], stage_position[1])
        if self._run_logger is not None:
            self._run_logger.log_stage_start(stage_name)

    def _on_stage_complete(self, stage_name: str) -> None:
        """Emit stage-complete event to the structured logger."""

        if self._run_logger is not None:
            self._run_logger.log_stage_complete(stage_name)

    def _on_stage_failure(self, stage_name: str, exc: Exception) -> None:
        """Emit stage-failure event with sanitized exception metadata."""

        if self._run_logger is not None:
            self._run_logger.log_stage_failure(stage_name, type(exc).__name__)

    def _run_stage(
        self,
        stage_name: str,
        action: Callable[[], _StageResult],
    ) -> _StageResult:
        """Run one named stage and emit start/complete/failure telemetry events."""

        self._on_stage_start(stage_name)
        try:
            result = action()
        except Exception as exc:
            self._on_stage_failure(stage_name, exc)
            raise
        self._on_stage_complete(stage_name)
        return result
