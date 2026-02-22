---
task: TASK-041
status: "backlog"
priority: P2
type: feature
---

# Deterministic audio export stage for AAC/MP3

Task: TASK-041
Status: backlog
Priority: P2
Type: feature
Author:
Created: 2026-02-22
Related: TASK-039, TASK-038

## Problem

The pipeline currently ends at merged WAV output. We need an explicit, deterministic export stage that can produce chapter-split delivery files (`.m4a`/AAC primary, `.mp3` secondary) from the merged WAV/chapter-part master artifacts.

## Definition of Done

- [ ] Add a dedicated export/packaging stage after merge that consumes WAV artifacts as source-of-truth.
- [ ] Implement deterministic chapter-level export (one chapter = one audio file) for AAC (`.m4a`) and MP3 via local encoder toolchain (for example `ffmpeg`) with explicit codec/bitrate defaults.
- [ ] Set AAC (`.m4a`) as primary export target; MP3 remains explicitly available as a secondary target.
- [ ] Persist packaged outputs under deterministic filenames and artifact paths.
- [ ] Keep merged WAV generation and optional full merged packaged output available when chapter packaging is enabled.
- [ ] Add stage-aware failure diagnostics for missing encoder/runtime dependencies.
- [ ] Add tests for deterministic output path naming and export-stage invocation behavior.
- [ ] Add tests for chapter packaging determinism under both numbering modes (`source`, `sequential`).

## Notes

- Avoid in-place modification of merged WAV during export.
- Keep export policy explicit and minimal (no hidden quality presets).
- Naming policy should support:
  - reader-friendly style: `<NN> - <Chapter Title>.<ext>`
  - deterministic internal-safe style: `chapter_<NNN>_<chapter-title-slug>.<ext>`
