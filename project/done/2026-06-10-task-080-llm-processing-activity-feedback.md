---
task: TASK-080
status: "done"
priority: P1
type: feature
---

# Add activity feedback during long LLM processing stages

Task: TASK-080
Status: done
Priority: P1
Type: feature
Author:
Created: 2026-06-10
Related: TASK-019

## Problem

LLM processing stages can take a significant amount of time to complete. During
this period, the CLI application does not provide enough feedback, which may
lead users to believe that it has frozen or stopped responding.

## Proposed Solution

Add a progress bar, spinner, or periodic status updates to indicate that LLM
processing is ongoing.

## Expected Benefit

Users have a better understanding of the application's current state, reducing
confusion and improving the overall user experience.

## Definition of Done

- [x] Add visible activity feedback for long-running LLM stages in CLI commands
      that invoke translation or rewrite processing.
- [x] Ensure feedback is emitted while work is still in progress, not only
      before and after a provider call.
- [x] Keep terminal output concise and readable in both interactive terminals
      and CI logs.
- [x] Avoid leaking prompts, source text, API keys, credential material, or other
      sensitive data in progress output.
- [x] Add or update tests that verify activity feedback is shown for long LLM
      processing paths.
- [x] Update user-facing documentation with the new progress behavior.

## Notes

- Build on the existing stage logging and progress behavior from `TASK-019`
  where practical.
- Prefer deterministic test hooks for long-running provider calls instead of
  real sleeps.
