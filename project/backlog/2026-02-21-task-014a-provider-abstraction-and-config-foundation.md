---
task: TASK-014A
status: "backlog"
priority: P1
type: feature
---

# Provider abstraction and config foundation for real integrations

Task: TASK-014A
Status: backlog
Priority: P1
Type: feature
Author:
Created: 2026-02-21
Related: TASK-014, TASK-012, TASK-015

## Problem

Current pipeline wiring instantiates concrete stubs directly in orchestration code. This blocks clean real-provider integration and makes future provider additions expensive.

## Definition of Done

- [ ] Introduce provider-ready interfaces/factories for translator, rewriter, and TTS synthesizer creation.
- [ ] Add runtime config fields for provider IDs and model settings (translate, rewrite, TTS model, TTS voice).
- [ ] Keep one active implemented provider (`openai`) while preserving extension points for future providers.
- [ ] Define deterministic config precedence contract to support CLI values, secure stored credentials, and env fallback.
- [ ] Persist provider/model identifiers used in run artifacts and manifest metadata.
- [ ] Add tests covering provider factory resolution and config validation paths.

## Notes

- Do not add multi-provider runtime routing logic in this task.
- Keep orchestration changes minimal and avoid broad pipeline rewrites.
