---
task: TASK-027
status: "backlog"
priority: P2
type: refactor
---

# Deduplicate translation and rewrite artifact payload builders

Task: TASK-027
Status: backlog
Priority: P2
Type: refactor
Author:
Created: 2026-02-22
Related: TASK-026, TASK-014F

## Problem

`bookvoice/pipeline/orchestrator.py` builds translation and rewrite artifact JSON payloads inline in both `run` and `resume`. The structures are duplicated, easy to drift, and hard to test independently.

## Definition of Done

- [ ] Introduce shared payload builder helpers in `bookvoice/pipeline/artifacts.py` for translation and rewrite artifact bodies.
- [ ] Replace duplicated inline payload construction in `bookvoice/pipeline/orchestrator.py` with those helpers.
- [ ] Preserve output schema and field names in `text/translations.json` and `text/rewrites.json`.
- [ ] Add/adjust unit tests that assert identical payload shape for full run and resume paths.

## Notes

- Keep this change behavior-preserving; only move serialization responsibility.
- Do not change manifest fields in this task.
