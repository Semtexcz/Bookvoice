---
task: TASK-019
status: "backlog"
priority: P1
type: feature
---

# Add build progress indicator and pipeline stage logging

Task: TASK-019
Status: backlog
Priority: P1
Type: feature
Author:
Created: 2026-02-21
Related: TASK-009, TASK-014E

## Problem

The `bookvoice build` command can run for a longer time without visible activity in terminal output. Users cannot easily tell whether the process is still running or which stage is active.

## Definition of Done

- [ ] Add visible runtime activity feedback to `bookvoice build` (spinner like `|/-\\` or progress bar).
- [ ] Show clear stage transitions for pipeline phases (`extract`, `clean`, `split`, `chunk`, `translate`, `rewrite`, `tts`, `merge`, `manifest`).
- [ ] Integrate `loguru` for structured phase-level logging with deterministic, readable terminal output.
- [ ] Keep logs concise by default and avoid leaking secrets (API keys, credential material).
- [ ] Add tests that verify phase log emission and progress indicator activation in CLI output.
- [ ] Update `README.md` with logging/progress behavior and examples.

## Notes

- Preserve existing concise error surface and stage-aware diagnostics.
- Keep output deterministic enough for integration testing where feasible.
- Prefer a default output mode that remains readable in both local terminals and CI logs.
