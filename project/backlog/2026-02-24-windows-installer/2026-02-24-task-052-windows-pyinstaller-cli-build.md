---
task: TASK-052
status: "backlog"
priority: P2
type: chore
---

# Windows distributable CLI build via PyInstaller

Task: TASK-052
Status: backlog
Priority: P2
Type: chore
Author:
Created: 2026-02-24
Related: TASK-051

## Problem

Windows users currently need Python + Poetry to run Bookvoice. Provide a self-contained `bookvoice.exe` to reduce installation friction.

## Definition of Done

- [ ] Add a PyInstaller build definition (spec file or equivalent) that produces `bookvoice.exe`.
- [ ] Ensure the built executable runs `bookvoice --help` successfully on Windows 10/11 without Poetry.
- [ ] Ensure runtime output paths and artifact layout remain deterministic and unchanged.
- [ ] Ensure `bookvoice.exe` exposes all existing CLI commands (at minimum: `build`, `resume`, `translate-only`, `tts-only`, `list-chapters`, `credentials`).
- [ ] Include a minimal smoke check for the executable in CI (no provider calls required).
- [ ] Document build instructions for maintainers (how to produce the Windows build locally).

## Notes

- Prefer a one-folder distribution for debugging clarity first; evaluate `--onefile` only after stability.
- External dependencies (`pdftotext`, `ffmpeg`) are handled in dedicated tasks.

