---
task: TASK-008
status: "backlog"
priority: P1
type: feature
---

# Add basic resume support from manifest and existing artifacts

Task: TASK-008
Status: backlog
Priority: P1
Type: feature
Author:
Created: 2026-02-20
Related: TASK-002, TASK-007, TASK-010

## Problem

`resume` command currently only prints placeholder output. MVP stabilization requires practical continuation from partially completed runs.

## Definition of Done

- [ ] `resume` reads manifest and determines the next runnable stage.
- [ ] Existing artifacts are reused when present.
- [ ] Missing critical artifacts produce actionable error messages.
- [ ] At least one integration test covers interrupted-run resume.

## Notes

- Implement only common happy-path resume behavior.
- Deep recovery logic remains post-MVP.
