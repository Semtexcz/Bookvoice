---
task: TASK-009
status: "done"
priority: P1
type: infra
---

# Improve minimal error handling and CLI diagnostics for MVP

Task: TASK-009
Status: done
Priority: P1
Type: infra
Author:
Created: 2026-02-20
Related: TASK-003, TASK-006, TASK-008

## Problem

Error reporting is currently ad-hoc and not structured for quick debugging of failed MVP runs.

## Definition of Done

- [x] Pipeline raises clear stage-specific exceptions for common failures.
- [x] CLI catches exceptions and prints concise, actionable messages.
- [x] Exit codes distinguish success vs failure.
- [x] README includes a short troubleshooting section for common MVP failures.

## Notes

- Do not implement full error taxonomy yet.
- Keep logging and diagnostics simple.
