---
task: TASK-033
status: "backlog"
priority: P2
type: refactor
---

# Standardize provider HTTP transport on requests

Task: TASK-033
Status: backlog
Priority: P2
Type: refactor
Author:
Created: 2026-02-22
Related: TASK-032, TASK-014E, TASK-012

## Problem

`bookvoice/llm/openai_client.py` currently uses `urllib` directly for HTTP calls. This increases transport boilerplate and makes future reliability features (timeouts, retries, clearer exception mapping) harder to maintain consistently.

## Definition of Done

- [ ] Replace `urllib` transport usage in `bookvoice/llm/openai_client.py` with `requests` while preserving current public client APIs.
- [ ] Keep current OpenAI endpoint behavior for chat completions and speech synthesis.
- [ ] Preserve stage-facing `OpenAIProviderError` semantics and actionable diagnostics.
- [ ] Add/adjust tests for mapped transport failures (`HTTP` errors, timeouts, connection errors, malformed/empty payloads).
- [ ] Add `requests` as an explicit project dependency and keep lockfile synchronized.

## Notes

- Keep this refactor incremental and behavior-preserving.
- Do not introduce async HTTP or additional networking frameworks in this task.
