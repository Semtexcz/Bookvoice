---
task: TASK-021
status: "backlog"
priority: P1
type: feature
---

# Parent Task: Structure-aware audio part planning with text budgets

Task: TASK-021
Status: backlog
Priority: P1
Type: feature
Author:
Created: 2026-02-21
Related: TASK-014, TASK-019, TASK-022, TASK-023, TASK-024, TASK-025, TASK-026

## Problem

Current audio generation does not yet provide a clear, structure-aware strategy for producing practical recording parts. This affects listening usability, chapter navigation, and consistency across books with chapter/subchapter hierarchy.

## Definition of Done

- [ ] Split this work into child tasks and keep scope separated by pipeline concern.
- [x] Complete child task `TASK-024` (chapter/subchapter structure extraction and normalization).
- [x] Complete child task `TASK-025` (text-budget segment planning and merge rules).
- [x] Complete child task `TASK-026` (pipeline integration, artifacts, and resume behavior).
- [ ] Validate compatibility with existing tasks `TASK-022` (filename convention) and `TASK-023` (sentence-complete chunk boundaries).
- [ ] Update `README.md` with the final end-to-end behavior once child tasks are completed.

## Notes

- This is a coordination task for a larger feature and should not carry implementation detail that belongs to child tasks.
- Audio-length control is character-budget-based, not post-generation trimming.
