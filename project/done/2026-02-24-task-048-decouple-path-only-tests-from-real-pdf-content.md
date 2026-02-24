---
task: TASK-048
status: "done"
priority: P2
type: test
---

# Decouple path-only tests from real PDF fixture content

Task: TASK-048
Status: done
Priority: P2
Type: test
Author:
Created: 2026-02-24
Related: TASK-046, TASK-047

## Problem

Some tests may only validate configuration/path propagation but still reference the canonical PDF fixture. This increases unnecessary coupling and makes fixture updates harder.

## Definition of Done

- [x] Audit tests currently referencing the canonical fixture and classify each test as path-only or content-dependent.
- [x] Update path-only tests to use synthetic temporary files or path literals without canonical fixture dependency.
- [x] Keep content-dependent tests bound to canonical fixture helper introduced in `TASK-047`.
- [x] Maintain or improve test determinism and runtime.
- [x] Ensure `poetry run pytest` passes with the reduced fixture coupling.

## Notes

- Do not reduce coverage; only reduce unnecessary fixture dependence.
