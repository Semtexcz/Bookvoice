---
task: TASK-037
status: "backlog"
priority: P1
type: infra
---

# Resume artifact consistency hardening for partial runs

Task: TASK-037
Status: backlog
Priority: P1
Type: infra
Author:
Created: 2026-02-22
Related: TASK-012, TASK-031

## Problem

Resume already detects missing stage artifacts, but validation for partially inconsistent artifact sets is limited. Mixed stale/missing artifacts can currently produce confusing replay behavior and weaker diagnostics.

## Definition of Done

- [ ] Add explicit cross-artifact consistency checks for resume-critical sets (chapters/chunks/translations/rewrites/audio parts) before stage replay begins.
- [ ] Distinguish recoverable resume states (safe downstream replay) from non-recoverable states (manual cleanup required).
- [ ] Emit actionable stage diagnostics with concrete artifact paths and recommended remediation.
- [ ] Add integration tests covering inconsistent artifact combinations and expected recovery/failure behavior.
- [ ] Persist lightweight resume validation metadata in manifest `extra` for debugging.

## Notes

- This complements `TASK-012` retry/reliability work; it should not duplicate provider transport concerns.
- Prefer deterministic validation rules over heuristic auto-repair.
