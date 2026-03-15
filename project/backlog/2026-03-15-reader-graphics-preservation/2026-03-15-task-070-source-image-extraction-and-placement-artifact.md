---
task: TASK-070
status: "backlog"
priority: P1
type: feature
---

# Add source image extraction and placement artifact for reader exports

Task: TASK-070
Status: backlog
Priority: P1
Type: feature
Author:
Created: 2026-03-15
Related: TASK-063, TASK-067, TASK-069

## Problem

Reader exporters cannot preserve graphics unless the pipeline extracts source
images and stores deterministic placement references alongside translated text.

## Definition of Done

- [ ] Introduce a canonical artifact for source graphics referenced by
      translation-only reader exports.
- [ ] Capture enough metadata to replay graphics in downstream exporters,
      including stable identifiers, chapter association, order, and placement
      anchors relative to surrounding translated content.
- [ ] Define deterministic handling for unsupported image formats, duplicate
      embedded assets, and missing placement metadata.
- [ ] Add synthetic fixtures with embedded images for deterministic tests.
- [ ] Add automated tests for artifact serialization, image ordering, and
      placement-anchor stability.

## Notes

- Keep this artifact scoped to reader exports; do not couple it to audiobook
  artifacts.
- Avoid layout-engine-specific coordinates unless they are required for
  deterministic export behavior.
