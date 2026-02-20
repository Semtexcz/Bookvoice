---
task: TASK-004
status: "backlog"
priority: P0
type: feature
---

# Implement simple chapter split and chunk generation for happy path

Task: TASK-004
Status: backlog
Priority: P0
Type: feature
Author:
Created: 2026-02-20
Related: TASK-001, TASK-003, TASK-005

## Problem

Current chapter splitting and chunking are stubs and do not guarantee practical segmentation for downstream translation and TTS.

## Definition of Done

- [ ] `ChapterSplitter.split` returns deterministic chapter list for common simple input structure.
- [ ] `Chunker.to_chunks` produces bounded chunks with stable indices and offsets.
- [ ] Pipeline uses these outputs directly for translation and synthesis stages.
- [ ] Basic tests verify deterministic chunk boundaries for fixed input.

## Notes

- Heuristics can be simple; advanced chapter inference is post-MVP.
- Prioritize stable indices over linguistic perfection.
