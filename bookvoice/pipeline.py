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
from pathlib import Path

from .audio.merger import AudioMerger
from .audio.postprocess import AudioPostProcessor
from .config import BookvoiceConfig
from .io.chapter_splitter import ChapterSplitter
from .io.pdf_text_extractor import PdfTextExtractor
from .io.storage import ArtifactStore
from .llm.audio_rewriter import AudioRewriter
from .llm.translator import OpenAITranslator
from .models.datatypes import (
    AudioPart,
    BookMeta,
    Chapter,
    Chunk,
    RewriteResult,
    RunManifest,
    TranslationResult,
)
from .text.chunking import Chunker
from .text.cleaners import TextCleaner
from .tts.synthesizer import OpenAITTSSynthesizer
from .tts.voices import VoiceProfile


class BookvoicePipeline:
    """Coordinate all stages for a single Bookvoice run."""

    def run(self, config: BookvoiceConfig) -> RunManifest:
        """Run the full pipeline and return a manifest.

        MVP orchestration for text-native PDF to playable audio.
        """

        config_hash = self._config_hash(config)
        run_id = f"run-{config_hash[:12]}"
        store = ArtifactStore(config.output_dir / run_id)

        raw_text = self._extract(config)
        raw_text_path = store.save_text(Path("text/raw.txt"), raw_text)

        clean_text = self._clean(raw_text)
        clean_text_path = store.save_text(Path("text/clean.txt"), clean_text)

        chapters = self._split_chapters(clean_text)
        chapters_path = store.save_json(
            Path("text/chapters.json"),
            {"chapters": [asdict(chapter) for chapter in chapters]},
        )

        chunks = self._chunk(chapters, config)
        chunks_path = store.save_json(
            Path("text/chunks.json"),
            {"chunks": [asdict(chunk) for chunk in chunks]},
        )

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
                ]
            },
        )

        rewrites = self._rewrite_for_audio(translations, config)
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
                ]
            },
        )

        audio_parts = self._tts(rewrites, config, store)
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
                ]
            },
        )

        processed = self._postprocess(audio_parts, config)
        merged_path = self._merge(processed, config, store)
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
            },
            store=store,
        )
        return manifest

    def _extract(self, config: BookvoiceConfig) -> str:
        """Extract raw text from the configured PDF input."""

        extractor = PdfTextExtractor()
        return extractor.extract(config.input_pdf)

    def _clean(self, raw_text: str) -> str:
        """Apply deterministic cleanup and normalization rules."""

        cleaner = TextCleaner()
        return cleaner.clean(raw_text).strip()

    def _split_chapters(self, text: str) -> list[Chapter]:
        """Split cleaned text into chapter units."""

        splitter = ChapterSplitter()
        return splitter.split(text)

    def _chunk(self, chapters: list[Chapter], config: BookvoiceConfig) -> list[Chunk]:
        """Convert chapters into chunk-sized text units."""

        chunker = Chunker()
        return chunker.to_chunks(chapters, target_size=config.chunk_size_chars)

    def _translate(
        self, chunks: list[Chunk], config: BookvoiceConfig
    ) -> list[TranslationResult]:
        """Translate chunks into target language text."""

        translator = OpenAITranslator()
        return [translator.translate(chunk, target_language=config.language) for chunk in chunks]

    def _rewrite_for_audio(
        self, translations: list[TranslationResult], config: BookvoiceConfig
    ) -> list[RewriteResult]:
        """Rewrite translated text for natural spoken delivery."""

        _ = config
        rewriter = AudioRewriter()
        return [rewriter.rewrite(translation) for translation in translations]

    def _tts(
        self, rewrites: list[RewriteResult], config: BookvoiceConfig, store: ArtifactStore
    ) -> list[AudioPart]:
        """Synthesize audio parts for rewritten text chunks."""

        voice = VoiceProfile(
            name="mvp-cs-voice",
            provider_voice_id="mvp-cs-voice",
            language=config.language,
            speaking_rate=1.0,
        )
        synthesizer = OpenAITTSSynthesizer(output_root=store.root / "audio/chunks")
        return [synthesizer.synthesize(item, voice) for item in rewrites]

    def _postprocess(
        self, audio_parts: list[AudioPart], config: BookvoiceConfig
    ) -> list[AudioPart]:
        """Apply postprocessing to synthesized audio parts."""

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

    def _merge(self, audio_parts: list[AudioPart], config: BookvoiceConfig, store: ArtifactStore) -> Path:
        """Merge chapter or book-level audio outputs."""

        _ = config
        merger = AudioMerger()
        return merger.merge(audio_parts, output_path=store.root / "audio/bookvoice_merged.wav")

    def _write_manifest(
        self,
        config: BookvoiceConfig,
        run_id: str,
        config_hash: str,
        merged_audio_path: Path,
        artifact_paths: dict[str, str],
        store: ArtifactStore,
    ) -> RunManifest:
        """Build a run manifest with deterministic identifiers."""

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
            total_llm_cost_usd=0.0,
            total_tts_cost_usd=0.0,
            extra=artifact_paths,
        )
        manifest_path = store.save_json(Path("run_manifest.json"), self._manifest_payload(manifest))
        return RunManifest(
            run_id=manifest.run_id,
            config_hash=manifest.config_hash,
            book=manifest.book,
            merged_audio_path=manifest.merged_audio_path,
            total_llm_cost_usd=manifest.total_llm_cost_usd,
            total_tts_cost_usd=manifest.total_tts_cost_usd,
            extra={**manifest.extra, "manifest_path": str(manifest_path)},
        )

    def _manifest_payload(self, manifest: RunManifest) -> dict[str, object]:
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
            "extra": json.loads(json.dumps(dict(manifest.extra))),
        }

    def _config_hash(self, config: BookvoiceConfig) -> str:
        payload = {
            "input_pdf": str(config.input_pdf),
            "output_dir": str(config.output_dir),
            "language": config.language,
            "provider_translator": config.provider_translator,
            "provider_tts": config.provider_tts,
            "chunk_size_chars": config.chunk_size_chars,
            "resume": config.resume,
            "extra": dict(config.extra),
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return sha256(canonical.encode("utf-8")).hexdigest()
