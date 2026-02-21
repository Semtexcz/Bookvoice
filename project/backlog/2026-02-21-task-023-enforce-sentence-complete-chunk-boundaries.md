---
task: TASK-023
status: "backlog"
priority: P1
type: feature
---

# Enforce sentence-complete chunk boundaries for TTS

Task: TASK-023
Status: backlog
Priority: P1
Type: feature
Author:
Created: 2026-02-21
Related: TASK-014, TASK-021

## Problem

Chunking can end in the middle of a sentence, which reduces narration quality and creates unnatural transitions in TTS output. Chunks should end only at sentence boundaries, preferably after a period.

## Definition of Done

- [ ] Chunker no longer emits chunks ending mid-sentence.
- [ ] Preferred split boundary is after sentence-ending punctuation (`.`, `!`, `?`), with `.` as primary target.
- [ ] If no valid boundary exists near target size, chunker extends to the next sentence boundary within a bounded safety margin.
- [ ] Add deterministic fallback for pathological text (very long sentence without punctuation) with explicit marker/metadata.
- [ ] Add tests covering normal prose, abbreviations, decimal numbers, and no-punctuation edge cases.
- [ ] Update `README.md` with chunk-boundary guarantees and limitations.

## Notes

- Keep chunk sizing predictable while prioritizing sentence completeness.
- Validate that improved chunking does not regress chapter/chunk index stability.
