---
task: TASK-074
status: "backlog"
priority: P1
type: feature
---

# Define REST API request and response contracts

Task: TASK-074
Status: backlog
Priority: P1
Type: feature
Author:
Created: 2026-05-15
Related: TASK-073, TASK-024, TASK-043, TASK-066

## Problem

HTTP clients need stable JSON contracts that describe source documents,
chapter selection, provider runtime options, output formats, and pipeline
results without exposing CLI-specific parsing details.

## Definition of Done

- [ ] Add documented request and response models for API build requests.
- [ ] Add documented response models for chapters, run metadata, progress
      events, artifacts, warnings, and errors.
- [ ] Represent source format explicitly instead of assuming PDF-only input.
- [ ] Reuse existing dataclasses and config concepts where practical without
      leaking internal filesystem paths unnecessarily.
- [ ] Validate chapter selection, output format, provider, model, and voice
      options with clear HTTP 422 responses.
- [ ] Add model serialization tests for representative valid and invalid
      payloads.
- [ ] Ensure generated OpenAPI schemas use clear field names and descriptions.

## Notes

- Keep API models in `bookvoice.api.schemas` or an equivalent focused module.
- Avoid duplicating CLI option parsing rules; centralize shared normalization
      helpers when a rule must be used by both CLI and API.
- Treat request/response compatibility as a public API surface.
