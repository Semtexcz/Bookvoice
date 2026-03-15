---
task: TASK-064
status: "done"
priority: P1
type: feature
---

# Export translated books as EPUB

Task: TASK-064
Status: done
Priority: P1
Type: feature
Author:
Created: 2026-03-15
Related: TASK-062, TASK-063

## Problem

Bookvoice does not currently emit `EPUB`, which blocks use as a translator-only
tool for e-readers and ebook applications.

## Definition of Done

- [x] Implement deterministic `EPUB` export from the canonical translated
      document artifact.
- [x] Generate valid navigation, ordered chapter content, and required package
      metadata for common e-readers.
- [x] Preserve translated language metadata and human-readable title/chapter
      labels in the exported file.
- [x] Define and test deterministic output naming and destination paths.
- [x] Add automated tests that validate basic `EPUB` structure and chapter
      ordering.
- [x] Update user documentation with at least one example of `EPUB` export.

## Notes

- Prefer standards-compliant, minimal `EPUB` generation over visual complexity.
- Initial scope does not require cover generation unless needed for compatibility.
