---
task: TASK-055
status: "done"
priority: P2
type: chore
---

# GitHub Actions: build Windows release assets (EXE + installer)

Task: TASK-055
Status: done
Priority: P2
Type: chore
Author:
Created: 2026-02-24
Related: TASK-052, TASK-054

## Problem

Windows deliverables should be built reproducibly and published to GitHub Releases.

## Definition of Done

- [x] Add a GitHub Actions workflow job that runs on Windows and builds:
  - a zipped portable distribution (folder layout including bundled tools)
  - the Inno Setup installer `.exe`
- [x] Configure workflow to publish artifacts to GitHub Releases (triggered by tags).
- [x] Ensure release artifacts include a version in filename (for example `bookvoice-windows-x64-vX.Y.Z.zip`).
- [x] Add a minimal verification step in the workflow:
  - run `bookvoice.exe --help`
  - run a non-provider command that exercises local tooling checks
- [x] Ensure secrets are not required for the release build (no provider calls).

## Notes

- Code signing is out of scope for now.
- Keep the workflow deterministic and pinned (explicit action versions).
