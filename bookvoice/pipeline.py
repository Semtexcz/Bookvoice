"""Pipeline orchestration for Bookvoice.

Responsibilities:
- Define the high-level stage order for the audiobook build flow.
- Coordinate stage outputs into a reproducible run manifest.

Key types:
- `BookvoicePipeline`: orchestration facade.
- `RunManifest`: immutable record of run inputs and outputs.
"""

from __future__ import annotations

from dataclasses import asdict
from hashlib import sha256
import json
import os
from pathlib import Path

from .audio.merger import AudioMerger
from .audio.postprocess import AudioPostProcessor
from .config import BookvoiceConfig, ProviderRuntimeConfig, RuntimeConfigSources
from .errors import PipelineStageError
from .io.pdf_outline_extractor import PdfOutlineChapterExtractor
from .io.chapter_splitter import ChapterSplitter
from .io.pdf_text_extractor import PdfTextExtractor
from .io.storage import ArtifactStore
from .models.datatypes import (
    AudioPart,
    BookMeta,
    Chapter,
    Chunk,
    RewriteResult,
    RunManifest,
    TranslationResult,
)
from .provider_factory import ProviderFactory
from .text.chapter_selection import (
    format_chapter_selection,
    parse_chapter_indices_csv,
    parse_chapter_selection,
)
from .text.chunking import Chunker
from .text.cleaners import TextCleaner
from .telemetry.cost_tracker import CostTracker
from .tts.voices import VoiceProfile


