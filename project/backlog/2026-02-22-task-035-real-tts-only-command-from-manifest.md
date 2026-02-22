---
task: TASK-035
status: "backlog"
priority: P1
type: feature
---

# Real `tts-only` command execution from manifest artifacts

Task: TASK-035
Status: backlog
Priority: P1
Type: feature
Author:
Created: 2026-02-22
Related: TASK-014D, TASK-018, TASK-031, TASK-034

## Problem

The CLI command `bookvoice tts-only` is currently a stub line and does not synthesize audio from existing text artifacts. This blocks partial reruns for TTS/merge-only workflows and roadmap milestone `v0.2.0`.

## Definition of Done

- [ ] Implement `bookvoice tts-only <manifest.json>` to load manifest/artifacts and execute only `tts`, `merge`, and manifest write stages.
- [ ] Validate prerequisites (`rewrites` artifact, chunk metadata, runtime provider/model/voice settings) with actionable stage errors.
- [ ] Reuse deterministic output naming and artifact schemas from full `build`/`resume` flows.
- [ ] Avoid re-running upstream stages (`extract` through `rewrite`) when valid artifacts already exist.
- [ ] Add integration coverage for successful TTS-only replay and for missing/corrupted prerequisite artifact failures.
- [ ] Update CLI/docs examples to include real `tts-only` usage.

## Notes

- The command should behave as a constrained resume mode, but with explicit stage start and clear guardrails.
- Keep command UX deterministic and aligned with existing progress indicator semantics.
