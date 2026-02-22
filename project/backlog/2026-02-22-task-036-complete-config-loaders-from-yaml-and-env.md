---
task: TASK-036
status: "backlog"
priority: P2
type: feature
---

# Complete `ConfigLoader.from_yaml` and `ConfigLoader.from_env`

Task: TASK-036
Status: backlog
Priority: P2
Type: feature
Author:
Created: 2026-02-22
Related: TASK-014A, TASK-028, TASK-029

## Problem

`ConfigLoader.from_yaml` and `ConfigLoader.from_env` are still placeholders. This leaves runtime configuration incomplete and keeps roadmap constraints unresolved.

## Definition of Done

- [ ] Implement `ConfigLoader.from_yaml` with explicit schema validation and clear errors for missing/invalid fields.
- [ ] Implement `ConfigLoader.from_env` for all supported runtime keys, including provider/model/voice and rewrite bypass values.
- [ ] Keep deterministic precedence behavior compatible with CLI/runtime source resolution (`CLI > secure > env > defaults`).
- [ ] Add focused unit tests for valid config load, invalid field handling, and blank/typed value normalization.
- [ ] Document supported YAML keys and environment variables in `README.md`.

## Notes

- Keep parsing strict enough to prevent silent misconfiguration.
- Reuse shared parsing helpers from `bookvoice/parsing.py` where applicable.
