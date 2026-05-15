---
task: TASK-073
status: "backlog"
priority: P1
type: feature
---

# Add FastAPI application foundation

Task: TASK-073
Status: backlog
Priority: P1
Type: feature
Author:
Created: 2026-05-15
Related: TASK-014, TASK-036, TASK-040

## Problem

Bookvoice is currently exposed primarily through the CLI. A REST API needs a
small, explicit FastAPI application foundation before command flows can be
called safely from HTTP clients.

## Definition of Done

- [ ] Add FastAPI and an ASGI server dependency through the project dependency
      model with a clear justification.
- [ ] Introduce a `bookvoice.api` package with a documented application factory.
- [ ] Expose a versioned API root, such as `/api/v1`, without changing existing
      CLI behavior.
- [ ] Add `/health` and `/api/v1/version` endpoints returning deterministic JSON.
- [ ] Configure OpenAPI metadata with project name, version, and a concise API
      description.
- [ ] Add unit tests for the application factory and basic endpoints.
- [ ] Document how to run the local API server for development.

## Notes

- Keep the API package independent from Typer command wiring.
- Reuse `bookvoice.__version__` as the single version source.
- Prefer a narrow application factory over a module-level server singleton so
      tests can create isolated app instances.
