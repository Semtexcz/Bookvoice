---
task: TASK-042
status: "backlog"
priority: P2
type: feature
---

# Format-aware metadata tagging for MP3 and M4A

Task: TASK-042
Status: backlog
Priority: P2
Type: feature
Author:
Created: 2026-02-22
Related: TASK-039, TASK-041

## Problem

Current metadata tagging is WAV-focused. Delivery artifacts in MP3 or M4A need deterministic, format-aware tags so players show title/chapter context consistently.

## Definition of Done

- [ ] Define canonical metadata payload for packaged outputs (title, chapter scope/context, source/run identifier).
- [ ] Implement format-aware tag writing for MP3 (ID3) and M4A (MP4 atoms) with deterministic key mapping.
- [ ] Include chapter-level track metadata aligned with selected numbering mode (`source` or `sequential`).
- [ ] Ensure tag writes are idempotent and replay-safe in `resume` and `tts-only`.
- [ ] Persist tag-related summary metadata in manifest `extra`.
- [ ] Add tests for tag presence/values on MP3 and M4A packaged outputs.
- [ ] Document supported metadata fields and known player/format limitations.

## Notes

- Keep tag content deterministic and compact.
- Do not expose secrets in tags or manifest metadata.
- Validate behavior for both full merged packaged output and chapter-split packaged outputs.
