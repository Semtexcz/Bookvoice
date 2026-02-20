---
task: TASK-005
status: "backlog"
priority: P0
type: feature
---

# Implement minimal translation and rewrite execution path

Task: TASK-005
Status: backlog
Priority: P0
Type: feature
Author:
Created: 2026-02-20
Related: TASK-001, TASK-004, TASK-006, TASK-011

## Problem

LLM stage modules are placeholders. MVP needs one practical way to obtain Czech narration text per chunk.

## Definition of Done

- [ ] Pipeline executes one translation path for each chunk.
- [ ] Rewrite-for-audio stage is executed or intentionally bypassed with explicit behavior.
- [ ] Output text artifacts are persisted for inspection.
- [ ] Stage metadata records provider/model identifiers in results.

## Notes

- Use one default provider path only.
- Skip advanced prompt versioning and multi-provider strategy for MVP.
