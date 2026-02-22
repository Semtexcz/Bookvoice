# Architecture

## Core Data Model

Bookvoice is centered around typed dataclasses shared across stages:

- `BookMeta`: source book identity.
- `Chapter`: chapter split output.
- `ChapterStructureUnit`: normalized chapter/subchapter planning unit.
- `Chunk`: bounded text segment used by translate/rewrite/TTS.
- `TranslationResult`: translation output per chunk.
- `RewriteResult`: rewrite output per translation.
- `AudioPart`: synthesized audio metadata per emitted WAV.
- `SegmentPlan` and `PlannedSegment`: structure-aware segmentation output.
- `RunManifest`: deterministic run record (config hash, outputs, costs, metadata).

These models live in `bookvoice/models/datatypes.py`.

## Pipeline Design

`BookvoicePipeline` is composed from focused mixins:

- `PipelineRuntimeMixin`: config validation, runtime provider resolution, run hashing.
- `PipelineExecutionMixin`: extract/clean/split/chunk/translate/rewrite/tts/merge execution.
- `PipelineChapterScopeMixin`: chapter-selection parsing and scope metadata.
- `PipelineManifestMixin`: `RunManifest` construction and persistence.
- `PipelineTelemetryMixin`: deterministic stage progress and structured stage events.

Primary flow in `BookvoicePipeline.run`:

1. `extract`
2. `clean`
3. `split`
4. `chunk`
5. `translate`
6. `rewrite`
7. `tts`
8. `merge`
9. `manifest`

`BookvoicePipeline.run_translate_only` executes the same deterministic text stages
through `translate`, then writes manifest metadata for continuation workflows.

`resume` reuses available artifacts and executes only missing stages.

## Runtime Configuration

Runtime provider settings are resolved with deterministic precedence:

`CLI explicit > secure credential storage > environment > config defaults`

Supported provider set is currently `openai` for translator, rewriter, and TTS.
Resolved non-secret runtime metadata is persisted in manifest `extra`.

## Artifact and Reproducibility Model

- Run ID and run directory are derived from a canonical config hash.
- Stage outputs are written to deterministic paths under `<out>/run-<hash-prefix>/`.
- Resume logic infers the next stage by checking expected artifact existence.
- Manifest includes cost summary, chapter scope metadata, and part-mapping metadata.

## Error Handling

- Stage failures are normalized into `PipelineStageError` with `stage`, `detail`, and optional `hint`.
- CLI prints concise stage-aware diagnostics.
- Provider errors are translated to user-facing hints (key/config/model/provider checks).

## Current Constraints

- `tts-only` command is still a placeholder.
- Audio postprocessing and metadata tagging are intentionally minimal.
- YAML/environment config loader helpers are present but still placeholder implementations.
