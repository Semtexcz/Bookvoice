---
task: TASK-021
status: "done"
priority: P1
type: feature
---

# Parent Task: Structure-aware audio part planning with text budgets

Task: TASK-021
Status: done
Priority: P1
Type: feature
Author:
Created: 2026-02-21
Related: TASK-014, TASK-019, TASK-022, TASK-023, TASK-024, TASK-025, TASK-026

## Problem

Current audio generation does not yet provide a clear, structure-aware strategy for producing practical recording parts. This affects listening usability, chapter navigation, and consistency across books with chapter/subchapter hierarchy.

## Definition of Done

- [x] Split this work into child tasks and keep scope separated by pipeline concern.
- [x] Complete child task `TASK-024` (chapter/subchapter structure extraction and normalization).
- [x] Complete child task `TASK-025` (text-budget segment planning and merge rules).
- [x] Complete child task `TASK-026` (pipeline integration, artifacts, and resume behavior).
- [x] Validate compatibility with existing tasks `TASK-022` (filename convention) and `TASK-023` (sentence-complete chunk boundaries).
- [x] Update `README.md` with the final end-to-end behavior once child tasks are completed.

## Notes

- This is a coordination task for a larger feature and should not carry implementation detail that belongs to child tasks.
- Audio-length control is character-budget-based, not post-generation trimming.
- Compatibility validation:
  - `TASK-022`: deterministic part filename convention is enforced by synthesis output naming (`<chapter>_<part>_<title-slug>.wav`) and artifact assertions in integration tests.
  - `TASK-023`: sentence-complete boundaries remain a dedicated follow-up concern; current segment planning keeps deterministic chapter/part metadata and stable ordering so sentence-boundary logic can be added without changing artifact contracts.
