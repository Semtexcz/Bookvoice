# Module Overview

## Responsibilities and Public APIs

| Module | Responsibility | Public APIs |
|---|---|---|
| `bookvoice.__init__` | Package exports and versioning | `__version__`, `BookvoicePipeline` |
| `bookvoice.cli` | CLI entrypoint and subcommands | `app`, `main`, `build_command`, `translate_only_command`, `tts_only_command`, `resume_command` |
| `bookvoice.config` | Runtime configuration model/loading | `BookvoiceConfig`, `ConfigLoader.from_yaml`, `ConfigLoader.from_env` |
| `bookvoice.pipeline` | Stage orchestration | `BookvoicePipeline.run` |
| `bookvoice.io.pdf_text_extractor` | PDF text extraction interfaces | `PdfTextExtractor.extract`, `PdfTextExtractor.extract_pages` |
| `bookvoice.io.chapter_splitter` | Chapter boundary splitting | `ChapterSplitter.split` |
| `bookvoice.io.storage` | Artifact persistence abstraction | `ArtifactStore.save_text`, `save_json`, `save_audio`, `load_text`, `exists` |
| `bookvoice.text.cleaners` | Deterministic cleanup rules | `TextCleaner.clean`, `RemovePageNumbers.apply`, `RemoveHeadersFooters.apply`, `FixHyphenation.apply`, `NormalizeQuotes.apply`, `CollapseWhitespace.apply`, `RemoveFigureRefs.apply` |
| `bookvoice.text.normalizer` | Language/form normalization | `TextNormalizer.normalize` |
| `bookvoice.text.chunking` | Chunk generation from chapters | `Chunker.to_chunks` |
| `bookvoice.text.structure` | Chapter/subchapter structure normalization | `ChapterStructureNormalizer.from_chapters` |
| `bookvoice.llm.prompts` | Prompt template library | `PromptLibrary.translate_prompt`, `PromptLibrary.rewrite_for_audio_prompt` |
| `bookvoice.llm.translator` | Translation interface + provider stubs | `Translator.translate`, `OpenAITranslator.translate` |
| `bookvoice.llm.audio_rewriter` | Spoken-style rewrite stage | `AudioRewriter.rewrite` |
| `bookvoice.llm.rate_limiter` | Request throttling abstraction | `RateLimiter.acquire` |
| `bookvoice.llm.cache` | LLM response cache abstraction | `ResponseCache.get`, `ResponseCache.set` |
| `bookvoice.tts.voices` | Voice profile metadata | `VoiceProfile` |
| `bookvoice.tts.synthesizer` | TTS interface + provider stubs | `TTSSynthesizer.synthesize`, `OpenAITTSSynthesizer.synthesize` |
| `bookvoice.audio.postprocess` | Audio cleanup primitives | `AudioPostProcessor.normalize`, `AudioPostProcessor.trim_silence` |
| `bookvoice.audio.merger` | Multi-part merge orchestration | `AudioMerger.merge` |
| `bookvoice.audio.tags` | Metadata tagging abstraction | `MetadataWriter.write_id3` |
| `bookvoice.telemetry.cost_tracker` | Cost accounting | `CostTracker.add_llm_usage`, `add_tts_usage`, `summary` |
| `bookvoice.telemetry.logger` | Structured run logging | `RunLogger.log_event`, `log_error` |
| `bookvoice.models.datatypes` | Shared dataclasses | `BookMeta`, `Chapter`, `Chunk`, `TranslationResult`, `RewriteResult`, `AudioPart`, `ChapterStructureUnit`, `RunManifest` |

## Cross-Module Dependencies

- `bookvoice.pipeline` imports from: `bookvoice.config`, `bookvoice.models.datatypes`, `bookvoice.io`, `bookvoice.text`, `bookvoice.llm`, `bookvoice.tts`, `bookvoice.audio`, `bookvoice.telemetry`.
- `bookvoice.cli` imports from: `bookvoice.config`, `bookvoice.pipeline`.
- Provider modules should depend on shared models, not on each other.
- Shared dataclasses in `bookvoice.models.datatypes` are the dependency anchor to avoid cycles.

## Extension Points

- Add a new PDF extractor:
  - Implement `PdfTextExtractor` in a new module, wire into pipeline stage construction.
- Add a new translator:
  - Implement `Translator` protocol and plug provider config in `BookvoiceConfig`.
- Add a new TTS provider:
  - Implement `TTSSynthesizer` protocol and map to `VoiceProfile` selection.
