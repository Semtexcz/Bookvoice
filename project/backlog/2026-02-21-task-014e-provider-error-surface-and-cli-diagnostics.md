---
task: TASK-014E
status: "backlog"
priority: P1
type: feature
---

# Provider error surface and actionable CLI diagnostics

Task: TASK-014E
Status: backlog
Priority: P1
Type: feature
Author:
Created: 2026-02-21
Related: TASK-014, TASK-009, TASK-014C, TASK-014D

## Problem

Real provider integrations introduce authentication, quota, request validation, and transient failure modes that are not clearly mapped in current CLI diagnostics.

## Definition of Done

- [ ] Define stage-specific provider error mapping for `translate`, `rewrite`, and `tts`.
- [ ] Ensure CLI messages expose actionable user hints for common cases (invalid key, insufficient quota, invalid model, timeout).
- [ ] Keep error messages concise and avoid leaking secrets.
- [ ] Add deterministic tests asserting stage, detail, and hint behavior for representative provider failures.

## Notes

- Align message style with existing `PipelineStageError` diagnostics.
- Keep transport-layer internals out of user-facing output unless actionable.
