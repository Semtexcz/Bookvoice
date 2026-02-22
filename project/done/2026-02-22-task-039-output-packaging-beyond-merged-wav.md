---
task: TASK-039
status: "done"
priority: P3
type: feature
---

# Output packaging for AAC/MP3 deliverables

Task: TASK-039
Status: done
Priority: P3
Type: feature
Author:
Created: 2026-02-22
Related: TASK-038

## Problem

Roadmap Phase 3 includes packaging formats beyond merged WAV. Current pipeline emits deterministic WAV artifacts only, while audiobook delivery commonly expects chapter-split AAC (`.m4a`) or MP3 outputs.

## Definition of Done

- [x] Define packaging abstraction that treats merged WAV as the deterministic master artifact and adds optional lossy export as a separate stage.
- [x] Implement chapter-split packaged outputs (one chapter = one output file) for AAC (`.m4a`) and MP3 with deterministic naming and manifest metadata.
- [x] Use AAC (`.m4a`) as primary packaged target and MP3 as secondary packaged target.
- [x] Keep default behavior unchanged (`bookvoice_merged.wav`) when packaging is not requested.
- [x] Allow packaging mode that keeps full merged deliverable in addition to chapter-split files.
- [x] Ensure resume and `tts-only` replay preserve packaging determinism and avoid unnecessary re-encoding drift.
- [x] Add tests for packaged output generation, deterministic manifest references, and replay-safe behavior.
- [x] Document CLI usage, artifact structure, and known codec/runtime limitations.

## Notes

- Packaging should be an additive step after core synthesis/merge success.
- External local tooling (for example `ffmpeg`) is acceptable if behavior and diagnostics remain deterministic.
- Chapter numbering strategy must be user-selectable (`source` or `sequential`).
