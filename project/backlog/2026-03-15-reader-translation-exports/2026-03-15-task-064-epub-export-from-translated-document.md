---
task: TASK-064
status: "backlog"
priority: P1
type: feature
---

# Export translated books as EPUB

Task: TASK-064
Status: backlog
Priority: P1
Type: feature
Author:
Created: 2026-03-15
Related: TASK-062, TASK-063

## Problem

Bookvoice does not currently emit `EPUB`, which blocks use as a translator-only
tool for e-readers and ebook applications.

## Definition of Done

- [ ] Implement deterministic `EPUB` export from the canonical translated
      document artifact.
- [ ] Generate valid navigation, ordered chapter content, and required package
      metadata for common e-readers.
- [ ] Preserve translated language metadata and human-readable title/chapter
      labels in the exported file.
- [ ] Define and test deterministic output naming and destination paths.
- [ ] Add automated tests that validate basic `EPUB` structure and chapter
      ordering.
- [ ] Update user documentation with at least one example of `EPUB` export.

## Notes

- Prefer standards-compliant, minimal `EPUB` generation over visual complexity.
- Initial scope does not require cover generation unless needed for compatibility.
