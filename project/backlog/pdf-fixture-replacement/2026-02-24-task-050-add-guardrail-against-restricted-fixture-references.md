---
task: TASK-050
status: "backlog"
priority: P3
type: chore
---

# Add a guardrail against reintroducing restricted fixture references

Task: TASK-050
Status: backlog
Priority: P3
Type: chore
Author:
Created: 2026-02-24
Related: TASK-046, TASK-049

## Problem

Without an automated check, references to removed restricted fixtures can be accidentally reintroduced in tests or documentation.

## Definition of Done

- [ ] Add a lightweight check (test, lint step, or script) that fails when `zero_to_one.pdf` is referenced in tracked project files.
- [ ] Integrate the check into existing local/CI test workflow.
- [ ] Document remediation guidance when the check fails.
- [ ] Keep the check deterministic and fast.

## Notes

- Scope should be targeted to the known restricted filename to avoid false positives.
