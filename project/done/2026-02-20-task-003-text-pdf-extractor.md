---
task: TASK-003
status: "done"
priority: P0
type: feature
---

# Implement first concrete text PDF extractor

Task: TASK-003
Status: done
Priority: P0
Type: feature
Author:
Created: 2026-02-20
Related: TASK-001, TASK-004

## Problem

`PdfTextExtractor` is currently a placeholder. MVP cannot proceed without real text extraction from text-native PDFs.

## Definition of Done

- [x] A concrete extractor implementation is added and wired into pipeline extraction stage.
- [x] `extract` returns full-document text for text-based PDFs.
- [x] `extract_pages` returns page-ordered text segments.
- [x] Failure mode for unreadable or unsupported PDF is explicit and user-visible.

## Notes

- MVP scope is text-native PDFs only.
- OCR/scanned PDFs are out of scope for this task.
