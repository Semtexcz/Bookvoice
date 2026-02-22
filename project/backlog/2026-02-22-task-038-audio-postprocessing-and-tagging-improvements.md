---
task: TASK-038
status: "backlog"
priority: P2
type: feature
---

# Audio postprocessing and metadata tagging improvements

Task: TASK-038
Status: backlog
Priority: P2
Type: feature
Author:
Created: 2026-02-22
Related: TASK-007, TASK-026

## Problem

Roadmap Phase 3 calls out minimal audio postprocessing and metadata tagging. Current output quality/metadata behavior is intentionally basic.

## Definition of Done

- [ ] Implement deterministic postprocessing steps for merged output (for example peak normalization and silence trimming policy) with explicit, testable defaults.
- [ ] Add deterministic metadata tagging path (title, chapter/part context, source identifiers) for emitted audio files where format supports tags.
- [ ] Ensure postprocessing/tagging can be replayed safely in resume and `tts-only` flows without artifact drift.
- [ ] Add tests for postprocessing determinism and metadata/tag presence.
- [ ] Update `README.md` and `docs/ARTIFACTS.md` with new output behavior and limitations.

## Notes

- Keep implementation format-aware and avoid introducing lossy transcoding by default.
- Configuration surface should remain minimal and explicit.
