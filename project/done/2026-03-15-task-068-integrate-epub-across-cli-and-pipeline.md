---
task: TASK-068
status: "done"
priority: P1
type: feature
---

# Integrate EPUB sources across CLI and pipeline flows

Task: TASK-068
Status: done
Priority: P1
Type: feature
Author:
Created: 2026-03-15
Related: TASK-034, TASK-066, TASK-067

## Problem

Even with a generalized input contract and raw `EPUB` extraction, Bookvoice will
not be usable with ebooks until command flows and manifests handle `EPUB`
sources end to end.

## Definition of Done

- [x] Support `EPUB` sources in at least `list-chapters`, `translate-only`, and
      the main build flow where source text is required.
- [x] Persist source-format metadata and source identifiers in manifests and
      relevant artifacts without `PDF`-specific naming.
- [x] Ensure resume and replay behavior remains deterministic when the source is
      `EPUB`.
- [x] Add stage-scoped diagnostics for `EPUB`-specific validation or extraction
      failures.
- [x] Add integration tests covering at least one successful `EPUB` command flow
      and one actionable failure case.
- [x] Update user documentation to show `EPUB` as a supported input format where
      applicable.

## Notes

- Keep source-specific logic behind format-aware helpers rather than scattering
      `if .epub` checks across commands.
- Defer any format-specific rewriting heuristics unless explicitly needed.
