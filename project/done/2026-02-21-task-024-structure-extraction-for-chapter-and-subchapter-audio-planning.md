---
task: TASK-024
status: "done"
priority: P1
type: feature
---

# Extract and normalize chapter/subchapter structure for audio planning

Task: TASK-024
Status: done
Priority: P1
Type: feature
Author:
Created: 2026-02-21
Related: TASK-021, TASK-014

## Problem

Books with finer chapter/subchapter hierarchy need structure-aware audio planning. Current flow does not expose a normalized structure model suitable for deterministic part planning.

## Definition of Done

- [x] Define a normalized structure model for `chapter` and optional `subchapter` units used by downstream planning.
- [x] Prefer PDF outline hierarchy when available; fall back to heading detection from extracted text.
- [x] Persist normalized structure metadata in artifacts with deterministic ordering.
- [x] Keep chapter boundaries explicit and stable across repeated runs.
- [x] Add tests for outline-first behavior, fallback behavior, and ordering stability.

## Notes

- This task should not implement budget splitting logic.
- The output of this task becomes input for `TASK-025`.
