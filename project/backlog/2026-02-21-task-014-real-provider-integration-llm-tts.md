---
task: TASK-014
status: "backlog"
priority: P1
type: feature
---

# Integrate real LLM and TTS provider APIs for production path

Task: TASK-014
Status: backlog
Priority: P1
Type: feature
Author:
Created: 2026-02-21
Related: TASK-005, TASK-006, TASK-009, TASK-011, TASK-012

## Problem

Current translation and TTS stages use deterministic local stubs. MVP flow works, but no real provider API calls are executed, so outputs are not production-grade.

## Definition of Done

- [ ] Translator stage performs real provider API calls with configurable model and language options.
- [ ] Rewriter stage performs real provider API calls or is explicitly configurable as bypass with documented behavior.
- [ ] TTS stage performs real provider API calls and writes returned audio to chunk artifacts.
- [ ] Provider API keys and required settings are loaded from configuration/environment with clear validation errors.
- [ ] Pipeline errors from provider calls surface stage-specific actionable messages in CLI.
- [ ] Tests cover one mocked happy path and one mocked provider-failure path for both LLM and TTS.

## Notes

- Keep one default provider (`openai`) for first real integration.
- Do not implement multi-provider routing in this task.
- Reuse existing resume and artifact structure.
