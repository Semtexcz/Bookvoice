---
task: TASK-081
status: "done"
priority: P2
type: enhancement
---

# Show time in log output

Task: TASK-081
Status: done
Priority: P2
Type: enhancement
Author:
Created: 2026-06-10
Related: TASK-019, TASK-080

## Problem

CLI logs show pipeline activity, but they do not make elapsed or wall-clock time
visible enough for users to understand when long-running processing stages are
still making progress.

## Proposed Solution

Include time information in CLI log output, such as a timestamp, elapsed runtime,
or stage duration, using a consistent format that remains readable in terminals
and deterministic enough for tests.

## Expected Benefit

Users can better judge how long a run has been active, when the last visible
activity happened, and which stages are taking the most time.

## Definition of Done

- [x] Add time information to CLI log output for pipeline stage activity.
- [x] Use a clear, documented format for timestamps, elapsed runtime, or stage
      duration values.
- [x] Keep default log output concise and avoid noisy per-token or per-line time
      messages.
- [x] Preserve deterministic tests by controlling, injecting, or normalizing time
      values where needed.
- [x] Add or update tests that verify time information appears in relevant log
      output.
- [x] Update user-facing documentation with an example of timed log output.

## Notes

- Coordinate formatting with the existing `loguru` integration from `TASK-019`.
- Prefer explicit stage duration reporting if wall-clock timestamps would make
  CLI output harder to test or compare.
