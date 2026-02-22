---
task: TASK-030
status: "backlog"
priority: P3
type: refactor
---

# Extract CLI output and error rendering helpers

Task: TASK-030
Status: backlog
Priority: P3
Type: refactor
Author:
Created: 2026-02-22
Related: TASK-029, TASK-014E

## Problem

`bookvoice/cli.py` contains repeated output formatting responsibilities (cost summaries, chapter summaries/lists, stage error rendering). Presentation logic is coupled to command control flow, making incremental diagnostics changes risky.

## Definition of Done

- [ ] Move command output rendering helpers from `bookvoice/cli.py` into a dedicated rendering module.
- [ ] Keep output text and ordering stable for existing integration tests.
- [ ] Keep `PipelineStageError` rendering centralized in one helper path used by all commands.
- [ ] Add/adjust tests to assert renderer behavior directly (stage error with hint, non-stage error fallback).

## Notes

- This task is a structural extraction only.
- Do not alter progress indicator format in this task.
