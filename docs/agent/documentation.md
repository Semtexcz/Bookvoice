# Agent Documentation Playbook

## Purpose

Documentation should reduce future repository scanning and make important behavior easy to recover.

## What To Document

Document:

- public APIs
- module responsibilities
- architecture boundaries
- important data flows
- assumptions and limitations
- integration points
- non-obvious implementation details
- operational or workflow steps that future agents must repeat

## Where To Document

Prefer the smallest durable location:

- module docstrings for module responsibilities
- public API docstrings for interface behavior
- local README files for complex directories
- `docs/` for cross-cutting behavior
- ADRs for architecture decisions
- task or feature files for product planning context

Do not use `AGENTS.md` as a large memory dump. Keep it as a routing file.

## Docstrings

Public modules, public classes, public functions, and non-obvious private helpers must have docstrings.

Docstrings are not required for trivial private helpers when the name and type hints are sufficient.

Good docstrings explain:

- purpose
- assumptions
- side effects
- edge cases
- integration behavior

Avoid docstrings that merely repeat the symbol name.

## Style

- Keep documentation concise.
- Prefer examples only when they reduce future reasoning cost.
- Keep docs in English.
- Update docs in the same change as behavior changes.
- Remove or update obsolete documentation instead of adding contradictory notes.
