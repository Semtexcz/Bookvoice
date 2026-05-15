---
task: TASK-077
status: "backlog"
priority: P2
type: feature
---

# Add chapter discovery endpoints

Task: TASK-077
Status: backlog
Priority: P2
Type: feature
Author:
Created: 2026-05-15
Related: TASK-016, TASK-017, TASK-066, TASK-067, TASK-068, TASK-076

## Problem

Clients should be able to inspect a source document and choose chapters before
submitting a full build job. The CLI already has chapter discovery flows, but
the API needs stable HTTP endpoints for the same capability.

## Definition of Done

- [ ] Implement `POST /api/v1/sources/{source_id}/chapters` or an equivalent
      endpoint that extracts chapter information for an uploaded source.
- [ ] Return chapter identifiers, titles, ordering, and source format metadata
      in a documented response model.
- [ ] Surface extraction failures with actionable HTTP error responses.
- [ ] Reuse existing chapter extraction and source-format helpers rather than
      duplicating PDF or EPUB parsing logic.
- [ ] Add tests covering successful chapter listing and at least one invalid or
      unsupported source case.
- [ ] Document how chapter identifiers from this endpoint map into job
      submission requests.

## Notes

- The endpoint should remain read-only and must not start audio or translation
      pipeline stages.
- Keep source metadata sufficient for clients to render a chapter picker.
