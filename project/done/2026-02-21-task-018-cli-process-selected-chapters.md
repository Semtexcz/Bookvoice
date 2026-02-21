---
task: TASK-018
status: "done"
priority: P1
type: feature
---

# Add CLI chapter selection for partial processing

Task: TASK-018
Status: done
Priority: P1
Type: feature
Author:
Created: 2026-02-21
Related: TASK-004, TASK-016, TASK-017

## Problem

Current pipeline commands process all chapters for a run. There is no CLI control to process only selected chapters (for example one chapter, comma-separated list, or range), which makes testing slower and more expensive.

## Definition of Done

- [x] Add CLI options to select chapter subset for processing (single chapter, list, and closed range).
- [x] Selection syntax is validated with actionable errors (invalid indices, overlapping or malformed ranges, out-of-bound chapters).
- [x] Pipeline processes only selected chapters for downstream stages and skips non-selected chapters deterministically.
- [x] Generated artifacts (`chunks`, `translations`, `rewrites`, `audio_parts`, merged output, manifest) reflect selected-chapter scope explicitly.
- [x] Resume behavior remains correct for partial runs and does not reprocess excluded chapters.
- [x] Tests cover valid single/list/range selection and invalid selection error cases.
- [x] README documents syntax, examples, and testing-focused usage recommendations.

## Notes

- Keep chapter indexing 1-based and aligned with `chapters.json`.
- Prefer one canonical parser for chapter selection syntax reused across commands.
- Ensure deterministic ordering of processed chapters even when list input is unsorted.
