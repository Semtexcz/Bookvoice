---
task: TASK-014F
status: "done"
priority: P1
type: test
---

# Provider integration test matrix for real LLM and TTS path

Task: TASK-014F
Status: done
Priority: P1
Type: test
Author:
Created: 2026-02-21
Related: TASK-014, TASK-014B, TASK-014C, TASK-014D, TASK-014E

## Problem

Provider integrations need reliable tests for success and failure flows without requiring live network calls or real credentials.

## Definition of Done

- [x] Add mocked happy-path tests for translation, rewrite, and TTS real-provider code paths.
- [x] Add mocked provider-failure tests for translation, rewrite, and TTS with stage-specific assertions.
- [x] Add tests for credential/model config resolution across interactive CLI, non-interactive CLI, secure storage, and env fallback.
- [x] Ensure tests remain deterministic and offline-friendly.
- [x] Document test strategy for provider mocks and fixture patterns.

## Notes

- Prefer adapter-level mocking over global monkeypatching where possible.
- Do not require real API keys in CI test execution.
