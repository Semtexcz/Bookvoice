# Roadmap

Reference date: 2026-02-22.

## Product Goal

Primary outcome remains:

`PDF (text) -> translated + rewrite-adapted text -> synthesized audiobook artifacts`

## Current Delivery Status

Implemented:

- End-to-end `build` pipeline with deterministic stage order.
- Artifact persistence (`text/*`, `audio/*`, `run_manifest.json`).
- Resume support from existing manifest/artifacts.
- OpenAI-backed translation, rewrite, and TTS provider flow.
- Rewrite bypass mode for deterministic pass-through.
- Chapter listing and chapter-scope selection.
- Deterministic segment planner with budget ceiling.
- Structured stage logging and run-level cost summary.

Still limited:

- Final delivery packaging is still WAV-first; AAC/MP3 outputs are not yet implemented.
- Format-aware metadata tagging for MP3/M4A is not yet implemented.

## Next Priorities

## Phase 1: Command Completeness

Goal:

- Replace placeholder command behavior with true partial-pipeline execution.

Scope complete:

- `tts-only` implemented from manifest/artifacts with constrained replay (`tts` + `merge` + `manifest`).
- Integration coverage added for successful replay and prerequisite validation failures.

## Phase 2: Reliability Hardening

Goal:

- Improve resilience of external-provider stages.

Scope:

- Retry/backoff policy for provider calls.
- Better distinction of recoverable vs non-recoverable provider errors.
- Expanded resume validation around partially missing artifact sets.

## Phase 3: Audio Quality and Metadata

Goal:

- Improve output quality and playback metadata.

Scope:

- Enhanced postprocessing pipeline for merged WAV master artifact.
- Deterministic tagging metadata write path.
- Optional output packaging formats beyond merged WAV.
- Explicit AAC/MP3 delivery flow:
  - Deterministic export stage (`WAV -> MP3/M4A`).
  - Format-aware metadata tagging for packaged artifacts.
  - CLI/config controls for output format and encoding settings.

## Milestones

1. `v0.2.0`: fully functional command set (`build`, `chapters-only`, `list-chapters`, `resume`, `translate-only`, `tts-only`).
2. `v0.3.0`: provider reliability hardening and stronger resume robustness.
3. `v0.5.x`: merged WAV postprocessing and deterministic baseline tagging.
4. `v0.6.0`: AAC/MP3 packaging, format-aware tags, and CLI/config format controls.

## Backlog Mapping (Audio Packaging)

- `TASK-039`: Output packaging for AAC/MP3 deliverables (umbrella).
- `TASK-041`: Deterministic audio export stage for AAC/MP3.
- `TASK-042`: Format-aware metadata tagging for MP3 and M4A.
- `TASK-043`: CLI output format controls and manifest packaging metadata.
