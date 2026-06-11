---
task: TASK-082
status: "done"
priority: P1
type: feature
---

# Support resume for interrupted builds before final manifest write

Task: TASK-082
Status: done
Priority: P1
Type: feature
Author:
Created: 2026-06-10
Related: TASK-008, TASK-037, TASK-080

## Problem

The `resume` command can continue a run from an existing `run_manifest.json`,
but the full `build` command currently writes that manifest only during the
final `manifest` stage. If a user interrupts the build before that point, stage
artifacts may already exist under the run directory, but there is no manifest
path that can be passed to `bookvoice resume`.

## Proposed Solution

Persist a resumable manifest or checkpoint metadata during the build as soon as
the run root and configuration are known, then update it after each completed
stage with the latest available artifact paths and stage status.

## Expected Benefit

Users can return to long-running builds after Ctrl+C, terminal closure, provider
timeouts, or process termination, even when the final manifest stage was never
reached.

## Definition of Done

- [x] Create an initial resumable manifest or checkpoint file early in
      `bookvoice build`, before long-running provider stages begin.
- [x] Update the resumable state after each completed stage with deterministic
      artifact paths and the latest completed stage.
- [x] Ensure `bookvoice resume <manifest>` can continue from a partially written
      build state that has not reached the final `manifest` stage.
- [x] Preserve existing final `run_manifest.json` behavior for completed builds.
- [x] Make partial-state writes atomic enough to avoid corrupted JSON when the
      process is interrupted during checkpoint persistence.
- [x] Add integration coverage for interruption before `translate`, before
      `rewrite`, and before `tts`, verifying that resume reuses completed
      artifacts and replays only missing downstream stages.
- [x] Document how users can find and resume an interrupted run.

## Notes

- Coordinate with existing resume validation from `TASK-037`; partial state
  should still fail clearly when artifact sets are inconsistent or corrupted.
- Avoid storing secrets in the resumable manifest or checkpoint metadata.
- Prefer reusing the normal `run_manifest.json` path if it can be made safe
  without weakening the completed-run manifest contract.
