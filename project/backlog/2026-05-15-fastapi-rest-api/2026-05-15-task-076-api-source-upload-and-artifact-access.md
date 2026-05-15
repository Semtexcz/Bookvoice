---
task: TASK-076
status: "backlog"
priority: P1
type: feature
---

# Add source upload and artifact access endpoints

Task: TASK-076
Status: backlog
Priority: P1
Type: feature
Author:
Created: 2026-05-15
Related: TASK-073, TASK-074, TASK-075, TASK-066, TASK-068

## Problem

Remote clients need a safe way to provide source documents and retrieve
generated artifacts without relying on direct access to the server filesystem.

## Definition of Done

- [ ] Implement a documented source upload endpoint for supported input formats.
- [ ] Validate file extension, declared source format, content size, and
      readable temporary storage location before accepting a job.
- [ ] Store uploaded sources in a deterministic API-managed workspace outside
      final run artifacts.
- [ ] Connect uploaded source references to `POST /api/v1/jobs` requests.
- [ ] Implement `GET /api/v1/jobs/{job_id}/artifacts` to list available output
      artifacts after a run completes.
- [ ] Implement a download endpoint for supported generated artifacts with safe
      path resolution.
- [ ] Add tests for upload validation, artifact listing, artifact download, and
      path traversal rejection.

## Notes

- Do not expose arbitrary filesystem reads through artifact endpoints.
- Keep upload storage cleanup behavior explicit and documented.
- Support both PDF and EPUB sources if the existing source pipeline supports
      them at implementation time.
