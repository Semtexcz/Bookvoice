# Agent Workflow Playbook

## Purpose

This playbook describes how agents should move from request to verified change without expanding scope.

## Standard Flow

1. Understand the request and identify the smallest useful outcome.
2. Load only the context needed for that outcome.
3. Check the No-Op Rule in `AGENTS.md`.
4. Identify affected files, module boundaries, and relevant tests.
5. Make the smallest safe change.
6. Update local documentation when behavior, workflow, or architecture understanding changes.
7. Run relevant verification.
8. Report the outcome clearly.

## Backlog Tasks

Tasks live in `project/backlog/`.

When implementing a task:

- Read the task file.
- Read the related feature only if behavior changes or the task references it.
- Read `docs/TASK_SEQUENCE.md` when choosing the next task or moving task files.
- Implement only the task Scope.
- Respect Out of Scope items.
- Satisfy Done criteria.
- Move completed tasks to `project/done/` and update status to `done`.

If a task is obsolete or already complete, explain the no-op outcome instead of forcing a code change.

## Scope Control

Keep changes tightly related to the request.

Avoid:

- opportunistic refactors
- style churn
- unrelated formatting
- changing public behavior without a requirement
- broad abstractions for one narrow use case

Prefer:

- direct fixes
- local helpers
- existing project patterns
- explicit tests for changed behavior

## User Changes

The working tree may already contain user edits.

- Do not revert changes you did not make.
- If unrelated files are dirty, ignore them.
- If user edits overlap with the task, work with them.
- Ask only if the overlap makes the request unsafe or impossible.

## Completion Checklist

Before finishing:

- Scope matches the request.
- Relevant tests or checks were run, or skipped checks are explained.
- Relevant documentation was updated.
- Backlog status and task sequence were updated when task files changed.
- No unrelated files were modified.
