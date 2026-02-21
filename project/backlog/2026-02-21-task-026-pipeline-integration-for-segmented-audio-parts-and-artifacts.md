---
task: TASK-026
status: "backlog"
priority: P1
type: feature
---

# Integrate segmented part planning into pipeline artifacts and resume flow

Task: TASK-026
Status: backlog
Priority: P1
Type: feature
Author:
Created: 2026-02-21
Related: TASK-021, TASK-022, TASK-024, TASK-025

## Problem

After structure extraction and segment planning exist, pipeline orchestration must consume them consistently across build, artifacts, and resume behavior.

## Definition of Done

- [ ] Integrate segment plan into pipeline execution before TTS generation.
- [ ] Ensure emitted artifacts (`audio/parts.json`, manifest metadata) include chapter/part mapping and source structure references.
- [ ] Preserve deterministic part ordering and stable identifiers across rebuild/resume.
- [ ] Keep compatibility with naming convention requirements from `TASK-022`.
- [ ] Add integration tests for build and resume flows with segmented chapter outputs.
- [ ] Update `README.md` with operational examples and artifact expectations.

## Notes

- This task should not redefine planning rules from `TASK-025`; it should only integrate and persist them.
