---
task: TASK-025
status: "done"
priority: P1
type: feature
---

# Implement text-budget segment planner with paragraph boundaries

Task: TASK-025
Status: done
Priority: P1
Type: feature
Author:
Created: 2026-02-21
Related: TASK-021, TASK-023, TASK-024

## Problem

Segment planning is needed to keep recordings practical while preserving textual structure. The planner must use text budgets, paragraph boundaries, and chapter/subchapter rules.

## Definition of Done

- [x] Implement deterministic segment planning based on character budget.
- [x] Set default budget to `6500` characters (approximately 7 minutes).
- [x] Treat 10-minute target as an upper character-budget ceiling.
- [x] Prefer segment boundaries at paragraph breaks and avoid paragraph cuts unless unavoidable.
- [x] Keep chapter boundary strict: each chapter has its own recording output, even when short.
- [x] Allow short subchapters to be merged when they fit within active budget and chapter boundary rules.
- [x] Produce a deterministic segment plan data structure consumable by pipeline/TTS stages.
- [x] Add tests for budget split behavior, merge behavior, and stability across repeated runs.

## Notes

- This task should not change output filenames.
- Sentence-complete chunking expectations remain governed by `TASK-023`.
