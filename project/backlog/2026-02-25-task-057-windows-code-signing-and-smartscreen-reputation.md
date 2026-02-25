---
task: TASK-057
status: "backlog"
priority: P1
type: chore
---

# Add Windows code-signing pipeline and SmartScreen mitigation

Task: TASK-057
Status: backlog
Priority: P1
Type: chore
Author:
Created: 2026-02-25
Related: TASK-054, TASK-055, .github/workflows/windows-release.yml

## Problem

Current Windows release artifacts (`bookvoice.exe` and installer `.exe`) can show
"Unknown publisher" and SmartScreen warnings. This reduces user trust and creates
installation friction even when binaries are downloaded from official releases.

## Definition of Done

- [ ] Define signing requirements and supported certificate profile(s) (OV and/or EV) for Bookvoice Windows releases.
- [ ] Extend the Windows release workflow to sign both:
  - [ ] `bookvoice.exe` (PyInstaller output)
  - [ ] `bookvoice-windows-x64-vX.Y.Z-setup.exe` (Inno Setup installer artifact)
- [ ] Configure trusted timestamping in the signing command so signatures remain valid after certificate expiry.
- [ ] Ensure secrets/certificate material are handled securely in CI with clear rotation guidance.
- [ ] Add release-time verification step(s) to validate signature presence and signer identity on produced artifacts.
- [ ] Document maintainer setup and operational runbook for certificate provisioning, CI configuration, and fallback behavior when signing is unavailable.
- [ ] Update end-user Windows docs with concise guidance on signature verification and expected publisher display.

## Notes

- Prefer signing at build/release time in CI so distributed artifacts are always signed consistently.
- Keep unsigned local developer builds supported; enforce signing only for release artifacts.
- If EV certificate hardware token constraints make full CI signing impractical, document a deterministic manual signing handoff process.
