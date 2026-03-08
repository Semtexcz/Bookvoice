---
task: TASK-060
status: "backlog"
priority: P2
type: chore
---

# Add CI and release automation for Linux Debian package artifacts

Task: TASK-060
Status: backlog
Priority: P2
Type: chore
Author:
Created: 2026-02-28
Related: TASK-058, TASK-059, .github/workflows

## Problem

Even with local `.deb` packaging support, maintainers need a repeatable release
process that builds, validates, and publishes Linux installer artifacts without
manual drift between releases.

## Definition of Done

- [ ] Add or extend CI workflow coverage to build the Linux `.deb` artifact on a
      supported Linux runner.
- [ ] Add release-time smoke validation for the produced package, including
      installation and a credential-free CLI command check.
- [ ] Publish a versioned Linux release artifact with a stable naming convention
      suitable for GitHub Releases.
- [ ] Ensure workflow steps fail clearly when package build inputs are missing or
      validation fails.
- [ ] Document required release inputs, secrets (if any), and maintainer
      operational steps for Linux packaging.

## Notes

- Keep Linux packaging automation separate from Windows-specific signing and
  installer concerns.
- Prefer deterministic build inputs so release artifacts remain auditable across
  reruns.
