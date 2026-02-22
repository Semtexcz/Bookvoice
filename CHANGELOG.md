# Changelog

All notable changes to this project will be documented in this file.

## [0.6.0] - 2026-02-22

### Added

- Completed `TASK-040` by adding explicit CLI config-file support (`--config <path.yaml>`) for `build` and `translate-only`.
- Added integration coverage for config-file happy paths and runtime precedence interactions when config defaults, environment values, secure credentials, and CLI overrides are combined.
- Added integration coverage for stage-aware diagnostics on missing or invalid CLI config files.

### Changed

- Wired command-level config resolution so `input_pdf`, `output_dir`, and `chapter_selection` can be sourced from YAML and overridden by explicit CLI arguments/options.
- Preserved deterministic runtime precedence with config defaults as fallback:
  `CLI explicit > secure > env > config/defaults`.
- Updated `README.md` with `--config` command examples and precedence documentation.
- Marked `TASK-040` as done and moved it from `project/backlog/` to `project/done/`.
- Bumped project version to `0.6.0`.

## [0.5.2] - 2026-02-22

### Changed

- Updated packaging backlog scope to reflect confirmed product decisions for audiobook deliverables:
  - chapter-split final outputs (one chapter = one file),
  - primary packaged target `m4a` (AAC) with secondary `mp3`,
  - optional full merged deliverable preserved,
  - user-selectable chapter numbering mode (`source` or `sequential`).
- Refined task definitions:
  - `TASK-039` now explicitly requires chapter-split packaging behavior and numbering-mode support.
  - `TASK-041` now targets deterministic chapter-level export policy and naming strategy options.
  - `TASK-042` now requires numbering-mode-aware track/tag metadata behavior.
  - `TASK-043` now requires CLI/config controls for layout, numbering mode, and naming mode.
- Bumped project version to `0.5.2`.

## [0.5.1] - 2026-02-22

### Changed

- Refined `TASK-039` scope to explicitly target AAC/MP3 delivery packaging from deterministic merged WAV master output.
- Added new backlog tasks for phased implementation of packaged audiobook delivery:
  - `TASK-041`: deterministic AAC/MP3 export stage.
  - `TASK-042`: format-aware metadata tagging for MP3/M4A.
  - `TASK-043`: CLI/config output-format controls and manifest packaging metadata.
- Updated `docs/ROADMAP.md` Phase 3 scope and milestones to include explicit WAV-master plus AAC/MP3 packaging strategy.
- Updated roadmap backlog mapping section for `TASK-039`, `TASK-041`, `TASK-042`, and `TASK-043`.
- Bumped project version to `0.5.1`.

## [0.5.0] - 2026-02-22

### Added

- Completed `TASK-038` by implementing deterministic merged-WAV postprocessing with explicit defaults: leading/trailing silence trimming and peak normalization to `95%`.
- Added deterministic WAV metadata tagging via RIFF `LIST/INFO` fields: `INAM` (title), `ISBJ` (chapter/part context), and `ICMT` (source identifier).
- Added unit coverage for postprocessing idempotence/normalization behavior and tag presence/idempotence.
- Added integration coverage asserting merged build outputs contain deterministic WAV metadata tags.

### Changed

- Wired merge stage to apply merged-output postprocessing and metadata tagging consistently across `build`, `resume`, and `tts-only` replay paths.
- Updated `README.md` and `docs/ARTIFACTS.md` to document postprocessing/tagging behavior and current WAV-only limitation.
- Updated `tts-only` missing-rewrites integration expectation to reflect current `resume-validation` behavior for mixed missing/stale artifact chains.
- Marked `TASK-038` as done and moved it from `project/backlog/` to `project/done/`.
- Bumped project version to `0.5.0`.

## [0.4.3] - 2026-02-22

### Changed

