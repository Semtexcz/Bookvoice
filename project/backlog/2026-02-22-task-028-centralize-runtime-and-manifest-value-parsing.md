---
task: TASK-028
status: "backlog"
priority: P2
type: refactor
---

# Centralize runtime and manifest value parsing rules

Task: TASK-028
Status: backlog
Priority: P2
Type: refactor
Author:
Created: 2026-02-22
Related: TASK-027

## Problem

Boolean and normalized-string parsing logic is duplicated across `bookvoice/config.py` and `bookvoice/pipeline/resume.py` (`_parse_boolean_value`, `manifest_bool`, `manifest_string`). This creates hidden coupling and risk of subtle behavior mismatch.

## Definition of Done

- [ ] Extract shared parsing helpers for normalized string and permissive boolean parsing into a dedicated module (for example `bookvoice/pipeline/parsing.py` or `bookvoice/utils/parsing.py`).
- [ ] Update `bookvoice/config.py` and `bookvoice/pipeline/resume.py` to use shared helpers.
- [ ] Keep current accepted boolean tokens and fallback behavior unchanged.
- [ ] Add focused unit tests for parsing edge cases (blank values, mixed case, invalid boolean tokens).

## Notes

- This task is internal cleanup only; no CLI interface changes.
- Keep error message text stable where tests depend on it.
