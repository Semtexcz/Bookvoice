---
task: TASK-044
status: "backlog"
priority: P2
type: feature
---

# Language proficiency level control for learning-friendly output

Task: TASK-044
Status: backlog
Priority: P2
Type: feature
Author:
Created: 2026-02-22
Related: TASK-014, TASK-034, TASK-040, TASK-043

## Problem

Users learning a language need explicit control over output complexity. Current translation/rewrite behavior does not expose a deterministic proficiency-level target (`A0` to `C2`) for generated text and spoken output.

## Definition of Done

- [ ] Add explicit CLI/config option for target language proficiency level (`A0`, `A1`, `A2`, `B1`, `B2`, `C1`, `C2`).
- [ ] Integrate level selection into translation/rewrite prompt policy with deterministic fallback when omitted.
- [ ] Validate and normalize accepted values case-insensitively (`a2` -> `A2`) with clear diagnostics for invalid values.
- [ ] Persist resolved proficiency level in run manifest `extra` and stage artifacts metadata where relevant.
- [ ] Ensure `build`, `resume`, and `tts-only` replay preserve level metadata deterministically.
- [ ] Add tests for CLI/config precedence, validation errors, and metadata persistence.
- [ ] Update `README.md` with usage examples for simplified-learning outputs.

## Notes

- Keep this feature orthogonal to packaging format controls in `TASK-043`.
- Avoid ambiguous aliases; supported levels should match CEFR labels exactly.
- Default behavior must remain backward compatible when no level is provided.