- Completed `TASK-037` by adding resume preflight consistency validation for critical artifact chains (`chapters`, `chunks`, `translations`, `rewrites`, `audio_parts`) before stage replay starts.
- Classified resume states into recoverable and non-recoverable modes using deterministic rules for mixed missing/stale artifacts and cross-artifact payload alignment.
- Added actionable `resume-validation` diagnostics that include concrete artifact paths and explicit manual-cleanup remediation guidance.
- Persisted lightweight resume validation metadata in manifest `extra` (`resume_validation_*`) for post-run debugging.
- Added integration coverage for non-recoverable mixed artifact topology and cross-artifact payload mismatch failures, and assertions for recoverable validation metadata.
- Marked `TASK-037` as done and moved it from `project/backlog/` to `project/done/`.
- Bumped project version to `0.4.3`.

## [0.4.2] - 2026-02-22

### Changed

- Added `TASK-040` to `project/backlog/` to track CLI integration of config-file loading (`--config`) with explicit precedence guarantees and tests/docs scope.
- Bumped project version to `0.4.2`.

## [0.4.1] - 2026-02-22

### Changed

- Added sanitized `.env.example` generated from root `.env` with `OPENAI_API_KEY` value removed.
- Added local YAML runtime config file `bookvoice.local.yaml` containing API-key-based runtime settings.
- Updated `.gitignore` to ignore `bookvoice.local.yaml` so local secrets stay untracked.
- Bumped project version to `0.4.1`.

## [0.4.0] - 2026-02-22

### Added

- Completed `TASK-036` by implementing real `ConfigLoader.from_yaml` and `ConfigLoader.from_env` parsing and validation in `bookvoice/config.py`.
- Added strict YAML schema validation for required keys, unknown-key rejection, typed boolean/integer parsing, and normalized optional string/mapping fields.
- Added focused unit coverage for valid/invalid YAML payloads, environment loading behavior, typed value errors, blank normalization, and runtime precedence compatibility.

### Changed

- Updated `README.md` with explicit supported keys for `ConfigLoader.from_yaml` and `ConfigLoader.from_env`, including typed token expectations for boolean and integer values.
- Marked `TASK-036` as done and moved it from `project/backlog/` to `project/done/`.
- Bumped project version to `0.4.0`.

## [0.3.0] - 2026-02-22

### Added

- Completed `TASK-035` by implementing a real `bookvoice tts-only <manifest.json>` flow that replays from persisted artifacts and executes only `tts`, `merge`, and `manifest` stages.
- Added strict `tts-only` prerequisite validation for manifest runtime metadata (`provider_tts`, `model_tts`, `tts_voice`), required `text/rewrites.json`, and required chunk metadata in `text/chunks.json`.
- Added integration coverage for `tts-only` successful replay, upstream-stage non-execution guarantees, and missing/corrupted prerequisite artifact failures.

### Changed

- Replaced the CLI `tts-only` placeholder with full pipeline wiring including stage progress, phase logging, chapter summary, and deterministic cost output rendering.
- Updated docs (`README.md`, `docs/ARCHITECTURE.md`, `docs/MODULES.md`, `docs/ROADMAP.md`) to document real `tts-only` behavior and remove placeholder status.
- Marked `TASK-035` as done and moved it from `project/backlog/` to `project/done/`.
- Bumped project version to `0.3.0`.

## [0.2.0] - 2026-02-22

### Added

- Completed `TASK-034` by implementing a real `bookvoice translate-only` command path that executes stages through `translate` and writes deterministic `text/raw.txt`, `text/clean.txt`, `text/chapters.json`, `text/chunks.json`, and `text/translations.json` artifacts.
- Added pipeline orchestration entrypoint `BookvoicePipeline.run_translate_only` to keep translate-stage execution explicit and reusable from CLI wiring.
- Added integration coverage for `translate-only` artifact behavior and command diagnostics, including explicit assertions that `rewrite`, `tts`, and `merge` outputs are not produced.
- Added runtime precedence coverage proving `translate-only` resolves provider/model/API key values with the same `CLI > secure > env > defaults` behavior as `build`.

### Changed

