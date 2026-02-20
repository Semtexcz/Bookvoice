# Roadmap

This roadmap defines a pragmatic path from scaffold to production-ready, deterministic audiobook generation for Czech outputs.

## Planning Horizon

- Reference date: 2026-02-20.
- Timeline style: target windows, not hard deadlines.
- Delivery principle: each phase should leave the project in a usable state.

## Phase 0: Foundation Hardening (Target: 1-2 weeks)

Goals:
- Keep current scaffold coherent after CLI migration to Typer.
- Establish basic quality gates before adding provider logic.

Scope:
- Add unit tests for datatypes, CLI command wiring, and pipeline stage ordering.
- Add placeholder CI workflow (lint/test/type-check commands can remain TODO).
- Standardize error classes for deterministic vs external failures.

Definition of done:
- CI runs on pull requests and executes at least a smoke test suite.
- Core modules (`config`, `pipeline`, `models`, `cli`) have baseline tests.
- No circular imports introduced by new changes.

## Phase 1: Deterministic Local Pipeline MVP (No External APIs) (Target: 2-4 weeks)

Goals:
- Make the pipeline produce real intermediate artifacts locally without third-party services.
- Validate resumability and manifest reproducibility end-to-end.

Scope:
- Implement local filesystem `ArtifactStore` read/write behavior.
- Implement deterministic chapter splitting and chunk generation with tests.
- Implement manifest persistence with config hash + stage metadata.
- Add `resume` logic based on existing artifacts and manifest state.

Definition of done:
- `bookvoice build input.pdf --out out/` creates reproducible text/manifests for the same input.
- `bookvoice resume ...` skips already completed deterministic stages.
- Re-running the same config produces identical manifest hashes (except timestamp fields, if any).

## Phase 2: PDF Extraction Backends (Target: 2-3 weeks)

Goals:
- Replace extraction stubs with pluggable text extraction implementations.
- Preserve deterministic output normalization across backends.

Scope:
- Add backend abstraction variants for text-native and OCR-capable workflows (future optional deps).
- Implement page-level extraction and stable ordering guarantees.
- Add extractor quality checks (empty-page rates, suspicious character ratios).

Definition of done:
- At least one production-capable extractor backend integrated.
- Extraction output is persisted and can be reused without re-extraction.
- Extraction failures are classified as recoverable/non-recoverable.

## Phase 3: LLM Translation + Rewrite Integration (Target: 2-4 weeks)

Goals:
- Integrate real translation and rewrite providers with cost control.
- Ensure chunk-level caching for pay-as-you-go behavior.

Scope:
- Implement `Translator` and `AudioRewriter` provider adapters.
- Implement `ResponseCache` with deterministic keying.
- Implement retry policy and rate limiter behavior.
- Track usage costs via `CostTracker` and include in `RunManifest`.

Definition of done:
- Chunk cache hits prevent repeated provider calls for unchanged inputs.
- Failed chunk calls are retried with bounded backoff and logged.
- Manifest includes provider/model usage metadata and cost summary.

## Phase 4: TTS + Audio Assembly (Target: 2-4 weeks)

Goals:
- Produce listenable audiobook outputs with pluggable voices.
- Provide deterministic part ordering and merge behavior.

Scope:
- Implement real `TTSSynthesizer` provider adapter(s).
- Integrate audio postprocessing and merge pipeline (future ffmpeg integration).
- Implement metadata writing (`MetadataWriter`) for final output.

Definition of done:
- `build` produces merged audiobook output file(s) and metadata.
- `tts-only` can regenerate audio from cached rewrite artifacts.
- Output ordering is stable across repeated runs.

## Phase 5: Reliability, Observability, and Release Readiness (Target: 2-3 weeks)

Goals:
- Prepare for open-source adoption and real-world runs.
- Make failures diagnosable and recovery predictable.

Scope:
- Structured run logs with stage-level durations and statuses.
- Better error taxonomy and user-facing CLI diagnostics.
- Expand tests to include integration scenarios and resume behavior.
- Document contribution flow, coding standards, and release process.

Definition of done:
- Deterministic regression test coverage for key pipeline paths.
- Clear troubleshooting docs for common failure classes.
- Versioned release checklist and first stable pre-release tag.

## Cross-Cutting Workstreams

- Security and compliance:
  - Keep explicit non-goals: no DRM bypass, respect copyright.
- Performance:
  - Optimize chunk sizing and concurrency without breaking determinism.
- Developer experience:
  - Improve local dev commands and fixture-based testing flows.

## Deferred / Out of Scope for Initial Releases

- Full OCR research and advanced layout reconstruction.
- Voice cloning or speaker diarization features.
- GUI application.

## Suggested Milestones

1. `v0.2.0`: deterministic local MVP with persisted manifests and resume.
2. `v0.3.0`: first provider-backed translation/rewrite with cache + costs.
3. `v0.4.0`: first provider-backed TTS output and audio assembly.
4. `v0.5.0`: reliability pass, documentation hardening, pre-release quality bar.
