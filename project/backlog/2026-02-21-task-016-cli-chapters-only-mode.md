---
task: TASK-016
status: "backlog"
priority: P1
type: feature
---

# Add CLI mode for chapter-only PDF split

Task: TASK-016
Status: backlog
Priority: P1
Type: feature
Author:
Created: 2026-02-21
Related: TASK-003, TASK-004, TASK-013

## Problem

Current CLI commands focus on full pipeline execution (`build`) or resume behavior. There is no direct command to only extract and split chapters from PDF input, which blocks fast validation of chapter boundary quality and outline fallback behavior.

## Definition of Done

- [ ] Add a dedicated CLI command (or explicit mode flag) that runs only extract, clean, and chapter split stages.
- [ ] Chapter-only command writes deterministic chapter artifacts (`text/chapters.json`) under run output.
- [ ] Command output includes chapter extraction source metadata (`pdf_outline` vs `text_heuristic`) and fallback reason when applicable.
- [ ] The command does not call translation, rewrite, TTS, postprocess, or merge stages.
- [ ] Tests cover one successful run and assert that downstream stage artifacts are not created.
- [ ] CLI help/README includes usage and expected outputs for the chapter-only mode.

## Notes

- Reuse existing pipeline components rather than duplicating extraction/split logic.
- Keep output schema consistent with current chapter artifact metadata from TASK-013.
- Preserve deterministic run identifiers and artifact paths.
