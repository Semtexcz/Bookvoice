---
task: TASK-078
status: "backlog"
priority: P1
type: feature
---

# Add API configuration and baseline security controls

Task: TASK-078
Status: backlog
Priority: P1
Type: feature
Author:
Created: 2026-05-15
Related: TASK-014, TASK-036, TASK-040, TASK-073

## Problem

A REST API introduces new runtime configuration and security concerns that do
not exist for local CLI use. The first API version needs explicit controls for
credentials, CORS, upload limits, and optional access protection.

## Definition of Done

- [ ] Add API-specific configuration keys for host, port, allowed origins,
      upload limits, workspace location, and job retention.
- [ ] Load API configuration through the same documented precedence model used
      by the rest of Bookvoice where practical.
- [ ] Add optional bearer-token authentication suitable for single-user or
      internal deployments.
- [ ] Ensure provider API keys are never returned in API responses, logs, or
      OpenAPI examples.
- [ ] Add CORS middleware only when configured, with restrictive defaults.
- [ ] Add tests covering auth enabled, auth disabled, CORS configuration, and
      secret redaction.
- [ ] Document environment variables and local development defaults.

## Notes

- Authentication can be simple for the first version, but the behavior must be
      explicit and testable.
- Avoid introducing a user account system unless a separate task requests it.
- Keep configuration names consistent with existing `BOOKVOICE_*` variables.
