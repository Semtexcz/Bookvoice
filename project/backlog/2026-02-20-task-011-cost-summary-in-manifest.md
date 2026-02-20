---
task: TASK-011
status: "backlog"
priority: P1
type: feature
---

# Add basic LLM and TTS cost summary to run manifest

Task: TASK-011
Status: backlog
Priority: P1
Type: feature
Author:
Created: 2026-02-20
Related: TASK-005, TASK-006, TASK-007

## Problem

`CostTracker` exists but is not integrated into a real pipeline path, so users cannot inspect per-run spend.

## Definition of Done

- [ ] Pipeline tracks LLM and TTS costs through execution.
- [ ] Manifest contains llm, tts, and total cost values.
- [ ] CLI summary prints cost totals after successful run.
- [ ] Costs are deterministic for a fixed mocked execution in tests.

## Notes

- Precise billing reconciliation is not required for MVP.
- Focus on transparent per-run estimate reporting.
