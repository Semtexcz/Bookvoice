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
Current configuration assumptions also rely too heavily on environment files, which is a poor fit for many CLI users.

## Definition of Done

- [ ] Add provider-ready interfaces/factories for translator, rewriter, and TTS stages so additional providers can be added later without pipeline rewrites.
- [ ] Implement first real provider integration only for `openai`; keep explicit provider identifiers in artifacts/telemetry.
- [ ] Translator stage performs real provider API calls with configurable model and target language options.
- [ ] Rewriter stage supports both real provider API calls and explicit bypass mode with documented deterministic behavior.
- [ ] TTS stage performs real provider API calls and writes returned audio bytes to chunk artifacts.
- [ ] CLI supports explicit API key and model input (interactive prompt support included) for users who do not use env files.
- [ ] API key entered via CLI is stored securely for future runs (OS keychain or equivalently secure local credential storage) and can be reused without re-entry.
- [ ] Configuration loading supports both `.env`/environment variables and CLI-provided values with deterministic precedence.
- [ ] Provider API key and model validation errors are actionable and stage-specific in CLI output.
- [ ] Pipeline errors from provider calls surface stage-specific actionable messages in CLI.
- [ ] Tests cover one mocked happy path and one mocked provider-failure path for both LLM and TTS.
- [ ] Tests cover non-interactive config path and interactive prompt path for API key/model resolution.

## Notes

- Keep `openai` as the only implemented provider in this task, but design code for future providers.
- Do not implement multi-provider runtime routing in this task.
- Reuse existing resume and artifact structure.
- Recommended initial defaults (subject to final validation during implementation):
  - Translation model: `gpt-4.1-mini`
  - Rewrite model: `gpt-4.1-mini`
  - TTS model: `gpt-4o-mini-tts`
  - TTS voice: `alloy`
