"""Core stage execution helpers for Bookvoice pipeline.

Responsibilities:
- Execute deterministic extract/clean/split/chunk content stages.
- Execute provider-driven translate/rewrite/tts stages.
- Execute postprocess/merge audio stages and output-path derivation.
"""

from __future__ import annotations

from pathlib import Path

from ..audio.merger import AudioMerger
from ..audio.postprocess import AudioPostProcessor
from ..config import BookvoiceConfig, ProviderRuntimeConfig
from ..errors import PipelineStageError
from ..io.chapter_splitter import ChapterSplitter
from ..io.pdf_outline_extractor import PdfOutlineChapterExtractor
from ..io.pdf_text_extractor import PdfTextExtractor
from ..io.storage import ArtifactStore
from ..llm.audio_rewriter import DeterministicBypassRewriter
from ..llm.openai_client import OpenAIProviderError
from ..models.datatypes import (
    AudioPart,
    Chapter,
    ChapterStructureUnit,
    Chunk,
    RewriteResult,
    TranslationResult,
)
from ..provider_factory import ProviderFactory
from ..text.chunking import Chunker
from ..text.cleaners import TextCleaner
from ..text.segment_planner import TextBudgetSegmentPlanner
from ..text.slug import slugify_audio_title
from ..text.structure import ChapterStructureNormalizer
from ..tts.voices import VoiceProfile


class PipelineExecutionMixin:
    """Provide stage-level pipeline helper methods."""

    @staticmethod
    def _provider_error_detail(stage: str, exc: OpenAIProviderError) -> str:
        """Build concise stage-scoped detail text for provider-backed failures."""

        _ = stage
        mapping = {
            "invalid_api_key": "Provider authentication failed for OpenAI API credentials.",
            "insufficient_quota": "Provider quota is insufficient for this OpenAI request.",
            "invalid_model": "Provider rejected the configured model for this request.",
            "timeout": "Provider request timed out before completion.",
            "transport": "Provider request failed due to a transport/network error.",
        }
        return mapping.get(exc.failure_kind, str(exc))

    @staticmethod
    def _provider_error_hint(stage: str, exc: OpenAIProviderError) -> str:
        """Build actionable user hints for stage-specific provider failure kinds."""

        kind = exc.failure_kind
        if kind == "invalid_api_key":
            return (
                "Set a valid API key via `bookvoice credentials` or pass one-time "
                "`--api-key` / `--prompt-api-key`."
            )
        if kind == "insufficient_quota":
            if stage == "rewrite":
                return (
                    "Check OpenAI billing/quota for this project, then retry. "
                    "For one-off runs, you can use `--rewrite-bypass`."
                )
            return "Check OpenAI billing/quota for this project, then retry the command."
        if kind == "invalid_model":
            stage_model_hint = {
                "translate": "Use `--model-translate` with an available chat model.",
                "rewrite": (
                    "Use `--model-rewrite` with an available chat model, "
                    "or run with `--rewrite-bypass`."
                ),
                "tts": "Use `--model-tts` with an available TTS model.",
            }
            return stage_model_hint.get(
                stage,
                "Use a valid model identifier for the configured provider.",
            )
        if kind == "timeout":
            return "Retry the command. If timeouts persist, verify network stability."
        if kind == "transport":
            return "Check internet/proxy connectivity and retry the command."

        fallback = {
            "translate": (
                "Verify API key and translation model/provider configuration, then retry."
            ),
            "rewrite": (
                "Verify API key and rewrite model/provider configuration, "
                "or use `--rewrite-bypass`."
            ),
            "tts": "Verify API key plus TTS model/voice/provider configuration, then retry.",
        }
        return fallback.get(stage, "Verify provider configuration and retry the command.")

    def _provider_stage_error(self, stage: str, exc: OpenAIProviderError) -> PipelineStageError:
        """Convert provider exception metadata into a stage-aware pipeline error."""

        return PipelineStageError(
            stage=stage,
            detail=self._provider_error_detail(stage, exc),
            hint=self._provider_error_hint(stage, exc),
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
            raise self._provider_stage_error("translate", exc) from exc
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
            raise self._provider_stage_error("rewrite", exc) from exc
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
            raise self._provider_stage_error("tts", exc) from exc
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