class BookvoicePipeline:
    """Coordinate all stages for a single Bookvoice run."""

    _TRANSLATE_COST_PER_1K_CHARS_USD = 0.0015
    _REWRITE_COST_PER_1K_CHARS_USD = 0.0008
    _TTS_COST_PER_1K_CHARS_USD = 0.0150

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
            chapters = self._load_chapters(chapters_artifact)
            metadata = self._load_chapter_metadata(chapters_artifact)
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
        """Run the full pipeline and return a manifest.

        MVP orchestration for text-native PDF to playable audio.
        """

        run_id, config_hash, store = self._prepare_run(config)
        runtime_config = self._resolve_runtime_config(config)
        cost_tracker = CostTracker()

        raw_text = self._extract(config)
        raw_text_path = store.save_text(Path("text/raw.txt"), raw_text)

        clean_text = self._clean(raw_text)
        clean_text_path = store.save_text(Path("text/clean.txt"), clean_text)

        chapters, chapter_source, chapter_fallback_reason = self._split_chapters(
            clean_text, config.input_pdf
        )
        selected_chapters, chapter_scope = self._resolve_chapter_scope(
            chapters, config.chapter_selection
        )
        chapters_path = store.save_json(
            Path("text/chapters.json"),
            self._chapter_artifact_payload(
                chapters, chapter_source, chapter_fallback_reason, chapter_scope
            ),
        )

        chunks = self._chunk(selected_chapters, config)
        chunks_path = store.save_json(
            Path("text/chunks.json"),
            {
                "chunks": [asdict(chunk) for chunk in chunks],
                "metadata": {"chapter_scope": chapter_scope},
            },
        )

        translations = self._translate(chunks, config)
        self._add_translation_costs(translations, cost_tracker)
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

        rewrites = self._rewrite_for_audio(translations, config, runtime_config)
        self._add_rewrite_costs(rewrites, cost_tracker)
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
                    "provider": runtime_config.rewriter_provider,
                    "model": runtime_config.rewrite_model,
                },
            },
        )

        audio_parts = self._tts(rewrites, config, store, runtime_config)
        self._add_tts_costs(rewrites, cost_tracker)
        audio_parts_path = store.save_json(
            Path("audio/parts.json"),
            {
                "audio_parts": [
                    {
                        "chapter_index": item.chapter_index,
                        "chunk_index": item.chunk_index,
                        "path": str(item.path),
                        "duration_seconds": item.duration_seconds,
                    }
                    for item in audio_parts
                ],
                "metadata": {
                    "chapter_scope": chapter_scope,
                    "provider": runtime_config.tts_provider,
                    "model": runtime_config.tts_model,
                    "voice": runtime_config.tts_voice,
                },
            },
        )

        processed = self._postprocess(audio_parts, config)
        merged_path = self._merge(
            processed,
            config,
            store,
            output_path=self._merged_output_path_for_scope(store, chapter_scope),
        )
        manifest = self._write_manifest(
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
                "chapter_source": chapter_source,
                "chapter_fallback_reason": chapter_fallback_reason,
                **runtime_config.as_manifest_metadata(),
                **chapter_scope,
            },
            cost_summary=self._rounded_cost_summary(cost_tracker),
            store=store,
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
            self._chapter_artifact_payload(
                chapters, chapter_source, chapter_fallback_reason, chapter_scope
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

        payload = self._load_manifest_payload(manifest_path)
        run_id = self._require_manifest_field(payload, "run_id")
        config_hash = self._require_manifest_field(payload, "config_hash")

        book_payload = payload.get("book")
        if not isinstance(book_payload, dict):
            raise ValueError(
                "Manifest is missing required object `book`; run `bookvoice build` again "
                "or provide a valid manifest."
            )
        source_pdf_value = self._require_manifest_field(book_payload, "source_pdf", scope="book")
        language_value = self._require_manifest_field(book_payload, "language", scope="book")

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

        run_root = self._resolve_run_root(manifest_path, extra)
        store = ArtifactStore(run_root)
        config = BookvoiceConfig(
            input_pdf=source_pdf,
            output_dir=run_root.parent,
            language=language,
            provider_translator=self._manifest_string(extra, "provider_translator", "openai"),
            provider_rewriter=self._manifest_string(extra, "provider_rewriter", "openai"),
            provider_tts=self._manifest_string(extra, "provider_tts", "openai"),
            model_translate=self._manifest_string(extra, "model_translate", "gpt-4.1-mini"),
            model_rewrite=self._manifest_string(extra, "model_rewrite", "gpt-4.1-mini"),
            model_tts=self._manifest_string(extra, "model_tts", "gpt-4o-mini-tts"),
            tts_voice=self._manifest_string(extra, "tts_voice", "alloy"),
            resume=True,
        )
        runtime_config = self._resolve_runtime_config(config)

        raw_text_path = self._resolve_artifact_path(
            manifest_path, run_root, extra, "raw_text", Path("text/raw.txt")
        )
        clean_text_path = self._resolve_artifact_path(
            manifest_path, run_root, extra, "clean_text", Path("text/clean.txt")
        )
        chapters_path = self._resolve_artifact_path(
            manifest_path, run_root, extra, "chapters", Path("text/chapters.json")
        )
        chunks_path = self._resolve_artifact_path(
            manifest_path, run_root, extra, "chunks", Path("text/chunks.json")
        )
        translations_path = self._resolve_artifact_path(
            manifest_path, run_root, extra, "translations", Path("text/translations.json")
        )
        rewrites_path = self._resolve_artifact_path(
            manifest_path, run_root, extra, "rewrites", Path("text/rewrites.json")
        )
        audio_parts_path = self._resolve_artifact_path(
            manifest_path, run_root, extra, "audio_parts", Path("audio/parts.json")
        )
        merged_path = self._resolve_merged_path(manifest_path, run_root, payload)

        next_stage = self._detect_next_stage(
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
            chapters = self._load_chapters(chapters_path)
            chapter_metadata = self._load_chapter_metadata(chapters_path)
            if chapter_metadata["source"]:
                chapter_source = chapter_metadata["source"]
            chapter_fallback_reason = chapter_metadata["fallback_reason"]
        else:
            chapters, chapter_source, chapter_fallback_reason = self._split_chapters(
                clean_text, config.input_pdf
            )
            _, chapter_scope = self._resolve_resume_chapter_scope(chapters, extra)
            chapters_path = store.save_json(
                Path("text/chapters.json"),
                self._chapter_artifact_payload(
                    chapters, chapter_source, chapter_fallback_reason, chapter_scope
                ),
            )
        selected_chapters, chapter_scope = self._resolve_resume_chapter_scope(chapters, extra)

        if chunks_path.exists():
            chunks = self._load_chunks(chunks_path)
        else:
            chunks = self._chunk(selected_chapters, config)
            chunks_path = store.save_json(
                Path("text/chunks.json"),
                {
                    "chunks": [asdict(chunk) for chunk in chunks],
                    "metadata": {"chapter_scope": chapter_scope},
                },
            )

        if translations_path.exists():
            translations = self._load_translations(translations_path)
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
        self._add_translation_costs(translations, cost_tracker)

        if rewrites_path.exists():
            rewrites = self._load_rewrites(rewrites_path)
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
                        "provider": runtime_config.rewriter_provider,
                        "model": runtime_config.rewrite_model,
                    },
                },
            )
        self._add_rewrite_costs(rewrites, cost_tracker)

        reuse_audio_parts = False
        if audio_parts_path.exists():
            loaded_parts = self._load_audio_parts(audio_parts_path)
            if all(part.path.exists() for part in loaded_parts):
                audio_parts = loaded_parts
                reuse_audio_parts = True
            else:
                audio_parts = self._tts(rewrites, config, store, runtime_config)
                audio_parts_path = store.save_json(
                    Path("audio/parts.json"),
                    {
                        "audio_parts": [
                            {
                                "chapter_index": item.chapter_index,
                                "chunk_index": item.chunk_index,
                                "path": str(item.path),
                                "duration_seconds": item.duration_seconds,
                            }
                            for item in audio_parts
                        ],
                        "metadata": {
                            "chapter_scope": chapter_scope,
                            "provider": runtime_config.tts_provider,
                            "model": runtime_config.tts_model,
                            "voice": runtime_config.tts_voice,
                        },
                    },
                )
        else:
            audio_parts = self._tts(rewrites, config, store, runtime_config)
            audio_parts_path = store.save_json(
                Path("audio/parts.json"),
                {
                    "audio_parts": [
                        {
                            "chapter_index": item.chapter_index,
                            "chunk_index": item.chunk_index,
                            "path": str(item.path),
                            "duration_seconds": item.duration_seconds,
                            }
                            for item in audio_parts
                        ],
                        "metadata": {
                            "chapter_scope": chapter_scope,
                            "provider": runtime_config.tts_provider,
                            "model": runtime_config.tts_model,
                            "voice": runtime_config.tts_voice,
                        },
                    },
                )
        self._add_tts_costs(rewrites, cost_tracker)

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
                "resume_next_stage": next_stage,
                "chapter_source": chapter_source,
                "chapter_fallback_reason": chapter_fallback_reason,
                **runtime_config.as_manifest_metadata(),
                **chapter_scope,
            },
            cost_summary=self._rounded_cost_summary(cost_tracker),
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

    def _chapter_artifact_payload(
        self,
        chapters: list[Chapter],
        source: str,
        fallback_reason: str,
        chapter_scope: dict[str, str],
    ) -> dict[str, object]:
        """Serialize chapter artifacts with extraction metadata for resume and diagnostics."""

        return {
            "chapters": [asdict(chapter) for chapter in chapters],
            "metadata": {
                "source": source,
                "fallback_reason": fallback_reason,
                "chapter_scope": chapter_scope,
            },
        }

    def _resolve_chapter_scope(
        self, chapters: list[Chapter], chapter_selection: str | None
    ) -> tuple[list[Chapter], dict[str, str]]:
        """Resolve selected chapters for a run from user chapter selection expression."""

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
                selected_indices = parse_chapter_indices_csv(
                    raw_indices_csv, available_indices
                )
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
                    selected_indices = parse_chapter_selection(
                        selection_input, available_indices
                    )
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

    def _chunk(self, chapters: list[Chapter], config: BookvoiceConfig) -> list[Chunk]:
        """Convert chapters into chunk-sized text units."""

        try:
            chunker = Chunker()
            return chunker.to_chunks(chapters, target_size=config.chunk_size_chars)
        except PipelineStageError:
            raise
        except Exception as exc:
            raise PipelineStageError(
                stage="chunk",
                detail=f"Failed to chunk chapters: {exc}",
                hint="Verify chapter artifacts are well-formed and chunk size is positive.",
            ) from exc

    def _translate(
        self, chunks: list[Chunk], config: BookvoiceConfig
    ) -> list[TranslationResult]:
        """Translate chunks into target language text."""

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
            rewriter = ProviderFactory.create_rewriter(
                provider_id=resolved_runtime.rewriter_provider,
                model=resolved_runtime.rewrite_model,
                api_key=resolved_runtime.api_key,
            )
            return [rewriter.rewrite(translation) for translation in translations]
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
        """Compute deterministic merged output path for full or selected chapter scope."""

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
        """Build a run manifest with deterministic identifiers."""

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
            manifest_path = store.save_json(
                Path("run_manifest.json"),
                self._manifest_payload(manifest),
            )
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

    def _manifest_payload(self, manifest: RunManifest) -> dict[str, object]:
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

    def _add_translation_costs(
        self, translations: list[TranslationResult], cost_tracker: CostTracker
    ) -> None:
        """Accumulate deterministic LLM cost estimate for translation stage."""

        for item in translations:
            source_chars = len(item.chunk.text)
            translated_chars = len(item.translated_text)
            billable_chars = max(1, source_chars + translated_chars)
            cost_tracker.add_llm_usage(
                (billable_chars / 1000.0) * self._TRANSLATE_COST_PER_1K_CHARS_USD
            )

    def _add_rewrite_costs(
        self, rewrites: list[RewriteResult], cost_tracker: CostTracker
    ) -> None:
        """Accumulate deterministic LLM cost estimate for rewrite stage."""

        for item in rewrites:
            input_chars = len(item.translation.translated_text)
            output_chars = len(item.rewritten_text)
            billable_chars = max(1, input_chars + output_chars)
            cost_tracker.add_llm_usage(
                (billable_chars / 1000.0) * self._REWRITE_COST_PER_1K_CHARS_USD
            )

    def _add_tts_costs(self, rewrites: list[RewriteResult], cost_tracker: CostTracker) -> None:
        """Accumulate deterministic TTS cost estimate for synthesis stage."""

        for item in rewrites:
            billable_chars = max(1, len(item.rewritten_text))
            cost_tracker.add_tts_usage(
                (billable_chars / 1000.0) * self._TTS_COST_PER_1K_CHARS_USD
            )

    def _rounded_cost_summary(self, cost_tracker: CostTracker) -> dict[str, float]:
        """Return cost summary rounded for stable JSON and CLI display."""

        summary = cost_tracker.summary()
        llm_cost_usd = round(summary["llm_cost_usd"], 6)
        tts_cost_usd = round(summary["tts_cost_usd"], 6)
        return {
            "llm_cost_usd": llm_cost_usd,
            "tts_cost_usd": tts_cost_usd,
            "total_cost_usd": round(llm_cost_usd + tts_cost_usd, 6),
        }

    def _validate_config(self, config: BookvoiceConfig) -> None:
        """Validate top-level configuration and map failures to a stage-aware error."""

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
            runtime_sources = RuntimeConfigSources(env=os.environ)
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

    def _manifest_string(
        self, payload: dict[str, object], key: str, default_value: str
    ) -> str:
        """Read a non-empty string from manifest extras with a deterministic default."""

        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        return default_value

    def _load_manifest_payload(self, manifest_path: Path) -> dict[str, object]:
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

    def _require_manifest_field(
        self, payload: dict[str, object], key: str, scope: str = "manifest"
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

    def _resolve_run_root(self, manifest_path: Path, extra: dict[str, object]) -> Path:
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

    def _resolve_merged_path(
        self, manifest_path: Path, run_root: Path, payload: dict[str, object]
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

    def _resolve_artifact_path(
        self,
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

    def _detect_next_stage(
        self,
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

    def _load_json_object(self, path: Path) -> dict[str, object]:
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

    def _load_chapters(self, path: Path) -> list[Chapter]:
        """Load chapter artifacts from JSON."""

        payload = self._load_json_object(path)
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

    def _load_chapter_metadata(self, path: Path) -> dict[str, str]:
        """Load chapter extraction metadata from chapter artifacts."""

        payload = self._load_json_object(path)
        metadata = payload.get("metadata")
        if not isinstance(metadata, dict):
            return {"source": "", "fallback_reason": ""}
        source = metadata.get("source")
        fallback_reason = metadata.get("fallback_reason")
        return {
            "source": str(source) if isinstance(source, str) else "",
            "fallback_reason": (
                str(fallback_reason) if isinstance(fallback_reason, str) else ""
            ),
        }

    def _load_chunks(self, path: Path) -> list[Chunk]:
        """Load chunk artifacts from JSON."""

        payload = self._load_json_object(path)
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
            chunks.append(
                Chunk(
                    chapter_index=int(item["chapter_index"]),
                    chunk_index=int(item["chunk_index"]),
                    text=str(item["text"]),
                    char_start=int(item["char_start"]),
                    char_end=int(item["char_end"]),
                )
            )
        return chunks

    def _load_translations(self, path: Path) -> list[TranslationResult]:
        """Load translation artifacts from JSON."""

        payload = self._load_json_object(path)
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
            chunk = Chunk(
                chapter_index=int(chunk_payload["chapter_index"]),
                chunk_index=int(chunk_payload["chunk_index"]),
                text=str(chunk_payload["text"]),
                char_start=int(chunk_payload["char_start"]),
                char_end=int(chunk_payload["char_end"]),
            )
            translations.append(
                TranslationResult(
                    chunk=chunk,
                    translated_text=str(item["translated_text"]),
                    provider=str(item["provider"]),
                    model=str(item["model"]),
                )
            )
        return translations

    def _load_rewrites(self, path: Path) -> list[RewriteResult]:
        """Load rewrite artifacts from JSON."""

        payload = self._load_json_object(path)
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
            chunk = Chunk(
                chapter_index=int(chunk_payload["chapter_index"]),
                chunk_index=int(chunk_payload["chunk_index"]),
                text=str(chunk_payload["text"]),
                char_start=int(chunk_payload["char_start"]),
                char_end=int(chunk_payload["char_end"]),
            )
            translation = TranslationResult(
                chunk=chunk,
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

    def _load_audio_parts(self, path: Path) -> list[AudioPart]:
        """Load synthesized audio part artifacts from JSON."""

        payload = self._load_json_object(path)
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
                )
            )
        return audio_parts

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
            "chunk_size_chars": config.chunk_size_chars,
            "chapter_selection": config.chapter_selection,
            "resume": config.resume,
            "extra": dict(config.extra),
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return sha256(canonical.encode("utf-8")).hexdigest()