- Updated `bookvoice translate-only` CLI wiring to use runtime source resolution, chapter selection support, stage progress/phase logs, and concise manifest/cost output consistent with existing command rendering.
- Updated docs (`README.md`, `docs/ARCHITECTURE.md`, `docs/MODULES.md`, `docs/ROADMAP.md`) to remove placeholder wording for `translate-only` and document real command behavior.
- Marked `TASK-034` as done and moved it from `project/backlog/` to `project/done/`.
- Bumped project version to `0.2.0`.

## [0.1.56] - 2026-02-22

### Changed

- Reviewed current implementation against `docs/ROADMAP.md` and current backlog/done task inventory.
- Added `TASK-034` for real `translate-only` command execution through the translation stage with deterministic artifacts and integration tests.
- Added `TASK-035` for real `tts-only` command execution from manifest artifacts with constrained stage replay and validation.
- Added `TASK-036` for completing `ConfigLoader.from_yaml` and `ConfigLoader.from_env`.
- Added `TASK-037` for resume artifact consistency hardening and recoverable/non-recoverable resume-state handling.
- Added `TASK-038` for roadmap Phase 3 audio postprocessing and deterministic metadata tagging improvements.
- Added `TASK-039` for optional output packaging formats beyond merged WAV.
- Bumped project version to `0.1.56`.

## [0.1.55] - 2026-02-22

### Changed

- Completed `TASK-033` by replacing `urllib` transport calls in `bookvoice/llm/openai_client.py` with `requests.post` while preserving existing `OpenAIChatClient` and `OpenAISpeechClient` public APIs.
- Preserved OpenAI endpoint behavior for `/chat/completions` and `/audio/speech` requests, including shared response-byte handling and empty speech payload validation.
- Kept stage-facing `OpenAIProviderError` semantics and actionable diagnostics for invalid key, quota, model, timeout, and transport failure mapping.
- Updated OpenAI integration unit tests to use `requests`-style mocked responses/exceptions and added explicit coverage for mapped HTTP failures, timeout/connection transport failures, and malformed or empty payload handling.
- Added `requests` as an explicit project dependency and synchronized `poetry.lock`.
- Marked `TASK-033` as done and moved it from `project/backlog/` to `project/done/`.
- Bumped project version to `0.1.55`.

## [0.1.54] - 2026-02-22

### Changed

- Completed `TASK-032` by consolidating duplicated OpenAI JSON POST request construction and transport/exception mapping logic into shared `_OpenAIBaseClient` helpers.
- Kept chat-completions text parsing and speech-byte validation stage-specific while reusing shared HTTP plumbing for both `OpenAIChatClient` and `OpenAISpeechClient`.
- Preserved existing `OpenAIProviderError` diagnostic message patterns used by pipeline stage error mapping.
- Added unit coverage for shared transport handling: malformed HTTP error body decoding fallback, URL transport failures, timeout classification, and empty OpenAI speech responses.
- Marked `TASK-032` as done and moved it from `project/backlog/` to `project/done/`.
- Bumped project version to `0.1.54`.

## [0.1.53] - 2026-02-22

### Changed

- Completed `TASK-031` by refactoring `BookvoicePipeline.resume` into typed state-driven, stage-specific `load-or-*` helper methods in `bookvoice/pipeline/orchestrator.py`.
- Added explicit resume context dataclasses for resolved artifact paths and loaded stage state while preserving artifact locations and manifest metadata keys.
- Kept resume behavior parity for chapter metadata recovery, chapter-scope reconstruction, deterministic cost tracking, and merged output reuse decisions.
- Added targeted integration coverage for three resume branches: full reuse with no TTS/merge replay, partial replay from `translate`, and replay when audio chunk files are missing.
- Marked `TASK-031` as done and moved it from `project/backlog/` to `project/done/`.
- Bumped project version to `0.1.53`.

## [0.1.52] - 2026-02-22

### Changed

