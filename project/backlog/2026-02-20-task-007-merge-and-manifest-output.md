---
task: TASK-007
status: "backlog"
priority: P0
type: feature
---

# Implement audio merge and minimal manifest writing

Task: TASK-007
Status: backlog
Priority: P0
Type: feature
Author:
Created: 2026-02-20
Related: TASK-001, TASK-002, TASK-006

## Problem

Pipeline does not yet produce a final merged audiobook artifact and manifest persisted to disk.

## Definition of Done

- [ ] `AudioMerger.merge` creates one final playable output from ordered audio parts.
- [ ] Manifest is written to disk and includes config hash, run id, and output paths.
- [ ] CLI prints final output path and manifest path on successful build.
- [ ] Ordering is deterministic for identical chunk inputs.

## Notes

- Advanced mastering and ID3 tagging are not required for MVP.
- Prefer straightforward merge behavior over feature-rich options.
