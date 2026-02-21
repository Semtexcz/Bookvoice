---
task: TASK-014C
status: "backlog"
priority: P1
type: feature
---

# Real OpenAI LLM integration for translation and rewrite stages

Task: TASK-014C
Status: backlog
Priority: P1
Type: feature
Author:
Created: 2026-02-21
Related: TASK-014, TASK-014A, TASK-014B

## Problem

Translation and rewrite currently use deterministic local stubs, so text output is not generated via real provider APIs.

## Definition of Done

- [ ] Implement real OpenAI-backed translation provider call with configurable model and target language.
- [ ] Implement real OpenAI-backed rewrite provider call with configurable model.
- [ ] Support explicit rewrite bypass mode with documented deterministic behavior.
- [ ] Persist provider and model metadata in translation and rewrite artifacts.
- [ ] Map provider failures to stage-specific errors with actionable hints.
- [ ] Add mocked tests for one happy path and one provider-failure path for both translation and rewrite.

## Notes

- Recommended default model for translation: `gpt-4.1-mini`.
- Recommended default model for rewrite: `gpt-4.1-mini`.
