# Roadmap

Reference date: 2026-02-21.

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

- `translate-only` and `tts-only` commands are placeholders.
- Postprocessing and metadata tagging are minimal.
- `ConfigLoader.from_yaml` and `ConfigLoader.from_env` remain placeholders.

## Next Priorities

## Phase 1: Command Completeness

Goal:
- Replace placeholder command behavior with true partial-pipeline execution.

Scope:
- Implement real `translate-only`.
- Implement real `tts-only` from manifest/artifacts.
- Add integration tests for both command paths.

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
- Enhanced postprocessing pipeline.
- Deterministic tagging metadata write path.
- Optional output packaging formats beyond merged WAV.

## Milestones

1. `v0.2.0`: fully functional command set (`build`, `chapters-only`, `list-chapters`, `resume`, `translate-only`, `tts-only`).
2. `v0.3.0`: provider reliability hardening and stronger resume robustness.
3. `v0.4.0`: audio quality and metadata improvements.
