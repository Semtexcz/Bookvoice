# Project Workflow Playbook

## Purpose

This document explains how Bookvoice turns product ideas into scoped,
testable implementation work.

Use it as a practical guide. Small maintenance changes may only need a task
card and tests; larger behavior changes should also update product and design
documentation.

## Default Flow

The recommended path is:

1. capture high-level intent in `docs/VISION.MD`
2. describe product requirements in `product/prds/` when scope needs alignment
3. split requirements into feature documents under `product/features/`
4. add user stories only when user behavior or acceptance logic needs clarity
5. create implementation tasks in `project/backlog/`
6. keep execution order visible in `docs/TASK_SEQUENCE.md`
7. implement from a concrete task or explicit user request
8. validate with `poetry run pytest`
9. update version, changelog, and commits according to `AGENTS.md`

## Planning Artifacts

- `docs/VISION.MD` defines product direction, users, value, and non-goals.
- `product/prds/` contains product requirements for larger workstreams.
- `product/features/` describes deliverable capabilities and success criteria.
- `product/user-stories/` is optional and should clarify user behavior.
- `project/backlog/` contains executable tasks.
- `docs/TASK_SEQUENCE.md` records task order and dependencies.
- `docs/decisions/` stores ADRs for durable architecture decisions.

## Agent Workflow

Agents must follow the repository-level `AGENTS.md`. That file is the
authoritative rule set for language, docstrings, testing, versioning,
changelog updates, and automatic commits.

The focused playbooks in `docs/agent/` provide additional context for
workflow, testing, documentation, release, architecture, security, and review
tasks.

## Template Updates

This repository is linked to `Semtexcz/_ai_python_project_template` through
`.copier-answers.yml`. To pull future template changes, run:

```bash
copier update
```

Review generated diffs carefully before committing. Keep Bookvoice-specific
application layout and the local `AGENTS.md` rules unless a template update is
intentionally adopted.
