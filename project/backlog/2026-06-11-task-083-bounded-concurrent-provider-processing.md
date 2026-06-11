---
task: TASK-083
status: "backlog"
priority: P1
type: feature
---

# Add bounded concurrent provider processing for long books

Task: TASK-083
Status: backlog
Priority: P1
Type: feature
Author:
Created: 2026-06-11
Related: TASK-012, TASK-019, TASK-080, TASK-082

## Problem

Creating recordings for long books is slow because translation, rewrite, and
TTS provider calls are processed sequentially across many chunks. Each call is
mostly network-bound, so the CLI spends significant time waiting for provider
responses even when independent chunks could be processed concurrently.

## Proposed Solution

Add bounded concurrent execution for independent per-chunk provider calls using
`concurrent.futures.ThreadPoolExecutor`.

Run each provider stage with a configurable worker limit, for example
`max_provider_workers`, while preserving deterministic result ordering by
submitting work with stable chunk indexes and collecting results back into the
original chunk order. Keep stage boundaries explicit: complete translation
before rewrite, complete rewrite before TTS, and keep merge/manifest generation
single-threaded and deterministic.

Expose the worker limit through CLI, config file, and environment configuration.
Use a conservative default such as `1` or `2`, validate that the value is a
positive integer, and document provider rate-limit tradeoffs. Reuse the existing
retry, cache, cost tracking, progress, and resume behavior for each individual
provider call.

## Expected Benefit

Long books can finish significantly faster when provider rate limits and user
configuration allow more than one in-flight request, without replacing the
current synchronous provider implementation or adding a new HTTP dependency.

## Definition of Done

- [ ] Add a shared bounded concurrency helper for ordered per-item stage
      execution.
- [ ] Apply bounded concurrency to translation, rewrite, and TTS stages where
      each chunk or rewrite can be processed independently.
- [ ] Preserve deterministic output ordering, artifact paths, manifest content,
      and audio merge order regardless of completion order.
- [ ] Add `max_provider_workers` configuration support through CLI options,
      YAML config, and environment variables.
- [ ] Validate worker configuration and report actionable errors for invalid
      values.
- [ ] Keep the default behavior conservative enough to avoid surprising provider
      rate-limit failures.
- [ ] Ensure progress output remains readable when multiple items are in flight.
- [ ] Ensure provider errors include enough context to identify the failed
      stage and chunk while cancelling or draining remaining work predictably.
- [ ] Add tests proving that concurrent completion order does not change
      translation, rewrite, TTS, manifest, or merge ordering.
- [ ] Add tests for worker-limit parsing, invalid worker values, and provider
      error handling during concurrent execution.
- [ ] Update user-facing documentation with concurrency configuration examples
      and rate-limit guidance.

## Notes

- Prefer `ThreadPoolExecutor` over `asyncio` for this task because the current
  provider implementations are synchronous and requests-based.
- Do not parallelize merge, tagging, packaging, or manifest writing.
- Coordinate with `TASK-082` so interrupted concurrent runs can still be resumed
  from completed artifacts without replaying successful work unnecessarily.
- Avoid sharing mutable provider state across threads unless the implementation
  is explicitly safe; create per-worker clients or protect shared state if
  needed.
