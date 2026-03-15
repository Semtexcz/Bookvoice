---
task: TASK-065
status: "backlog"
priority: P1
type: feature
---

# Export translated books as reader-friendly PDF

Task: TASK-065
Status: backlog
Priority: P1
Type: feature
Author:
Created: 2026-03-15
Related: TASK-062, TASK-063

## Problem

Bookvoice does not currently emit translated `PDF` output for reading devices.
Users who only want translated text cannot receive a portable PDF deliverable.

## Definition of Done

- [ ] Implement deterministic translated `PDF` export from the canonical
      translated document artifact.
- [ ] Produce readable title, chapter, and paragraph layout suitable for common
      reading-device PDF viewers.
- [ ] Define an initial Unicode-safe font and text-wrapping strategy with clear
      behavior for unsupported glyphs.
- [ ] Define and test deterministic output naming and destination paths.
- [ ] Add automated tests covering basic document generation and chapter order.
- [ ] Update user documentation with at least one example of translated `PDF`
      export.

## Notes

- Optimize for readable digital output, not print publishing fidelity.
- If a new PDF-generation dependency is required, document the justification and
      maintenance tradeoff explicitly.
