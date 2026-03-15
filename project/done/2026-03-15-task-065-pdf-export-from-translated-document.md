---
task: TASK-065
status: "done"
priority: P1
type: feature
---

# Export translated books as reader-friendly PDF

Task: TASK-065
Status: done
Priority: P1
Type: feature
Author:
Created: 2026-03-15
Related: TASK-062, TASK-063

## Problem

Bookvoice does not currently emit translated `PDF` output for reading devices.
Users who only want translated text cannot receive a portable PDF deliverable.

## Definition of Done

- [x] Implement deterministic translated `PDF` export from the canonical
      translated document artifact.
- [x] Produce readable title, chapter, and paragraph layout suitable for common
      reading-device PDF viewers.
- [x] Define an initial Unicode-safe font and text-wrapping strategy with clear
      behavior for unsupported glyphs.
- [x] Define and test deterministic output naming and destination paths.
- [x] Add automated tests covering basic document generation and chapter order.
- [x] Update user documentation with at least one example of translated `PDF`
      export.

## Notes

- Optimize for readable digital output, not print publishing fidelity.
- If a new PDF-generation dependency is required, document the justification and
      maintenance tradeoff explicitly.
