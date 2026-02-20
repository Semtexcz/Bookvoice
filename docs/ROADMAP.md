# Roadmap (Fast MVP First)

This roadmap prioritizes one outcome above all else:

**Convert a text-based PDF into a playable audiobook as quickly as possible.**

Reference date: 2026-02-20.

## Product Priority

- Primary goal: `PDF (text) -> translated/rewritten text -> synthesized audio file`.
- Edge cases are explicitly deferred until after MVP.
- Initial implementation can be pragmatic and narrow if it works reliably for happy-path inputs.

## MVP Scope (What must work)

- CLI command: `bookvoice build input.pdf --out out/`.
- Text-native PDF extraction (single backend).
- Basic cleanup and chunking (simple deterministic rules).
- One translation/rewriter path (or bypass rewrite if needed for first playable output).
- One TTS path.
- Merge chunk audio into one final audiobook file.
- Write a minimal `RunManifest` with key outputs and config hash.

## Explicit Non-Goals for MVP

- OCR/scanned PDFs.
- Advanced chapter detection heuristics.
- Sophisticated retries/rate-limiting/caching strategies.
- Rich metadata tagging and advanced audio mastering.
- Full observability stack and broad test matrix.

## Execution Plan

## Phase A: Thin Vertical Slice (Target: 3-5 days)

Goal:
- Ship the fastest possible end-to-end happy path.

Scope:
- Wire pipeline stages so `build` produces a final merged audio artifact.
- Implement minimal `ArtifactStore` filesystem reads/writes.
- Keep one default provider path for translation and TTS.
- Keep logs simple (stdout is enough).

Definition of done:
- Running `bookvoice build sample.pdf --out out/` produces:
  - extracted/intermediate text artifacts,
  - chunk-level audio parts,
  - one merged playable output file,
  - a `RunManifest` file.

## Phase B: MVP Stabilization (Target: 4-7 days)

Goal:
- Make happy-path execution predictable for repeated runs.

Scope:
- Basic resume support from manifest/artifacts.
- Minimal failure handling with clear user-facing errors.
- Basic cost tracking in manifest (`LLM`, `TTS`, total).
- Add smoke tests for CLI + pipeline integration path.

Definition of done:
- Re-running the same command with same input/config does not break output generation.
- `resume` can continue a partially completed run in common scenarios.
- Smoke tests cover the main build flow.

## Phase C: Post-MVP Hardening (After first usable release)

Goal:
- Improve reliability, scale, and quality without blocking MVP delivery.

Scope:
- Better caching strategy and deterministic cache keys.
- Retry/backoff and rate limiting.
- Better chapter splitting and extraction diagnostics.
- Audio postprocessing improvements and metadata writing.
- Expanded tests, CI quality gates, and contributor workflow.

Definition of done:
- Failures are easier to recover from and diagnose.
- Runtime cost and latency are reduced on repeated runs.
- Project is ready for broader open-source usage.

## Milestones

1. `v0.2.0-mvp`: first working PDF-to-audiobook happy path.
2. `v0.3.0`: stabilization (resume, smoke tests, clearer errors).
3. `v0.4.0`: hardening and quality improvements.

## Implementation Order (Immediate)

1. Implement real filesystem `ArtifactStore`.
2. Implement one concrete text PDF extractor.
3. Implement simple chapter split + chunk path.
4. Implement one translator/rewriter execution path (minimal).
5. Implement one TTS provider path.
6. Implement merge step and manifest write.
7. Add smoke test for full `build` command.

This order is intentionally optimized for fastest delivery of an audible result, not for completeness.