- Completed `TASK-030` by extracting CLI output and error rendering helpers into new module `bookvoice/cli_rendering.py`.
- Updated `bookvoice/cli.py` to delegate chapter summaries, chapter list/source rendering, cost summaries, and command failure diagnostics through shared rendering helpers.
- Kept CLI output text and ordering stable for existing command integration coverage.
- Added unit tests for centralized error rendering behavior for both `PipelineStageError` (with hint) and generic exception fallback paths.
- Marked `TASK-030` as done and moved it from `project/backlog/` to `project/done/`.
- Bumped project version to `0.1.52`.

## [0.1.51] - 2026-02-22

### Changed

- Completed `TASK-029` by extracting provider runtime-source assembly and interactive prompt flow from `bookvoice/cli.py` into new support module `bookvoice/cli_runtime.py`.
- Kept `bookvoice build` CLI options and secure credential behavior unchanged for `--store-api-key`, `--prompt-api-key`, and `--interactive-provider-setup`.
- Added focused unit coverage for extracted runtime-resolution helpers, including interactive prompts, secure fallback behavior, and secure-store failure mapping.
- Updated `bookvoice/cli.py` to delegate provider runtime resolution to the extracted helper while preserving command signatures and UX output.
- Marked `TASK-029` as done and moved it from `project/backlog/` to `project/done/`.
- Bumped project version to `0.1.51`.

## [0.1.50] - 2026-02-22

### Changed

- Completed `TASK-028` by introducing shared parsing helpers in `bookvoice/parsing.py` for normalized optional strings and permissive/strict boolean token parsing.
- Refactored `bookvoice/config.py` and `bookvoice/pipeline/resume.py` to consume the shared parsing helpers while preserving accepted boolean tokens, defaults, and runtime validation error text.
- Added focused unit coverage for parsing edge cases, including blank values, mixed-case boolean tokens, and invalid-token fallback/validation behavior.
- Marked `TASK-028` as done and moved it from `project/backlog/` to `project/done/`.
- Bumped project version to `0.1.50`.

## [0.1.49] - 2026-02-22

### Changed

- Completed `TASK-027` by extracting shared translation and rewrite artifact payload builders into `bookvoice/pipeline/artifacts.py`.
- Replaced duplicated inline payload construction in both `run` and `resume` orchestration flows with the shared artifact helpers.
- Preserved persisted payload schema and field names for `text/translations.json` and `text/rewrites.json`.
- Added coverage for artifact payload shape consistency with a new unit test and a resume integration assertion comparing build vs resume schemas.
- Marked `TASK-027` as done and moved it from `project/backlog/` to `project/done/`.
- Bumped project version to `0.1.49`.

## [0.1.48] - 2026-02-22

- Completed `TASK-014F` by adding a dedicated provider integration test matrix for mocked translate/rewrite/TTS happy and failure paths with stage-specific assertions.
- Added CLI integration coverage for runtime provider/model/API-key environment fallback when CLI and secure-storage values are not provided.
- Documented provider mock strategy and fixture patterns for deterministic offline execution in `tests/README.md`.
- Bumped project version to `0.1.48`.

## [0.1.47] - 2026-02-22

- Added an agent rule in `AGENTS.md` requiring completed tasks from `project/backlog` to be marked `done` and moved to `project/done`.
- Bumped project version to `0.1.47`.

## [0.1.46] - 2026-02-22

- Added a new agent rule in `AGENTS.md` requiring `CHANGELOG.md` updates after every code change.
- Bumped project version to `0.1.46`.

## [0.1.42] - 2026-02-21

- Further split `bookvoice/pipeline/orchestrator.py` into focused mixin modules.
- Added `bookvoice/pipeline/execution.py` for stage execution helpers (`extract`..`merge`).
- Added `bookvoice/pipeline/chapter_scope.py` for chapter scope/selection resolution.
- Added `bookvoice/pipeline/runtime.py` for config validation/runtime resolution and run identity hashing.
- Added `bookvoice/pipeline/telemetry.py` for stage progress and telemetry hooks.
- Added `bookvoice/pipeline/manifesting.py` for manifest persistence logic.
- Reduced `bookvoice/pipeline/orchestrator.py` to orchestration flow methods (`run`, `run_chapters_only`, `resume`, listing).

