---
task: TASK-025
status: "backlog"
priority: P1
type: feature
---

# Implement text-budget segment planner with paragraph boundaries

Task: TASK-025
Status: backlog
Priority: P1
Type: feature
Author:
Created: 2026-02-21
Related: TASK-021, TASK-023, TASK-024

## Problem

Segment planning is needed to keep recordings practical while preserving textual structure. The planner must use text budgets, paragraph boundaries, and chapter/subchapter rules.

## Definition of Done

- [ ] Implement deterministic segment planning based on character budget.
- [ ] Set default budget to `6500` characters (approximately 7 minutes).
- [ ] Treat 10-minute target as an upper character-budget ceiling.
- [ ] Prefer segment boundaries at paragraph breaks and avoid paragraph cuts unless unavoidable.
- [ ] Keep chapter boundary strict: each chapter has its own recording output, even when short.
- [ ] Allow short subchapters to be merged when they fit within active budget and chapter boundary rules.
- [ ] Produce a deterministic segment plan data structure consumable by pipeline/TTS stages.
- [ ] Add tests for budget split behavior, merge behavior, and stability across repeated runs.

## Notes

- This task should not change output filenames.
- Sentence-complete chunking expectations remain governed by `TASK-023`.
