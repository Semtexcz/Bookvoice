---
task: TASK-029
status: "backlog"
priority: P2
type: refactor
---

# Extract CLI provider runtime resolution from command module

Task: TASK-029
Status: backlog
Priority: P2
Type: refactor
Author:
Created: 2026-02-22
Related: TASK-014B, TASK-028

## Problem

`bookvoice/cli.py` combines command wiring with provider prompting, secure credential reads/writes, and runtime source assembly. The module is large and mixes CLI presentation with runtime configuration logic, reducing testability.

## Definition of Done

- [ ] Move provider runtime source assembly and prompt flow from `bookvoice/cli.py` into a dedicated CLI support module.
- [ ] Keep Typer command signatures and flags unchanged.
- [ ] Keep secure credential behavior unchanged (`--store-api-key`, `--prompt-api-key`, `--interactive-provider-setup`).
- [ ] Add targeted tests for extracted runtime-resolution helpers without invoking full command execution.

## Notes

- This task should reduce command function size without changing command UX.
- Prefer pure helper functions for deterministic unit testing.