## [0.1.41] - 2026-02-21

- Reorganized pipeline internals into a dedicated `bookvoice/pipeline/` package.
- Moved orchestration into `bookvoice/pipeline/orchestrator.py`.
- Moved artifact helpers into `bookvoice/pipeline/artifacts.py`.
- Moved resume helpers into `bookvoice/pipeline/resume.py`.
- Moved deterministic cost helpers into `bookvoice/pipeline/costs.py`.
- Added compatibility exports in `bookvoice/pipeline/__init__.py` for `BookvoicePipeline`, `ChapterSplitter`, and `PdfOutlineChapterExtractor`.

## [0.1.40] - 2026-02-21

- Refactored `bookvoice/pipeline.py` to improve readability by separating artifact serialization/loading, resume-path resolution, and cost estimation helpers into dedicated modules.
- Added `bookvoice/pipeline_artifacts.py` for deterministic artifact payload builders and typed artifact loaders.
- Added `bookvoice/pipeline_resume.py` for manifest parsing, resume artifact path resolution, and missing-stage detection.
- Added `bookvoice/pipeline_costs.py` for deterministic translation/rewrite/TTS cost accumulation and rounded summary generation.

## [0.1.39] - 2026-02-21

- Fixed sentence-boundary handling in `TextBudgetSegmentPlanner` long-paragraph splitting to avoid mid-sentence chunk cuts.
- Added period/abbreviation/decimal-aware boundary detection and bounded forward sentence extension in planner fallback path.
- Added unit coverage for sentence-complete long-paragraph segmentation in planner-generated chunks.

## [0.1.38] - 2026-02-21

- Completed `TASK-023` by enforcing sentence-complete boundaries in fallback chapter chunking.
- Implemented sentence boundary preference ordering (`.` first, then `!`/`?`) with decimal and common-abbreviation guards.
- Added bounded forward extension when no valid sentence boundary exists near target chunk size.
- Added deterministic pathological-text fallback with explicit chunk metadata marker `boundary_strategy = "forced_split_no_sentence_boundary"`.
- Propagated new chunk boundary metadata through artifact serialization/resume loading paths.
- Added unit coverage for period-priority boundaries, bounded extension, abbreviation and decimal handling, and no-punctuation fallback behavior.
- Updated `README.md` with chunk-boundary guarantees and current limitation scope.
- Marked `TASK-023` as done and moved it to `project/done/`.

## [0.1.37] - 2026-02-21

- Completed `TASK-022` by standardizing part filenames to deterministic `<chapter>_<part>_<title-slug>.wav`.
- Unified slug generation through shared locale-independent ASCII normalization used by both segment planning and TTS synthesis.
- Updated fallback chunk metadata to emit title-based part IDs instead of generic `_part` suffixes.
- Extended `audio/parts.json` and manifest `extra` metadata with explicit emitted filename fields for produced audio files.
- Added unit and integration tests for deterministic non-ASCII slug handling, filename pattern coverage, and resume stability of emitted filenames.
- Updated `README.md` naming examples and moved `TASK-022` from `project/backlog/` to `project/done/`.

## [0.1.35] - 2026-02-21

- Completed `TASK-026` by integrating structure-based segmented part planning into the pipeline `chunk` stage before TTS generation.
- Persisted segmented-part metadata across artifacts (`text/chunks.json`, `audio/parts.json`) including deterministic `part_index`, `part_id`, and `source_order_indices`.
- Added compact manifest metadata for chapter/part mapping and referenced structure-unit indices to keep rebuild/resume identity stable.
- Updated TTS per-part artifact naming to the deterministic `chapter_part_title-slug` format (`001_01_chapter-title.wav`) for compatibility with `TASK-022` requirements.
- Added integration coverage for segmented build artifacts and resume stability of part identifiers/mapping.
- Updated `README.md` and `docs/ARTIFACTS.md` with segmented artifact behavior and naming expectations.
- Marked `TASK-026` as done and moved it to `project/done/`.

