---
task: TASK-014D
status: "done"
priority: P1
type: feature
---

# Real OpenAI TTS integration for chunk synthesis

Task: TASK-014D
Status: done
Priority: P1
Type: feature
Author:
Created: 2026-02-21
Related: TASK-014, TASK-014A, TASK-014B

## Problem

Current TTS implementation creates deterministic local WAV output instead of using real provider-generated speech.

## Definition of Done

- [x] Implement real OpenAI TTS API calls for each rewrite chunk.
- [x] Write returned audio bytes to deterministic chunk artifact paths currently used by pipeline.
- [x] Preserve chapter/chunk identity and deterministic ordering in synthesized outputs.
- [x] Persist provider/model/voice metadata in audio artifacts.
- [x] Map provider failures to stage-specific `tts` errors with actionable hints.
- [x] Add mocked tests for one happy path and one provider-failure path.

## Notes

- Recommended default TTS model: `gpt-4o-mini-tts`.
- Recommended default voice: `alloy`.
