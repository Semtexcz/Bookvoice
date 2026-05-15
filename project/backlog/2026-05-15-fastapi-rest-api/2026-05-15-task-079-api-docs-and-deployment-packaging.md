---
task: TASK-079
status: "backlog"
priority: P2
type: feature
---

# Document and package the REST API server

Task: TASK-079
Status: backlog
Priority: P2
Type: feature
Author:
Created: 2026-05-15
Related: TASK-073, TASK-075, TASK-076, TASK-078

## Problem

After the REST API exists, users need clear documentation and packaging entry
points for running it consistently in development and deployment environments.

## Definition of Done

- [ ] Add user documentation for starting the API server locally.
- [ ] Add API examples for health checks, uploads, job submission, status
      polling, chapter discovery, and artifact download.
- [ ] Add a project script or documented command for serving the FastAPI app via
      the selected ASGI server.
- [ ] Update architecture and module documentation to describe the API package,
      endpoint responsibilities, and job execution boundary.
- [ ] Document operational constraints, including local filesystem storage,
      long-running jobs, provider credentials, upload limits, and cleanup.
- [ ] Add a smoke test or integration test proving the documented server entry
      point imports successfully.
- [ ] Ensure changelog and versioning are updated when this task is implemented.

## Notes

- Keep documentation focused on the actual implemented API behavior.
- Include examples that can run against a local development server.
- Do not document production hardening that is not implemented yet.