## [0.1.34] - 2026-02-21

- Completed `TASK-025` by implementing a deterministic `TextBudgetSegmentPlanner` for chapter/subchapter-aware segment planning.
- Added a default segment budget of `6500` characters with a fixed upper ceiling of `9300` characters (10-minute target cap).
- Implemented paragraph-preferred segment boundaries with deterministic fallback splitting for oversized single paragraphs.
- Enforced strict chapter boundaries while allowing same-chapter short subchapter merges when combined text fits budget.
- Introduced immutable planning datatypes (`PlannedSegment`, `SegmentPlan`) and a planner-to-`Chunk` adapter for downstream pipeline/TTS compatibility.
- Added unit coverage for budget split behavior, merge behavior, deterministic repeated-run stability, and budget ceiling clamping.

## [0.1.33] - 2026-02-21

- Completed `TASK-019` by adding visible `bookvoice build` runtime progress lines across all core pipeline phases.
- Integrated phase-level structured logging through a new `RunLogger` implementation backed by `loguru` (with deterministic fallback output).
- Wired pipeline stage transition hooks (`start`/`complete`/`failure`) for `extract`, `clean`, `split`, `chunk`, `translate`, `rewrite`, `tts`, `merge`, and `manifest`.
- Added integration coverage asserting build progress indicator activation and phase log emission in CLI output.
- Updated `README.md` with runtime feedback behavior and sample output.

## [0.1.32] - 2026-02-21

- Completed `TASK-024` by adding a normalized `ChapterStructureUnit` model for chapter/subchapter-aware planning.
- Extended PDF outline extraction to include hierarchy-aware structure units with deterministic ordering and explicit chapter boundaries.
- Added deterministic text-heading fallback structure normalization when outline hierarchy is unavailable or incomplete.
- Persisted normalized structure metadata in `text/chapters.json` for build, chapters-only, and resume-rebuild chapter artifact paths.
- Added tests for outline-first structure extraction, fallback behavior, ordering stability, and chapters-only artifact metadata presence.

## [0.1.25] - 2026-02-21

- Added `TASK-019` to backlog for visible `bookvoice build` runtime feedback.
- Captured requirements for a progress indicator (spinner/progress bar), pipeline phase-level logs, and `loguru` integration.
- Included acceptance criteria for deterministic logging behavior, secret-safe output, tests, and README updates.

## [0.1.24] - 2026-02-21

- Revised `README.md` to reflect currently implemented OpenAI translation/rewrite/TTS behavior instead of planned-only wording.
- Added a practical usage guide with `poetry`-based setup, quickstart, command recipes, runtime precedence, environment keys, and artifact expectations.
- Expanded troubleshooting guidance with stage-specific diagnostics aligned to current CLI output.

## [0.1.23] - 2026-02-21

- Completed `TASK-014D` by replacing deterministic local TTS stub output with real OpenAI `/audio/speech` synthesis per rewrite chunk.
- Preserved deterministic chunk artifact paths while persisting per-chunk TTS metadata (`provider`, `model`, `voice`) in `audio/parts.json`.
- Added explicit stage-level provider failure mapping for `tts` with actionable API-key/model/voice hints.
- Added mocked unit coverage for OpenAI TTS happy path, provider-failure path, and pipeline `tts` stage error mapping.

## [0.1.22] - 2026-02-21

- Completed `TASK-014C` by implementing real OpenAI chat-completions integration for translation and rewrite stages.
- Added explicit rewrite bypass mode (`--rewrite-bypass`) with deterministic pass-through behavior and persisted rewrite bypass metadata.
- Added stage-specific provider failure mapping for translation and rewrite with actionable CLI hints.
- Added unit coverage for OpenAI translation/rewrite happy paths and provider-failure paths, plus stage-level error mapping assertions.
- Added integration-test fixture to mock OpenAI LLM calls for deterministic offline test runs.

