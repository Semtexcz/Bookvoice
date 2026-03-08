---
task: TASK-043
status: "done"
priority: P2
type: feature
---

# CLI output format controls and manifest packaging metadata

Task: TASK-043
Status: done
Priority: P2
Type: feature
Author:
Created: 2026-02-22
Related: TASK-039, TASK-041, TASK-042, TASK-040

## Problem

Users currently cannot request final audiobook packaging behavior through one cohesive CLI/config surface. Packaging settings and produced outputs must be controlled through CLI/config with clear precedence and reflected in manifest metadata.

## Definition of Done

- [x] Add explicit output-format controls (`wav`, `mp3`, `m4a`, or multi-target policy) to CLI and runtime config.
- [x] Add explicit output-language control in CLI/config (for example `--language`) so users can change target output language per run with deterministic precedence.
- [x] Add explicit encoding controls (for example bitrate/profile) with deterministic defaults.
- [x] Add explicit packaging layout controls:
  - chapter-split deliverables (one chapter per output file),
  - optional full merged packaged output alongside chapter files.
- [x] Add explicit chapter numbering mode control for packaged files/tags (`source` or `sequential`).
- [x] Add explicit naming mode control (`reader_friendly` vs `deterministic`) with clear defaults.
- [x] Integrate packaging options with existing config precedence model (`CLI > secure/env/file/default`).
- [x] Persist resolved output-language selection in manifest `extra` for replay/audit visibility.
- [x] Persist packaging intent and emitted packaged artifact paths in manifest `extra`.
- [x] Keep backward compatibility: no format flag still produces deterministic WAV output.
- [x] Define compatibility behavior for existing packaging flags (`--package-mode` values such as `none`, `aac`, `mp3`, `both`) to avoid breaking current users.
- [x] Add integration coverage for CLI/config precedence and deterministic artifact references.
- [x] Update `README.md` and `docs/ARTIFACTS.md` with usage examples and compatibility notes.

## Notes

- Reuse conventions established by `TASK-040` for config loading and precedence.
- Language-proficiency (`A0`-`C2`) behavior is owned by `TASK-044` and should remain out of scope here.
- Keep surface minimal; avoid introducing ambiguous aliases for format values.
