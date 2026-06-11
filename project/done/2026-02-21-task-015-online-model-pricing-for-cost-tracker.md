---
task: TASK-015
status: "done"
priority: P1
type: feature
---

# Fetch model pricing online for run cost calculation

Task: TASK-015
Status: done
Priority: P1
Type: feature
Author:
Created: 2026-02-21
Related: TASK-011, TASK-014

## Problem

Current run cost accounting in pipeline uses hardcoded per-character rates. This is useful for deterministic MVP reporting, but it does not reflect real model pricing changes and prevents provider-accurate cost estimates.

## Definition of Done

- [x] Introduce a pricing provider abstraction that resolves pricing by provider, model, and operation type (LLM input/output, TTS per character/token/minute).
- [x] Implement online pricing fetch path with explicit source metadata and timestamp persisted in run artifacts.
- [x] Add deterministic fallback behavior when pricing cannot be fetched (cached last-known values or configured defaults).
- [x] Manifest includes both calculated cost totals and pricing source metadata used for the run.
- [x] CLI summary includes a note whether costs are from live pricing or fallback pricing.
- [x] Tests cover fixed mocked online pricing responses and fallback path behavior.
- [x] Pricing resolution works with models selected via CLI prompts/flags or environment configuration from `TASK-014`.

## Notes

- Keep deterministic tests by mocking the online pricing fetch layer.
- Prefer explicit provider/model version identifiers in pricing keys.
- Do not block pipeline execution when pricing endpoint is unavailable.
- Ensure pricing metadata records the exact model IDs used for translation, rewrite, and TTS stages.
