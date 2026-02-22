# Module Overview

## Package Responsibilities

| Module | Responsibility | Key public APIs |
|---|---|---|
| `bookvoice.__init__` | Package exports and versioning | `__version__`, `BookvoicePipeline` |
| `bookvoice.cli` | CLI entrypoint and command wiring | `app`, `main`, `build_command`, `chapters_only_command`, `list_chapters_command`, `translate_only_command`, `tts_only_command`, `resume_command`, `credentials_command` |
| `bookvoice.config` | Runtime config model and precedence resolution | `BookvoiceConfig`, `ProviderRuntimeConfig`, `RuntimeConfigSources`, `ConfigLoader` |
| `bookvoice.credentials` | Secure API-key persistence via keyring | `CredentialStore`, `KeyringCredentialStore`, `create_credential_store` |
| `bookvoice.provider_factory` | Provider to implementation mapping | `ProviderFactory.create_translator`, `create_rewriter`, `create_tts_synthesizer` |
| `bookvoice.pipeline.orchestrator` | Top-level run/chapters-only/translate-only/tts-only/resume orchestration | `BookvoicePipeline.run`, `run_chapters_only`, `run_translate_only`, `run_tts_only_from_manifest`, `resume`, `list_chapters_from_pdf`, `list_chapters_from_artifact` |
| `bookvoice.pipeline.artifacts` | Artifact payload serialization and loading | `chapter_artifact_payload`, `chunk_artifact_payload`, `audio_parts_artifact_payload`, `manifest_payload`, `load_*` helpers |
| `bookvoice.pipeline.resume` | Resume manifest validation and stage detection | `load_manifest_payload`, `detect_next_stage`, `resolve_artifact_path` |
| `bookvoice.io.*` | PDF extraction, chapter splitting, filesystem artifacts | `PdfTextExtractor`, `PdfOutlineChapterExtractor`, `ChapterSplitter`, `ArtifactStore` |
| `bookvoice.text.*` | Text cleaning, chapter selection, structure normalization, chunk planning | `TextCleaner`, `parse_chapter_selection`, `ChapterStructureNormalizer`, `TextBudgetSegmentPlanner`, `Chunker`, `slugify_audio_title` |
| `bookvoice.llm.*` | Prompting and OpenAI-backed translation/rewrite clients | `PromptLibrary`, `OpenAITranslator`, `AudioRewriter`, `DeterministicBypassRewriter`, `OpenAIChatClient` |
| `bookvoice.tts.*` | Voice profiles and OpenAI speech synthesis | `VoiceProfile`, `resolve_voice_profile`, `OpenAITTSSynthesizer` |
| `bookvoice.audio.*` | Postprocess/merge/tagging primitives | `AudioPostProcessor`, `AudioMerger`, `MetadataWriter` |
| `bookvoice.telemetry.*` | Structured stage logs and cost accounting | `RunLogger`, `CostTracker` |
| `bookvoice.models.datatypes` | Shared typed dataclasses | `BookMeta`, `Chapter`, `Chunk`, `TranslationResult`, `RewriteResult`, `AudioPart`, `ChapterStructureUnit`, `PlannedSegment`, `SegmentPlan`, `RunManifest` |

## Dependency Notes

- `bookvoice.pipeline.*` modules coordinate all stage packages and remain the orchestration center.
- Shared dataclasses in `bookvoice.models.datatypes` are the dependency anchor across modules.
- Provider implementations do not depend on each other; orchestration chooses implementations through `ProviderFactory`.
- `bookvoice.cli` focuses on argument normalization and error presentation, then delegates execution to `BookvoicePipeline`.

## Extension Points

- Add a translator/rewriter/TTS provider:
  - Implement the respective protocol and add factory wiring in `bookvoice/provider_factory.py`.
- Add extraction strategy improvements:
  - Extend `bookvoice/io/pdf_outline_extractor.py` and/or `bookvoice/io/chapter_splitter.py`.
- Add new planning strategy:
  - Implement additional planner logic in `bookvoice/text/*` and integrate into `PipelineExecutionMixin._chunk`.
