---
task: TASK-066
status: "done"
priority: P1
type: refactor
---

# Generalize source document input contract beyond PDF

Task: TASK-066
Status: done
Priority: P1
Type: refactor
Author:
Created: 2026-03-15
Related: TASK-040, TASK-062

## Problem

The current CLI, config model, environment variables, and manifest naming assume
`input_pdf` as the only source type. That blocks clean support for `EPUB`
without either user-facing inconsistency or duplicated code paths.

## Definition of Done

- [x] Define a source-document abstraction that supports at least `PDF` and
      `EPUB`.
- [x] Rename or extend user-facing config/manifest fields so they are format
      neutral while preserving a backward-compatible path for existing `PDF`
      usage.
- [x] Define source-format detection and validation behavior, including
      actionable diagnostics for unsupported extensions.
- [x] Update command help, config loading, and manifest metadata to use the new
      source-document contract consistently.
- [x] Add automated tests for backward compatibility and source-format
      resolution.

## Notes

- Backward compatibility for existing `input_pdf` users matters.
- This task should not implement `EPUB` parsing itself; it only establishes the
      shared contract.
