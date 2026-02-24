---
task: TASK-049
status: "backlog"
priority: P2
type: docs
---

# Update documentation and artifact examples for the new canonical fixture

Task: TASK-049
Status: backlog
Priority: P2
Type: docs
Author:
Created: 2026-02-24
Related: TASK-046

## Problem

Repository documentation currently references `tests/files/zero_to_one.pdf`, which should no longer be distributed or recommended.

## Definition of Done

- [ ] Update fixture references in `README.md`, `tests/README.md`, and `docs/ARTIFACTS.md` to the new canonical fixture.
- [ ] Ensure documentation explains that the fixture is synthetic and repository-owned.
- [ ] Keep examples aligned with actual integration test fixture paths.
- [ ] Verify no stale references to `zero_to_one.pdf` remain in docs.

## Notes

- Keep wording explicit about redistribution safety and deterministic test intent.
