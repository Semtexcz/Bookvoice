---
task: TASK-062
status: "backlog"
priority: P1
type: feature
---

# Define translator-only reader export command contract

Task: TASK-062
Status: backlog
Priority: P1
Type: feature
Author:
Created: 2026-03-15
Related: TASK-034, TASK-040, TASK-043

## Problem

Bookvoice can already stop after translation via `translate-only`, but that flow
only persists intermediate artifacts. There is no explicit product contract for
using Bookvoice as a translator-only tool that returns reader-ready `EPUB` and
`PDF` outputs.

## Definition of Done

- [ ] Define whether reader export extends `translate-only` or introduces a
      dedicated command, and document the rationale.
- [ ] Define CLI/config options for requested reader output formats with initial
      support for `epub`, `pdf`, and `epub,pdf`.
- [ ] Define how reader export interacts with rewrite behavior, chapter
      selection, output naming, and output directory layout.
- [ ] Define manifest metadata and artifact naming required for deterministic
      replay and auditing of reader exports.
- [ ] Document backward-compatibility expectations for existing
      `translate-only` users.

## Notes

- Keep scope focused on user-facing contract and pipeline boundaries, not file
  writer internals.
- Reader-export semantics should remain deterministic and resumable.
