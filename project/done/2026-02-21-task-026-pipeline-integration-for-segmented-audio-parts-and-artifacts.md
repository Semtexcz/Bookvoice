---
task: TASK-026
status: "done"
priority: P1
type: feature
---

# Integrate segmented part planning into pipeline artifacts and resume flow

Task: TASK-026
Status: done
Priority: P1
Type: feature
Author:
Created: 2026-02-21
Related: TASK-021, TASK-022, TASK-024, TASK-025

## Problem

After structure extraction and segment planning exist, pipeline orchestration must consume them consistently across build, artifacts, and resume behavior.

## Definition of Done

- [x] Integrate segment plan into pipeline execution before TTS generation.
- [x] Ensure emitted artifacts (`audio/parts.json`, manifest metadata) include chapter/part mapping and source structure references.
- [x] Preserve deterministic part ordering and stable identifiers across rebuild/resume.
- [x] Keep compatibility with naming convention requirements from `TASK-022`.
- [x] Add integration tests for build and resume flows with segmented chapter outputs.
- [x] Update `README.md` with operational examples and artifact expectations.

## Notes

- This task should not redefine planning rules from `TASK-025`; it should only integrate and persist them.
