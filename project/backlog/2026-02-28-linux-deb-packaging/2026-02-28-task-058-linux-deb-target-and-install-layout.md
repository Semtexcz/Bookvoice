---
task: TASK-058
status: "backlog"
priority: P1
type: chore
---

# Define Linux Debian package target, support policy, and install layout

Task: TASK-058
Status: backlog
Priority: P1
Type: chore
Author:
Created: 2026-02-28
Related: pyproject.toml, README.md

## Problem

Bookvoice has no defined Linux distribution target for end-user installation. A
`.deb` package should prioritize the largest practical user segment, but the
project does not yet specify which Debian-family systems are officially
supported, which architecture is first-class, or how files should be laid out on
target systems.

## Definition of Done

- [ ] Define the primary supported Linux target as Ubuntu LTS on `amd64`, with
      any explicitly supported Debian-family compatibility documented.
- [ ] Document the initial support policy for package scope, including whether
      the first release targets only `amd64` and whether non-LTS releases are
      best-effort or unsupported.
- [ ] Define the filesystem layout for the package, including:
  - [ ] CLI entry point location
  - [ ] Installed application files
  - [ ] Bundled versus external runtime tools
  - [ ] License and metadata file placement
- [ ] Define how Bookvoice versioning maps to package versioning and artifact
      naming for Linux release assets.
- [ ] Document the expected package ownership boundaries between the Bookvoice
      `.deb` and system-provided dependencies.

## Notes

- Optimize for the largest desktop Linux audience first, not for maximum distro
  coverage.
- Prefer Ubuntu LTS compatibility decisions that also work on recent Debian
  derivatives when feasible.
- Keep the first packaging scope intentionally narrow and explicitly documented.
