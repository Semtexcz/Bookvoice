---
task: TASK-047
status: "backlog"
priority: P1
type: refactor
---

# Centralize canonical PDF fixture resolution in tests

Task: TASK-047
Status: backlog
Priority: P1
Type: refactor
Author:
Created: 2026-02-24
Related: TASK-046

## Problem

Many tests hardcode fixture paths inline, making bulk fixture migration error-prone and increasing maintenance overhead.

## Definition of Done

- [ ] Add a shared pytest fixture/helper for canonical PDF fixture path resolution.
- [ ] Replace hardcoded `Path("tests/files/zero_to_one.pdf")` usage in tests with the shared helper where content fixture is required.
- [ ] Keep tests readable and avoid hidden indirection beyond fixture path resolution.
- [ ] Ensure helper naming clearly distinguishes canonical content fixture from temporary path-only test files.
- [ ] Verify `poetry run pytest` still passes after refactor.

## Notes

- Focus this task on path centralization only, not behavior changes.
