---
task: TASK-071
status: "backlog"
priority: P1
type: feature
---

# Preserve source images in translated EPUB export

Task: TASK-071
Status: backlog
Priority: P1
Type: feature
Author:
Created: 2026-03-15
Related: TASK-064, TASK-069, TASK-070

## Problem

Translated `EPUB` export will be incomplete for many books if it drops source
graphics. E-readers expect embedded assets to remain part of the reading
experience.

## Definition of Done

- [ ] Extend the translated `EPUB` export path to embed preserved source images
      and reference them from generated chapter content.
- [ ] Define deterministic placement behavior for images relative to translated
      paragraphs and headings.
- [ ] Ensure package metadata and manifest records reflect preserved image
      assets where relevant.
- [ ] Add automated tests for embedded-image presence, content references, and
      chapter ordering in generated `EPUB` files.
- [ ] Update user documentation with at least one example that explains image
      preservation behavior in translated `EPUB` output.

## Notes

- Prioritize standards-compliant embedding and stable reading behavior across
  common `EPUB` readers.
- Do not attempt OCR or image-text translation in this task.
