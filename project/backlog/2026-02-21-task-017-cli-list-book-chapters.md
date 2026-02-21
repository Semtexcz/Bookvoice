---
task: TASK-017
status: "backlog"
priority: P1
type: feature
---

# Add CLI command to list extracted book chapters

Task: TASK-017
Status: backlog
Priority: P1
Type: feature
Author:
Created: 2026-02-21
Related: TASK-013, TASK-016

## Problem

Current CLI can generate chapter artifacts (`chapters-only`), but it cannot print a concise chapter list directly in terminal. This slows down validation and chapter-boundary debugging during iterative testing.

## Definition of Done

- [ ] Add a dedicated CLI command to list chapters for a selected input source.
- [ ] Command supports listing chapters from `text/chapters.json` artifact and from source PDF via existing extract/clean/split flow.
- [ ] Output includes chapter index and title in deterministic order.
- [ ] Output includes extraction metadata (`pdf_outline` vs `text_heuristic`) and fallback reason when applicable.
- [ ] Command exits with clear stage-aware errors when chapter source data is missing or invalid.
- [ ] Tests cover one successful listing path and one failure path with invalid/missing chapter artifact.
- [ ] README includes usage examples for chapter listing.

## Notes

- Reuse existing chapter extraction and artifact-loading code paths; do not duplicate split logic.
- Keep output compact for terminal use and deterministic for snapshot-style assertions.
