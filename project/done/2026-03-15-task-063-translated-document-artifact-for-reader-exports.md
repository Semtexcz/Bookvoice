---
task: TASK-063
status: "done"
priority: P1
type: feature
---

# Add translated document artifact for reader exports

Task: TASK-063
Status: done
Priority: P1
Type: feature
Author:
Created: 2026-03-15
Related: TASK-062, TASK-034, TASK-037

## Problem

Current translation artifacts are stage-oriented and optimized for the audiobook
pipeline. Reader exports need a deterministic, structured representation of the
translated book that can be reused by multiple non-audio exporters.

## Definition of Done

- [x] Introduce a canonical translated-document model covering ordered chapters,
      titles, body content, and relevant metadata needed by reader exporters.
- [x] Persist the model as a deterministic artifact that can be replayed without
      rerunning translation.
- [x] Include source-format, target-language, and chapter-selection metadata
      needed for auditability and resume behavior.
- [x] Ensure artifact serialization and deserialization are stable and validated
      with automated tests.
- [x] Wire the artifact into the chosen reader-export flow without changing
      existing audiobook output behavior.

## Notes

- Keep the model exporter-friendly and independent of any one file format.
- Avoid coupling this artifact to audio packaging metadata.