## [0.1.21] - 2026-02-21

- Completed `TASK-014B` by adding `build` CLI provider/model runtime options and an interactive provider setup flow with hidden API-key prompt input.
- Added secure credential management via OS keyring integration (`bookvoice credentials`, `--set-api-key`, `--clear-api-key`) and runtime loading from secure storage.
- Wired deterministic runtime source precedence end-to-end in CLI and pipeline (`CLI explicit input > secure credential storage > environment > defaults`).
- Added integration coverage for interactive prompt path, non-interactive option precedence path, and credential command set/clear/status behavior.
- Added unit coverage for keyring-backed secure credential store operations.
- Moved `TASK-014B` from `project/backlog/` to `project/done/` and marked acceptance criteria complete.

## [0.1.20] - 2026-02-21

- Marked `TASK-014A` as completed and moved its task card from `project/backlog/` to `project/done/`.
- Updated `TASK-014` epic subtask checklist to reflect `TASK-014A` completion.

## [0.1.19] - 2026-02-21

- Reorganized test suite into explicit `tests/unit/` and `tests/integration/` directories.
- Updated pytest discovery paths to run both unit and integration suites by default.
- Updated test documentation to reflect the new test layout and smoke-test path.

## [0.1.18] - 2026-02-21

- Completed `TASK-014A` by introducing provider factory abstractions for translation, rewrite, and TTS client construction.
- Expanded runtime config with provider/model fields (`provider_translator`, `provider_rewriter`, `provider_tts`, `model_translate`, `model_rewrite`, `model_tts`, `tts_voice`) and deterministic precedence resolution (`CLI > secure storage > environment > defaults`).
- Added configuration validation for supported provider IDs and required model/voice values.
- Wired pipeline stages to resolve provider runtime settings through the new factory layer while keeping `openai` as the only implemented provider.
- Persisted resolved provider/model/voice identifiers into stage artifacts metadata and run manifest metadata.
- Added tests for provider factory resolution, unsupported-provider validation, precedence behavior, and manifest metadata assertions.

## [0.1.17] - 2026-02-21

- Split `TASK-014` into an explicit epic with six concrete backlog subtasks: `TASK-014A` through `TASK-014F`.
- Added dedicated task cards for provider abstraction/config foundation, CLI credential+model UX with secure storage, OpenAI LLM integration, OpenAI TTS integration, provider error diagnostics, and provider test matrix.
- Updated `TASK-014` to track subtask completion and keep epic-level acceptance criteria.

## [0.1.16] - 2026-02-21

- Updated `TASK-014` definition of done to require secure persistent storage of CLI-entered API keys for future runs (for example OS keychain-backed storage).

## [0.1.15] - 2026-02-21

- Revised `TASK-014` to require OpenAI-first real provider integration with provider-ready abstractions for future providers.
- Added `TASK-014` requirements for CLI-based API key/model input (including interactive prompts) with deterministic config precedence over env inputs.
- Added recommended initial OpenAI model defaults in `TASK-014` (`gpt-4.1-mini` for translation/rewrite, `gpt-4o-mini-tts` with `alloy` voice for TTS).
- Updated `TASK-012` to align cache/retry/rate-limit hardening with real provider boundaries and provider/model-aware cache keys.
- Updated `TASK-015` to require provider+model-aware pricing resolution and compatibility with CLI-selected models from `TASK-014`.

## [0.1.14] - 2026-02-21

- Fixed `test_parse_chapter_selection_rejects_out_of_bounds_indices` to assert invalid 1-based index diagnostics for `0` and out-of-bounds diagnostics for `6`.

## [0.1.13] - 2026-02-21

