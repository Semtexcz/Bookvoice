---
task: TASK-021
status: "backlog"
priority: P1
type: feature
---

# Split audio recording parts by paragraph and text length budget

Task: TASK-021
Status: backlog
Priority: P1
Type: feature
Author:
Created: 2026-02-21
Related: TASK-014, TASK-019

## Problem

Current audio generation can produce long chapter outputs that are less practical for listening, navigation, and playback recovery. Some PDFs also contain fine-grained chapter and subchapter structure that should be reflected in produced recordings. Runtime audio-duration measurement is not required for this workflow. Instead, text should be split deterministically at paragraph boundaries using a configured character budget that approximates narration duration.

## Definition of Done

- [ ] Introduce deterministic chapter-part splitting based on a target text-length budget (characters).
- [ ] Set default chapter-part text budget to `6500` characters (approximate 7-minute narration target).
- [ ] Enforce a hard upper budget equivalent to 10 minutes of narration for a single recording part.
- [ ] Split points must prefer paragraph boundaries and must not cut a paragraph in the middle unless unavoidable.
- [ ] Preserve chapter and subchapter structure from PDF outline/text headings in emitted recordings where available.
- [ ] When a chapter exceeds the text budget, split it into sequential chapter parts.
- [ ] Allow short subchapters to be merged together when they fit in the active text budget.
- [ ] Keep chapter boundary strict: each chapter must produce its own recording output, even when very short.
- [ ] Preserve deterministic ordering and stable part numbering.
- [ ] Persist part-level metadata in artifacts (`audio/parts.json`, manifest extra metadata).
- [ ] Add tests verifying paragraph-aware splitting and stable part generation for repeated runs.
- [ ] Update `README.md` with text-budget split behavior and examples.

## Notes

- Keep merged output behavior explicit: either merged-per-part or merged-per-chapter with deterministic naming.
- Ensure split logic stays compatible with resume/rebuild flow.
- This task intentionally avoids post-generation trimming by measured audio duration.
- Use `6500` characters as the explicit baseline budget for approximately 7 minutes of narration.
- Treat the 10-minute limit as a character-budget ceiling, not a post-generated audio trimming operation.
