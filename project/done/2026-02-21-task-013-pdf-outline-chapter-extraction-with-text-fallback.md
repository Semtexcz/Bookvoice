---
task: TASK-013
status: "done"
priority: P1
type: feature
---

# Prefer PDF outline chapter extraction with deterministic text fallback

Task: TASK-013
Status: done
Priority: P1
Type: feature
Author:
Created: 2026-02-21
Related: TASK-003, TASK-004

## Problem

Chapter splitting currently depends on text heuristics only. Many PDFs already contain chapter structure in outline/bookmarks, which can provide more accurate boundaries than plain text matching.

## Definition of Done

- [x] Add a PDF chapter extractor that reads outline/bookmarks when available.
- [x] Pipeline prefers PDF outline-based chapters before text heuristic splitting.
- [x] If outline is missing/invalid, pipeline deterministically falls back to `ChapterSplitter.split(clean_text)`.
- [x] Chapter ordering and indices remain stable for the same input.
- [x] Tests cover both paths: outline-present and fallback-to-text.

## Notes

- MVP scope: use first-level outline entries only; nested structure can be deferred.
- Keep fallback behavior explicit and observable in logs/manifest metadata.
