---
task: TASK-014
status: "done"
priority: P1
type: epic
---

# Integrate real LLM and TTS provider APIs for production path

Task: TASK-014
Status: done
Priority: P1
Type: epic
Author:
Created: 2026-02-21
Related: TASK-005, TASK-006, TASK-009, TASK-011, TASK-012, TASK-014A, TASK-014B, TASK-014C, TASK-014D, TASK-014E, TASK-014F

## Problem

Current translation and TTS stages use deterministic local stubs. MVP flow works, but no real provider API calls are executed, so outputs are not production-grade.
Current configuration assumptions also rely too heavily on environment files, which is a poor fit for many CLI users.

## Subtasks

- [x] `TASK-014A`: Provider-ready abstraction and runtime config model for LLM/TTS stages.
- [x] `TASK-014B`: CLI credential/model UX with interactive prompts and secure API key persistence.
- [x] `TASK-014C`: Real OpenAI LLM integration for translation and rewrite/bypass behavior.
- [x] `TASK-014D`: Real OpenAI TTS integration with chunk artifact audio persistence.
- [x] `TASK-014E`: Stage-specific provider error mapping and actionable CLI diagnostics.
- [x] `TASK-014F`: Integration and unit tests for mocked provider happy/failure paths and config resolution modes.

## Definition of Done

- [x] All subtasks `TASK-014A` through `TASK-014F` are completed and merged.
- [x] End-to-end `bookvoice build` uses real OpenAI provider calls in translation and TTS by default.
- [x] CLI-first credential/model flow works for users without `.env` files.
- [x] Provider-ready architecture remains extensible for additional providers without pipeline rewrites.

## Notes

- Keep `openai` as the only implemented provider in this task, but design code for future providers.
- Do not implement multi-provider runtime routing in this task.
- Reuse existing resume and artifact structure.
- Recommended initial defaults (subject to final validation during implementation):
  - Translation model: `gpt-4.1-mini`
  - Rewrite model: `gpt-4.1-mini`
  - TTS model: `gpt-4o-mini-tts`
  - TTS voice: `alloy`
