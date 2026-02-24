---
task: TASK-056
status: "backlog"
priority: P3
type: docs
---

# Windows user documentation and troubleshooting

Task: TASK-056
Status: backlog
Priority: P3
Type: docs
Author:
Created: 2026-02-24
Related: TASK-052, TASK-054

## Problem

Windows users need clear guidance on installation, prerequisites (if any), and common failure modes (missing tools, audio codecs, permissions).

## Definition of Done

- [ ] Add a Windows-specific section to documentation describing:
  - how to install from GitHub Releases (portable zip and installer)
  - where outputs are written and how to set `--out`
  - how to provide an API key securely (keyring vs environment variable)
- [ ] Add troubleshooting guidance for:
  - `pdftotext` missing/not found
  - `ffmpeg` missing/not found
  - encoding/codec issues during packaging
  - antivirus false positives and recommended mitigations
- [ ] Keep documentation aligned with actual bundled behavior (no references to Poetry for end-users).

