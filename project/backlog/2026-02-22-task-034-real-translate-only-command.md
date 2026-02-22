---
task: TASK-034
status: "backlog"
priority: P1
type: feature
---

# Real `translate-only` command execution path

Task: TASK-034
Status: backlog
Priority: P1
Type: feature
Author:
Created: 2026-02-22
Related: TASK-014, TASK-016, TASK-018, TASK-030

## Problem

The CLI command `bookvoice translate-only` currently calls the full `build` path and prints stub output lines. This prevents deterministic partial-pipeline usage and blocks roadmap milestone `v0.2.0` command completeness.

## Definition of Done

- [ ] Implement an explicit `translate-only` execution path that runs stages through `translate` and writes deterministic artifacts (`raw`, `clean`, `chapters`, `chunks`, `translations`) plus manifest metadata.
- [ ] Ensure `translate-only` does not execute `rewrite`, `tts`, or `merge` stages.
- [ ] Preserve chapter selection support (`--chapters`) and provider/model/runtime precedence behavior used by `build`.
- [ ] Expose concise CLI output with stage-aware diagnostics consistent with existing `build`/`resume` error rendering.
- [ ] Add integration coverage proving expected artifacts are written and downstream audio artifacts are not produced.
- [ ] Update `README.md` and architecture docs to remove placeholder wording for `translate-only`.

## Notes

- Keep stage orchestration logic shared with existing pipeline internals; avoid duplicating stage implementations.
- Ensure manifest fields make `tts-only` continuation straightforward.
