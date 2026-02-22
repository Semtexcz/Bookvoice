---
task: TASK-032
status: "backlog"
priority: P2
type: refactor
---

# Consolidate duplicated OpenAI HTTP request and error handling

Task: TASK-032
Status: backlog
Priority: P2
Type: refactor
Author:
Created: 2026-02-22
Related: TASK-014E, TASK-012

## Problem

`bookvoice/llm/openai_client.py` duplicates request construction and exception mapping logic in `OpenAIChatClient` and `OpenAISpeechClient`. This increases maintenance cost and can cause inconsistent provider diagnostics.

## Definition of Done

- [ ] Extract shared request execution and error translation helpers in `_OpenAIBaseClient`.
- [ ] Keep chat and speech response parsing separate, but reuse transport/error plumbing.
- [ ] Preserve current `OpenAIProviderError` message patterns used by pipeline stage mapping.
- [ ] Add tests for shared transport error handling (HTTP error body decode, URL errors, timeout, empty response).

## Notes

 You can use `requests` library.
