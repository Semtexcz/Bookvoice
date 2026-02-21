---
task: TASK-022
status: "done"
priority: P1
type: feature
---

# Standardize audio filenames as chapter_part_title

Task: TASK-022
Status: done
Priority: P1
Type: feature
Author:
Created: 2026-02-21
Related: TASK-021

## Problem

Generated audio files currently do not follow a strict naming pattern that clearly identifies chapter and part. Required naming should start with chapter number, then underscore, then chapter part, then title.

## Definition of Done

- [x] Define deterministic filename format: `<chapter>_<part>_<title-slug>.wav`.
- [x] Chapter index and part index are always present and zero-padded (`001_01_<title>.wav`).
- [x] Title segment is normalized to filesystem-safe ASCII slug.
- [x] Naming applies consistently to part files and merged outputs where applicable.
- [x] Manifest/artifacts include the final emitted filename for each produced audio file.
- [x] Add tests verifying naming format and deterministic slug behavior.
- [x] Update `README.md` with naming convention examples.

## Notes

- Keep filenames stable across repeated runs with identical inputs.
- Avoid locale-dependent transformations in slug generation.
