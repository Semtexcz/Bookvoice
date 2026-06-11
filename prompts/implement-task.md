# Implement A Backlog Task

Use this prompt when asking an AI coding agent to implement a scoped task from `project/backlog/`.

```text
Implement the task in project/backlog/<task-file>.md.

Before editing, read:

- AGENTS.md
- docs/ARCHITECTURE.md
- docs/TASK_SEQUENCE.md
- project/backlog/README.md
- the related feature or PRD, if the task references one

Follow the task Scope and Done criteria exactly.
Make the smallest safe change, update relevant docs, bump the version, update `CHANGELOG.md`, create the required commit, run the narrowest useful verification, and report:

- what changed
- what was verified
- skipped checks and why
- remaining risks or follow-up
```
