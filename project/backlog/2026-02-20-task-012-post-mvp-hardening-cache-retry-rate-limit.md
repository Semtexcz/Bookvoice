---
task: TASK-012
status: "backlog"
priority: P2
type: infra
---

# Post-MVP hardening: cache keys, retry, and rate limiting

Task: TASK-012
Status: backlog
Priority: P2
Type: infra
Author:
Created: 2026-02-20
Related: TASK-005, TASK-006, TASK-010

## Problem

Current roadmap defers robust reliability controls. Without cache/retry/rate-limiting, production-like runs may be expensive and fragile.

## Definition of Done

- [ ] `ResponseCache` uses deterministic keys and persists reusable responses.
- [ ] External calls have bounded retry with backoff for transient failures.
- [ ] `RateLimiter` is enforced on provider request paths.
- [ ] Telemetry captures retry counts and cache hit rates.

## Notes

- This task starts only after MVP and stabilization milestones are completed.
- Keep design simple and stage-local before introducing global orchestration complexity.
