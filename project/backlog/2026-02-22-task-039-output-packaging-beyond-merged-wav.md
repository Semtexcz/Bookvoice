---
task: TASK-039
status: "backlog"
priority: P3
type: feature
---

# Optional output packaging beyond merged WAV

Task: TASK-039
Status: backlog
Priority: P3
Type: feature
Author:
Created: 2026-02-22
Related: TASK-038

## Problem

Roadmap Phase 3 includes optional packaging formats beyond merged WAV. Current pipeline emits deterministic WAV artifacts only.

## Definition of Done

- [ ] Define packaging abstraction for optional output targets (for example chapter-split package, alternate container, archive bundle).
- [ ] Implement at least one non-WAV packaging option with deterministic naming and manifest metadata.
- [ ] Keep default behavior unchanged (`bookvoice_merged.wav`) when packaging is not requested.
- [ ] Add tests for packaging artifact generation and manifest references.
- [ ] Document CLI usage and output structure for packaging options.

## Notes

- Packaging should be an additive step after core synthesis/merge success.
- Avoid introducing external service dependencies for packaging.