- Completed `TASK-018` by adding `--chapters` chapter-scope selection support to `bookvoice build` and `bookvoice chapters-only`.
- Added canonical chapter selection parsing and validation for single/list/range/mixed syntax with actionable overlap and bounds errors.
- Updated pipeline orchestration and resume flow to process only selected chapters downstream and persist deterministic chapter scope metadata across artifacts and manifest.
- Added coverage for parser validation, selected-scope build behavior, invalid CLI selection failures, and resume regeneration with preserved selected scope.
- Updated README chapter-selection syntax, examples, and testing-focused partial-run usage guidance.

## [0.1.12] - 2026-02-21

- Completed `TASK-017` by adding a dedicated `bookvoice list-chapters` CLI command.
- Added chapter listing support for both direct PDF extract/clean/split flow and existing `text/chapters.json` artifacts.
- Added deterministic CLI output with chapter index/title rows plus chapter source and optional fallback reason metadata.
- Added integration test coverage for successful artifact-based listing and stage-aware failure diagnostics for missing artifacts.

## [0.1.11] - 2026-02-21

- Added `TASK-017` to backlog for a CLI command that lists extracted book chapters with source metadata.
- Added `TASK-018` to backlog for CLI chapter selection (single/list/range) to support partial processing for faster testing.

## [0.1.10] - 2026-02-21

- Completed `TASK-016` by adding a dedicated `bookvoice chapters-only` CLI command for extract/clean/chapter-split only.
- Added deterministic chapter-only artifact coverage and verified downstream stage artifacts are not created.
- Updated README and artifacts documentation with chapter-only usage and `text/chapters.json` metadata shape.

## [0.1.9] - 2026-02-21

- Added `TASK-016` to backlog for a CLI chapter-only mode that splits PDF into chapters without running downstream stages.

## [0.1.8] - 2026-02-21

- Added `pytest-cov` to development test dependencies.
- Enabled optional coverage runs through `pytest-cov` (for example `pytest --cov=bookvoice --cov-report=term-missing`).

## [0.1.7] - 2026-02-21

- Added integration coverage for real PDF outline chapter splitting using a generated outline-enabled PDF fixture.
- Verified that pipeline chapter splitting prefers `pdf_outline` source even when cleaned text lacks chapter heading markers.

## [0.1.6] - 2026-02-21

- Completed `TASK-013` by adding first-level PDF outline chapter extraction with deterministic text-split fallback.
- Updated pipeline chapter splitting to prefer PDF outline boundaries and persist source/fallback metadata in chapter artifacts and run manifest.
- Added test coverage for both chapter extraction paths (outline-present and fallback-to-text), and surfaced chapter source details in CLI output.

## [0.1.5] - 2026-02-21

- Added `TASK-015` to backlog for online model-based pricing integration in cost tracking and manifest reporting.

## [0.1.4] - 2026-02-21

- Completed `TASK-011` by integrating deterministic LLM/TTS cost tracking into build and resume pipeline paths.
- Added `total_cost_usd` into run manifest payload and CLI run summaries (`build`, `resume`).
- Added integration test coverage for cost fields and deterministic CLI cost summary output.

## [0.1.3] - 2026-02-21

- Completed `TASK-010` by adding smoke coverage for `bookvoice build` on the canonical PDF fixture.
- Added smoke assertion for stage-aware failure output to keep pipeline diagnostics explicit.
- Moved `TASK-010` from `project/backlog/` to `project/done/`.

## [0.1.2] - 2026-02-21

- Added `TASK-014` to backlog for real LLM and TTS provider API integration.
- Clarified in `TASK-005` and `TASK-006` that completed MVP paths are deterministic stubs.

## [0.1.1] - 2026-02-21

- Added stage-scoped pipeline exceptions for core build and resume failures.
- Unified CLI failure diagnostics with concise actionable hints and stable exit code `1`.
- Added CLI error-handling tests and README troubleshooting guidance.

## [0.1.0] - 2026-02-20

- Initial open-source scaffold.
- Added package structure, typed stubs, and project documentation.
