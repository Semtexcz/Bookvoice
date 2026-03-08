---
task: TASK-061
status: "backlog"
priority: P2
type: docs
---

# Document Linux Debian package installation, upgrades, and troubleshooting

Task: TASK-061
Status: backlog
Priority: P2
Type: docs
Author:
Created: 2026-02-28
Related: TASK-058, TASK-059, TASK-060, README.md

## Problem

A `.deb` package only reduces support burden if Linux users have clear guidance
for installation, upgrades, dependency expectations, and common runtime issues.
The project currently has no end-user Linux packaging documentation.

## Definition of Done

- [ ] Add end-user documentation for installing the Bookvoice `.deb` package on
      the primary supported Ubuntu LTS target.
- [ ] Document upgrade and uninstall flows using standard Debian-family package
      manager commands.
- [ ] Document how required system dependencies are installed or verified,
      including `ffmpeg` and any required PDF text extraction tools.
- [ ] Add concise troubleshooting guidance for common Linux issues such as:
  - [ ] missing runtime dependencies
  - [ ] unsupported architecture
  - [ ] PATH or command resolution problems
  - [ ] codec or packaging-tool availability differences
- [ ] Update the main project documentation to link to the Linux install guide.

## Notes

- Keep user-facing documentation focused on supported distributions and explicit
  commands.
- Avoid mixing advanced maintainer build instructions into the end-user guide.
