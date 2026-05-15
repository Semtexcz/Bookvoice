---
task: TASK-075
status: "backlog"
priority: P1
type: feature
---

# Add API job orchestration and status tracking

Task: TASK-075
Status: backlog
Priority: P1
Type: feature
Author:
Created: 2026-05-15
Related: TASK-073, TASK-074, TASK-019, TASK-037

## Problem

Bookvoice builds can take a long time. The REST API must not block HTTP
requests for the full pipeline duration and needs a deterministic way to track
submitted jobs and expose stage progress.

## Definition of Done

- [ ] Add an API job model with stable job IDs, lifecycle states, timestamps,
      and terminal result metadata.
- [ ] Implement `POST /api/v1/jobs` to submit a build request and return `202
      Accepted` with a job resource.
- [ ] Implement `GET /api/v1/jobs/{job_id}` to return current job status,
      current stage, progress events, and terminal errors when present.
- [ ] Run pipeline work outside the request-response path using a simple
      in-process worker abstraction suitable for the first API version.
- [ ] Normalize `PipelineStageError` and unexpected failures into documented API
      error payloads.
- [ ] Preserve deterministic run directory and manifest behavior from the
      existing pipeline.
- [ ] Add tests covering accepted jobs, successful completion, failed jobs, and
      unknown job IDs.

## Notes

- Keep the first implementation local and explicit; distributed queues can be a
      later task if needed.
- Design the worker boundary so a future queue adapter can replace it without
      changing endpoint contracts.
- Do not make API progress reporting depend on terminal-oriented CLI rendering.
