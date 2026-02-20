---
task: TASK-001
status: "done"
priority: P0
type: feature
---

# MVP thin vertical slice: text PDF to playable audiobook

Task: TASK-001
Status: done
Priority: P0
Type: feature
Author:
Created: 2026-02-20
Related: TASK-002, TASK-003, TASK-004, TASK-005, TASK-006, TASK-007

## Problem

The repository currently provides a scaffold only. There is no end-to-end happy path that takes a text-based PDF and produces a playable audiobook file.

## Definition of Done

- [x] `bookvoice build input.pdf --out out/` executes a real thin pipeline for text PDFs.
- [x] The command creates a merged playable audio output file in `out/`.
- [x] Intermediate artifacts are stored so output can be inspected manually.
- [x] A minimal `RunManifest` is written and references key artifacts.

## Notes

- Optimize for fastest delivery of the happy path.
- Ignore edge cases and advanced robustness in this task.
- Keep implementation narrow and explicit to avoid over-abstraction.
