---
task: TASK-040
status: "done"
priority: P2
type: feature
---

# Add CLI config-file loading and precedence integration

Task: TASK-040
Status: done
Priority: P2
Type: feature
Author:
Created: 2026-02-22
Related: TASK-036, TASK-029

## Problem

`ConfigLoader.from_yaml` and `ConfigLoader.from_env` are implemented, but CLI commands do not consume them. Users cannot pass a config file directly to `build`/`translate-only`/`tts-only` flows, which keeps configuration management fragmented.

## Definition of Done

- [x] Add explicit CLI support for config file loading (for example `--config <path.yaml>`).
- [x] Wire loaded config values into runtime resolution without breaking deterministic precedence (`CLI explicit > secure > env > config defaults`).
- [x] Keep existing command behavior unchanged when `--config` is not provided.
- [x] Add focused tests for config file happy path, missing/invalid file diagnostics, and precedence interactions with CLI overrides.
- [x] Update `README.md` usage examples and configuration documentation for CLI config-file support.

## Notes

- Keep config-file handling strict and fail fast on invalid schema/values.
- Avoid introducing implicit auto-discovery behavior unless explicitly documented and tested.
