---
task: TASK-031
status: "backlog"
priority: P1
type: refactor
---

# Split resume flow into stage-specific helpers with explicit state

Task: TASK-031
Status: backlog
Priority: P1
Type: refactor
Author:
Created: 2026-02-22
Related: TASK-027, TASK-028

## Problem

`BookvoicePipeline.resume` in `bookvoice/pipeline/orchestrator.py` is long and condition-heavy. Artifact loading, stage replay decisions, metadata recovery, and manifest writing are tightly coupled in one method, which increases regression risk and makes focused testing difficult.

## Definition of Done

- [ ] Introduce a typed resume state/context object that holds resolved paths, loaded artifacts, chapter scope, and runtime config.
- [ ] Break `resume` into stage-specific private helpers (for example: load-or-extract text, load-or-split chapters, load-or-chunk, load-or-translate, load-or-rewrite, load-or-tts, load-or-merge).
- [ ] Preserve existing resume behavior, artifact paths, and manifest metadata keys.
- [ ] Add targeted tests for at least three resume branches: full reuse, partial replay from `translate`, and replay when audio files are missing.

## Notes

- Keep refactor incremental; avoid redesigning run-stage orchestration in this task.
- Prioritize deterministic behavior parity over abstraction depth.
