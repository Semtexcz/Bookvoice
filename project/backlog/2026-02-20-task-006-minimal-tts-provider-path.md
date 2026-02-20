---
task: TASK-006
status: "backlog"
priority: P0
type: feature
---

# Implement one TTS provider path for chunk synthesis

Task: TASK-006
Status: backlog
Priority: P0
Type: feature
Author:
Created: 2026-02-20
Related: TASK-001, TASK-005, TASK-007, TASK-011

## Problem

TTS interfaces are currently stubbed, so no real audio parts are generated from rewritten text.

## Definition of Done

- [ ] One concrete `TTSSynthesizer` path is implemented and wired into pipeline.
- [ ] Chunk-level audio files are generated in deterministic filenames.
- [ ] `AudioPart` metadata is populated with path and duration fields.
- [ ] Failures in synthesis surface clear errors to CLI output.

## Notes

- Focus on Czech output voice support for MVP.
- Voice profile configuration can stay minimal.
