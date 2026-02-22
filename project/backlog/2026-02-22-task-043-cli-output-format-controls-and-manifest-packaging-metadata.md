---
task: TASK-043
status: "backlog"
priority: P2
type: feature
---

# CLI output format controls and manifest packaging metadata

Task: TASK-043
Status: backlog
Priority: P2
Type: feature
Author:
Created: 2026-02-22
Related: TASK-039, TASK-041, TASK-042, TASK-040

## Problem

Users currently cannot request final audiobook format explicitly. Packaging settings and produced outputs must be controlled through CLI/config with clear precedence and reflected in manifest metadata.

## Definition of Done

- [ ] Add explicit output-format controls (`wav`, `mp3`, `m4a`, or multi-target policy) to CLI and runtime config.
- [ ] Add explicit encoding controls (for example bitrate/profile) with deterministic defaults.
- [ ] Add explicit packaging layout controls:
  - chapter-split deliverables (one chapter per output file),
  - optional full merged packaged output alongside chapter files.
- [ ] Add explicit chapter numbering mode control for packaged files/tags (`source` or `sequential`).
- [ ] Add explicit naming mode control (`reader_friendly` vs `deterministic`) with clear defaults.
- [ ] Integrate packaging options with existing config precedence model (`CLI > secure/env/file/default`).
- [ ] Persist packaging intent and emitted packaged artifact paths in manifest `extra`.
- [ ] Keep backward compatibility: no format flag still produces deterministic WAV output.
- [ ] Add integration coverage for CLI/config precedence and deterministic artifact references.
- [ ] Update `README.md` and `docs/ARTIFACTS.md` with usage examples and compatibility notes.

## Notes

- Reuse conventions established by `TASK-040` for config loading and precedence.
- Keep surface minimal; avoid introducing ambiguous aliases for format values.
