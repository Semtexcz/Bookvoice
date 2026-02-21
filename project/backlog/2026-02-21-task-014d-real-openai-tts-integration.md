---
task: TASK-014D
status: "backlog"
priority: P1
type: feature
---

# Real OpenAI TTS integration for chunk synthesis

Task: TASK-014D
Status: backlog
Priority: P1
Type: feature
Author:
Created: 2026-02-21
Related: TASK-014, TASK-014A, TASK-014B

## Problem

Current TTS implementation creates deterministic local WAV output instead of using real provider-generated speech.

## Definition of Done

- [ ] Implement real OpenAI TTS API calls for each rewrite chunk.
- [ ] Write returned audio bytes to deterministic chunk artifact paths currently used by pipeline.
- [ ] Preserve chapter/chunk identity and deterministic ordering in synthesized outputs.
- [ ] Persist provider/model/voice metadata in audio artifacts.
- [ ] Map provider failures to stage-specific `tts` errors with actionable hints.
- [ ] Add mocked tests for one happy path and one provider-failure path.

## Notes

- Recommended default TTS model: `gpt-4o-mini-tts`.
- Recommended default voice: `alloy`.
