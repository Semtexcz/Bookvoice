---
task: TASK-014F
status: "backlog"
priority: P1
type: test
---

# Provider integration test matrix for real LLM and TTS path

Task: TASK-014F
Status: backlog
Priority: P1
Type: test
Author:
Created: 2026-02-21
Related: TASK-014, TASK-014B, TASK-014C, TASK-014D, TASK-014E

## Problem

Provider integrations need reliable tests for success and failure flows without requiring live network calls or real credentials.

## Definition of Done

- [ ] Add mocked happy-path tests for translation, rewrite, and TTS real-provider code paths.
- [ ] Add mocked provider-failure tests for translation, rewrite, and TTS with stage-specific assertions.
- [ ] Add tests for credential/model config resolution across interactive CLI, non-interactive CLI, secure storage, and env fallback.
- [ ] Ensure tests remain deterministic and offline-friendly.
- [ ] Document test strategy for provider mocks and fixture patterns.

## Notes

- Prefer adapter-level mocking over global monkeypatching where possible.
- Do not require real API keys in CI test execution.
