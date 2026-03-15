---
task: TASK-072
status: "backlog"
priority: P1
type: feature
---

# Preserve source images in translated PDF export

Task: TASK-072
Status: backlog
Priority: P1
Type: feature
Author:
Created: 2026-03-15
Related: TASK-065, TASK-069, TASK-070

## Problem

Translated `PDF` export will lose important reading context if source graphics
are omitted. A reader-focused translated PDF should carry forward embedded
images even when full page fidelity is not preserved.

## Definition of Done

- [ ] Extend the translated `PDF` export path to render preserved source images
      alongside translated headings and paragraphs.
- [ ] Define deterministic image scaling, placement, and page-break behavior
      suitable for digital reading.
- [ ] Define fallback behavior for oversized, unsupported, or low-quality source
      images.
- [ ] Add automated tests covering image presence and ordering in generated
      `PDF` output.
- [ ] Update user documentation with at least one example that explains image
      preservation behavior in translated `PDF` output.

## Notes

- Optimize for readable digital output rather than exact facsimile layout.
- Do not change audiobook-oriented translation or TTS flows in this task.
