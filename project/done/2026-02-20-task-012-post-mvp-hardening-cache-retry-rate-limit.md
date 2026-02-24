---
task: TASK-012
status: "done"
priority: P2
type: infra
---

# Post-MVP hardening: cache keys, retry, and rate limiting

Task: TASK-012
Status: done
Priority: P2
Type: infra
Author:
Created: 2026-02-20
Related: TASK-005, TASK-006, TASK-010, TASK-014

## Problem

Current roadmap defers robust reliability controls. Without cache/retry/rate-limiting, real provider runs may be expensive, fragile, and prone to quota bursts.

## Definition of Done

- [x] `ResponseCache` uses deterministic keys that include provider, model, operation, and normalized input identity.
- [x] External provider calls have bounded retry with backoff for transient failures and clear non-retry rules for permanent failures.
- [x] `RateLimiter` is enforced on real provider request paths (LLM + TTS).
- [x] Telemetry captures retry counts and cache hit rates.

## Notes

- This task starts only after MVP and stabilization milestones are completed.
- Keep design simple and stage-local before introducing global orchestration complexity.
- Align retry/rate limits with `TASK-014` provider client boundaries rather than embedding logic directly in pipeline orchestration.
