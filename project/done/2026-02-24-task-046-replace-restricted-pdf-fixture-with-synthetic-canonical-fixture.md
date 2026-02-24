---
task: TASK-046
status: "done"
priority: P1
type: chore
---

# Replace restricted PDF fixture with a synthetic canonical test fixture

Task: TASK-046
Status: done
Priority: P1
Type: chore
Author:
Created: 2026-02-24
Related: TASK-010, TASK-013

## Problem

Current test coverage references `tests/files/zero_to_one.pdf`, which cannot be publicly redistributed. The repository needs a license-safe fixture that preserves deterministic integration behavior.

## Definition of Done

- [x] Add a new canonical fixture PDF in `tests/files/` that is fully synthetic and safe to publish.
- [x] Ensure the fixture includes deterministic chapter-like structure and enough content for chapter split and pipeline integration scenarios.
- [x] Keep fixture generation deterministic (either committed binary fixture with documented provenance or deterministic in-repo generation flow).
- [x] Remove direct runtime dependency on `tests/files/zero_to_one.pdf` from active tests.
- [x] Validate that integration tests currently using the canonical fixture pass with the replacement file.

## Notes

- Keep fixture size minimal to preserve test speed.
- Fixture text should be fully authored for this repository (no copyrighted source text).
