---
task: TASK-067
status: "backlog"
priority: P1
type: feature
---

# Add EPUB text and chapter extraction

Task: TASK-067
Status: backlog
Priority: P1
Type: feature
Author:
Created: 2026-03-15
Related: TASK-066

## Problem

Bookvoice has no extraction path for `EPUB` sources. To translate ebooks
directly, the pipeline must be able to read ordered text and chapter boundaries
from `EPUB` packages deterministically.

## Definition of Done

- [ ] Implement `EPUB` extraction that reads package metadata, spine order, and
      document text from the archive.
- [ ] Normalize extracted content into the chapter/text structures expected by
      downstream pipeline stages.
- [ ] Support chapter discovery from navigation metadata when available, with a
      documented fallback when explicit TOC data is missing.
- [ ] Add a synthetic repository-owned `EPUB` fixture suitable for deterministic
      tests.
- [ ] Add automated tests for successful extraction, chapter ordering, and
      missing-metadata fallback behavior.

## Notes

- Keep extraction deterministic; avoid renderer-dependent HTML interpretation.
- Prefer standard-library or already-approved parsing approaches unless a new
      dependency is clearly justified.
