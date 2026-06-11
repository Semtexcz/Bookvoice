# AGENTS.md

## Purpose

This repository is designed for AI-assisted development.

Agents should optimize for:

- correctness
- minimal scope changes
- clear reasoning
- testable outcomes
- maintainability
- low future context cost

Use this file as the routing index. Load detailed playbooks only when they are relevant to the task.

## Non-Negotiable Rules

- Work only inside the requested scope.
- Do not invent requirements.
- Do not refactor unrelated code.
- Do not overwrite user changes.
- Preserve architecture boundaries.
- Prefer the smallest safe change.
- Prefer project-defined commands over ad hoc commands.
- Keep all repository content in English.
- Do not commit unless explicitly requested.
- Do not add dependencies unless they are clearly justified.

## Context Loading

Load context lazily. For every task, read:

1. the task file, if the request names or implies one
2. directly affected files
3. local README files or module docstrings near affected code, if present

Additionally read:

- `docs/ARCHITECTURE.md` for architectural, cross-module, or dependency changes
- `docs/CURRENT_STATE.md` for planning, prioritization, task creation, or project-level questions
- `docs/RISKS.md` when evaluating trade-offs, architecture, external dependencies, or production readiness
- `docs/conversations/` only when the task explicitly references a previous conversation summary
- `product/features/` for feature behavior changes
- `docs/TASK_SEQUENCE.md` when selecting, sequencing, adding, removing, or moving tasks
- `context/test-strategy.md` when adding tests or changing test strategy
- `docs/agent/workflow.md` for task execution details
- `docs/agent/testing.md` for test strategy and AI/LLM testing guidance
- `docs/agent/release.md` for version, changelog, commit, or release work
- `docs/agent/documentation.md` for documentation expectations
- `docs/agent/architecture.md` for module boundary decisions
- `docs/agent/security.md` for secrets, dependency, auth, or external I/O work
- `docs/agent/review.md` for code review tasks

Do not read every repository document by default.

## No-Op Rule

Doing nothing is a valid successful outcome.

Before changing code, check whether:

- the requested behavior already exists
- the issue is already fixed
- the task is obsolete
- the requested change belongs in documentation, tests, or backlog instead of production code

If no code change is needed, explain why and stop.

## Scope Discipline

- Implement only what the task or user request asks for.
- Keep unrelated cleanup out of the change.
- Make narrow edits in the modules that own the behavior.
- Prefer explicit code over clever or implicit behavior.
- Keep functions small and single-purpose.
- Use type hints where they improve clarity.
- Prefer mature libraries over custom infrastructure when a dependency is justified.
- Prefer the standard library when it is sufficient.

## Documentation Policy

Documentation is a context cache for future agents.

- Document public APIs, module responsibilities, architecture decisions, important flows, assumptions, limitations, integration points, and non-obvious behavior.
- Prefer local documentation near the code over forcing future agents to re-read large areas.
- Keep documentation concise and structured.
- Do not turn `AGENTS.md` into the context cache; add focused docs under `docs/`, local READMEs, ADRs, or module docstrings.

Conversation summaries are archival notes, not the source of truth.

Promote important information from `docs/conversations/` into:

- `docs/CURRENT_STATE.md` for current facts
- `docs/decisions/` for accepted decisions
- `project/backlog/` for executable tasks
- `docs/RISKS.md` for risks

Docstrings:

- Public modules, public classes, public functions, and non-obvious private helpers must have docstrings.
- Trivial private helpers do not need docstrings when names and type hints are sufficient.
- Avoid docstrings that repeat the function name.
- Prefer docstrings that explain purpose, assumptions, side effects, edge cases, or integration behavior.

See `docs/agent/documentation.md`.

## Workflow

For implementation tasks:

1. Load only the relevant context.
2. Check whether a no-op is appropriate.
3. Identify affected modules and tests.
4. Make the smallest safe change.
5. Update relevant documentation.
6. Run relevant verification.
7. Report what changed and what was verified.

Tasks are stored in `project/backlog/`.

When implementing a backlog task:

- Follow `docs/TASK_SEQUENCE.md` when task order matters.
- Read the related feature only when behavior changes.
- Implement only the task's Scope.
- Satisfy the task's Done criteria.
- After completion, update task status to `done` and move it to `project/done/`.
- If backlog task files are added, removed, renamed, or moved, keep `docs/TASK_SEQUENCE.md` consistent.

See `docs/agent/workflow.md`.

## Bug Fix Protocol

For bug fixes:

1. Reproduce the bug or identify why reproduction is not possible.
2. Add or update a failing test when practical.
3. Implement the smallest fix.
4. Verify the test now passes.
5. Run relevant regression tests.

If the bug cannot be reproduced, do not guess. Document the investigation and propose the next smallest step.

## Commands

Prefer project-defined commands in this order:

1. `justfile` commands, if present
2. `Makefile` commands, if present
3. commands documented in `README.md`
4. direct Poetry commands as fallback

Fallback examples:

```bash
poetry run pytest
poetry run ruff check .
poetry run ruff format .
poetry run mypy src
```

Repository-defined commands take precedence over these examples.

## Testing And Verification

- Add or update tests for behavior changes.
- Prefer deterministic, fast tests.
- Test behavior, not implementation details.
- Run the narrowest useful test first, then broader regression checks when risk justifies it.
- If tests cannot be run, explain why and describe the remaining risk.

See `docs/agent/testing.md`.

## Release, Changelog, And Commits

Do not commit unless explicitly requested.

When asked to commit:

- inspect the diff first
- include only related files
- use Conventional Commits
- do not commit secrets
- do not commit failing tests unless explicitly requested

Update version and `CHANGELOG.md` only for release-relevant changes.

Release-relevant means:

- user-visible behavior change
- public API change
- CLI behavior change
- dependency change that affects users
- task explicitly marked as release-relevant
- actual release preparation

Do not bump version or changelog for:

- internal refactoring without behavior change
- test-only changes
- documentation-only changes
- formatting
- temporary implementation steps

See `docs/agent/release.md`.

## Automation Boundary

Use `AGENTS.md` for guidance.

Use CI, hooks, scripts, or project commands for mandatory enforcement.

Do not rely only on agent memory for:

- formatting
- linting
- tests
- secret scanning
- version checks
- changelog validation
- generated file validation

If a rule must always be enforced, add or use automation.

## Security

- Never commit secrets.
- Avoid logging credentials, tokens, personal data, or sensitive inputs.
- Treat dependency, network, filesystem, subprocess, authentication, and external I/O changes as security-relevant.
- Validate inputs at trust boundaries.

See `docs/agent/security.md`.

## Reviews

For review tasks, prioritize:

- correctness bugs
- regressions
- security issues
- missing tests
- maintainability risks

List findings first, ordered by severity, with file and line references when possible.

See `docs/agent/review.md`.

## Final Response Requirements

Finish with:

- a concise summary of changes
- tests or verification run
- any skipped checks and why
- any remaining risks or follow-up that matters

Do not claim tests passed unless they were run.

## When In Doubt

- Ask only when a safe assumption is not possible.
- Prefer the smallest reversible step.
- Document assumptions where future agents will find them.
