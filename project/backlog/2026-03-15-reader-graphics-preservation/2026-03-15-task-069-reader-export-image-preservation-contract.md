---
task: TASK-069
status: "backlog"
priority: P1
type: feature
---

# Define image-preservation contract for reader-only translation exports

Task: TASK-069
Status: backlog
Priority: P1
Type: feature
Author:
Created: 2026-03-15
Related: TASK-062, TASK-064, TASK-065

## Problem

The current reader-export backlog assumes text-focused translation output.
Translated `EPUB` and `PDF` exports need an explicit contract for preserving
source graphics, while the audiobook translation pipeline must remain unchanged.

## Definition of Done

- [ ] Define image-preservation scope for translation-only reader exports,
      including which source graphics must be carried over and which cases are
      explicitly out of scope in the first iteration.
- [ ] Define how image preservation interacts with chapter selection, output
      naming, metadata, and deterministic replay.
- [ ] Define placement expectations for preserved graphics when exact original
      layout cannot be reproduced.
- [ ] Document that audiobook-oriented translation and TTS flows keep their
      current behavior and are not coupled to reader-export image handling.
- [ ] Update related reader-export tasks to reference this contract where
      appropriate.

## Notes

- Favor explicit, deterministic behavior over best-effort visual reconstruction.
- This task defines boundaries only; it does not implement image extraction or
  rendering.
