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

        run_root = self._resolve_run_root(manifest_path, extra)
        store = ArtifactStore(run_root)
        config = BookvoiceConfig(
            input_pdf=source_pdf,
            output_dir=run_root.parent,
            language=language,
            resume=True,
        )

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
        else:
            chapters = self._split_chapters(clean_text)
            chapters_path = store.save_json(
                Path("text/chapters.json"),
                {"chapters": [asdict(chapter) for chapter in chapters]},
            )

        if chunks_path.exists():
            chunks = self._load_chunks(chunks_path)
        else:
            chunks = self._chunk(chapters, config)
            chunks_path = store.save_json(
                Path("text/chunks.json"),
                {"chunks": [asdict(chunk) for chunk in chunks]},
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
                    ]
                },
            )

        if rewrites_path.exists():
            rewrites = self._load_rewrites(rewrites_path)
        else:
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

        reuse_audio_parts = False
        if audio_parts_path.exists():
            loaded_parts = self._load_audio_parts(audio_parts_path)
            if all(part.path.exists() for part in loaded_parts):
                audio_parts = loaded_parts
                reuse_audio_parts = True
            else:
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
        else:
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

        if merged_path.exists() and reuse_audio_parts:
            final_merged_path = merged_path
        else:
            processed = self._postprocess(audio_parts, config)
            final_merged_path = self._merge(processed, config, store)

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
            },
            store=store,
        )

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

    def _load_manifest_payload(self, manifest_path: Path) -> dict[str, object]:
        if not manifest_path.exists():
            raise ValueError(
                f"Manifest file not found: {manifest_path}. Run `bookvoice build` first."
            )
        try:
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Manifest is not valid JSON: {manifest_path}") from exc
        if not isinstance(payload, dict):
            raise ValueError(f"Manifest root must be a JSON object: {manifest_path}")
        return payload

    def _require_manifest_field(
        self, payload: dict[str, object], key: str, scope: str = "manifest"
    ) -> str:
        value = payload.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                f"Manifest is missing required `{scope}.{key}` field; cannot resume run."
            )
        return value

    def _resolve_run_root(self, manifest_path: Path, extra: dict[str, object]) -> Path:
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
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Artifact JSON is invalid: {path}") from exc
        if not isinstance(payload, dict):
            raise ValueError(f"Artifact JSON must be an object: {path}")
        return payload

    def _load_chapters(self, path: Path) -> list[Chapter]:
        payload = self._load_json_object(path)
        items = payload.get("chapters")
        if not isinstance(items, list):
            raise ValueError(f"Artifact missing `chapters` list: {path}")
        chapters: list[Chapter] = []
        for item in items:
            if not isinstance(item, dict):
                raise ValueError(f"Malformed chapter item in {path}")
            chapters.append(
                Chapter(
                    index=int(item["index"]),
                    title=str(item["title"]),
                    text=str(item["text"]),
                )
            )
        return chapters

    def _load_chunks(self, path: Path) -> list[Chunk]:
        payload = self._load_json_object(path)
        items = payload.get("chunks")
        if not isinstance(items, list):
            raise ValueError(f"Artifact missing `chunks` list: {path}")
        chunks: list[Chunk] = []
        for item in items:
            if not isinstance(item, dict):
                raise ValueError(f"Malformed chunk item in {path}")
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
        payload = self._load_json_object(path)
        items = payload.get("translations")
        if not isinstance(items, list):
            raise ValueError(f"Artifact missing `translations` list: {path}")
        translations: list[TranslationResult] = []
        for item in items:
            if not isinstance(item, dict):
                raise ValueError(f"Malformed translation item in {path}")
            chunk_payload = item.get("chunk")
            if not isinstance(chunk_payload, dict):
                raise ValueError(f"Translation item missing `chunk` object in {path}")
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
        payload = self._load_json_object(path)
        items = payload.get("rewrites")
        if not isinstance(items, list):
            raise ValueError(f"Artifact missing `rewrites` list: {path}")
        rewrites: list[RewriteResult] = []
        for item in items:
            if not isinstance(item, dict):
                raise ValueError(f"Malformed rewrite item in {path}")
            translation_payload = item.get("translation")
            if not isinstance(translation_payload, dict):
                raise ValueError(f"Rewrite item missing `translation` object in {path}")
            chunk_payload = translation_payload.get("chunk")
            if not isinstance(chunk_payload, dict):
                raise ValueError(f"Rewrite translation missing `chunk` object in {path}")
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
        payload = self._load_json_object(path)
        items = payload.get("audio_parts")
        if not isinstance(items, list):
            raise ValueError(f"Artifact missing `audio_parts` list: {path}")
        audio_parts: list[AudioPart] = []
        for item in items:
            if not isinstance(item, dict):
                raise ValueError(f"Malformed audio part item in {path}")
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
