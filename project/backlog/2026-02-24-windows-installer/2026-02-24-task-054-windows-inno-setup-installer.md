---
task: TASK-054
status: "backlog"
priority: P2
type: feature
---

# Windows installer wizard via Inno Setup

Task: TASK-054
Status: backlog
Priority: P2
Type: feature
Author:
Created: 2026-02-24
Related: TASK-052, TASK-053

## Problem

Even with a zipped distribution, many Windows users prefer an installation wizard with uninstallation support and a predictable install location.

## Definition of Done

- [ ] Add an Inno Setup script that installs Bookvoice to a standard location (per-user install is acceptable).
- [ ] The installer includes:
  - `bookvoice.exe`
  - bundled `ffmpeg` + `pdftotext` (per `TASK-053`)
  - required license files/notices
- [ ] Create Start Menu shortcuts (at minimum: "Bookvoice (CLI)" opening a terminal with usage instructions or linking to docs).
- [ ] Add an uninstaller entry.
- [ ] Ensure upgrades are supported (install over an existing version without manual cleanup).
- [ ] Validate the installed app can run `bookvoice --help` and `bookvoice list-chapters <pdf>` (no provider calls required).

## Notes

- Do not require admin rights unless absolutely necessary.
- Do not implement auto-updates; distribution is GitHub Releases only.

