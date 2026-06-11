# Agent Architecture Playbook

## Purpose

Use this playbook when a task affects module boundaries, dependencies, data flow, or cross-module behavior.

Read `docs/ARCHITECTURE.md` before architecture-relevant changes.

## Boundaries

Repository layers:

- `docs/`, `product/`, and `project/` contain requirements, planning, and workflow.
- `bookvoice/` contains runtime behavior.
- `tests/` validates behavior.
- `scripts/` contains helper scripts, not primary application logic unless explicitly intended.

Preferred source layout:

- `domain/` for core logic
- `services/` for orchestration
- `adapters/` for external systems, filesystem, and APIs
- `cli.py`, `cli_runtime.py`, and `cli_rendering.py` for command-line interfaces
- `models/` for shared data structures
- `utils/` for small generic helpers

## Dependency Direction

- `domain/` must not depend on CLI or external providers.
- `services/` may coordinate domain and adapters.
- `adapters/` handle external I/O.
- CLI modules should stay thin.
- `utils/` must not become a dumping ground.

## Change Guidance

- Preserve existing patterns unless there is a clear reason to change them.
- Add abstractions only when they remove real duplication or clarify a stable boundary.
- Prefer explicit data structures over loosely shaped dictionaries at module boundaries.
- Keep architecture documentation updated when responsibilities or boundaries change.
