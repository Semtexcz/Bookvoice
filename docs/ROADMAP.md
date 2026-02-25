# Roadmap

Reference date: 2026-02-25.

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

- Packaging, tagging, and playback metadata quality depend on local `ffmpeg`
  runtime/container support and player-specific metadata rendering behavior.

## Next Priorities

## Phase 1: Command Completeness

Goal:

- Replace placeholder command behavior with true partial-pipeline execution.

Scope complete:

- `tts-only` implemented from manifest/artifacts with constrained replay (`tts` + `merge` + `manifest`).
- Integration coverage added for successful replay and prerequisite validation failures.

## Phase 2: Reliability Hardening

Goal:

- Improve resilience of external-provider stages and delivery quality gates.

Scope:

- Retry/backoff policy for provider calls.
- Better distinction of recoverable vs non-recoverable provider errors.
- Expanded resume validation around partially missing artifact sets.
- Resolve current `mypy` baseline and make CI type-checking blocking.
- Add online model pricing resolution with deterministic fallback metadata.

## Phase 3: Learning Controls

Goal:

- Make language-learning output complexity explicit and reproducible.

Scope:

- User-selectable target language proficiency (`A0` to `C2`).
- Deterministic propagation to translation/rewrite prompt strategy.
- Manifest and artifact metadata persistence for replay/audit.

## Phase 4: Audio Quality and Metadata Controls

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
  - Backward-compatible migration from current `--package-mode` semantics.

## Milestones

1. `M1` (completed): functional command set (`build`, `chapters-only`, `list-chapters`, `resume`, `translate-only`, `tts-only`).
2. `M2` (next): reliability hardening gate (`mypy` blocking in CI) and model-aware pricing metadata.
3. `M3`: CEFR learning controls (`A0`-`C2`) across prompt policy and replay metadata.
4. `M4`: finalized packaging/output controls (format/encoding/layout/naming) with compatibility guarantees.

## Active Backlog Mapping

- `TASK-051` (Phase 2): Mypy baseline cleanup and blocking CI gate.
- `TASK-015` (Phase 2): Online model pricing for cost tracking with fallback source metadata.
- `TASK-044` (Phase 3): Language proficiency level control (`A0`-`C2`) for learning-friendly outputs.
- `TASK-043` (Phase 4): CLI output format controls and manifest packaging metadata.
