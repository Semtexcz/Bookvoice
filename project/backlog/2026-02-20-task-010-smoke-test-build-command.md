---
task: TASK-010
status: "backlog"
priority: P1
type: test
---

# Add smoke test coverage for full build command

Task: TASK-010
Status: backlog
Priority: P1
Type: test
Author:
Created: 2026-02-20
Related: TASK-001, TASK-008

## Problem

There is no automated confidence check that the main user journey (`build`) remains functional after changes.

## Definition of Done

- [ ] A smoke test runs `bookvoice build` on a controlled text-PDF fixture.
- [ ] Test verifies final audio artifact and manifest are produced.
- [ ] Test is runnable locally with standard Python tooling.
- [ ] Test failure output clearly indicates failing pipeline stage.

## Notes

- Keep fixture small for fast execution.
- Heavy provider integration tests are out of scope for this task.
