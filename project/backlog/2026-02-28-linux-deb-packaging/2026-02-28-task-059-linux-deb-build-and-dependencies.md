---
task: TASK-059
status: "backlog"
priority: P1
type: feature
---

# Build a Debian package for Bookvoice and define dependency handling

Task: TASK-059
Status: backlog
Priority: P1
Type: feature
Author:
Created: 2026-02-28
Related: TASK-058, pyproject.toml, README.md

## Problem

Bookvoice does not currently produce a native Linux installer artifact. Users
who are not comfortable with Python tooling need a `.deb` package that installs
cleanly on supported Ubuntu and Debian-family systems with predictable runtime
behavior.

## Definition of Done

- [ ] Add deterministic packaging assets and scripts required to build a versioned
      `.deb` artifact for Bookvoice.
- [ ] Ensure the produced package installs the `bookvoice` CLI in a standard
      executable location expected by Debian-family systems.
- [ ] Define and implement package metadata, including package name, maintainer
      metadata, description, architecture, and version mapping.
- [ ] Declare runtime package dependencies appropriately, including the chosen
      policy for `ffmpeg` and any PDF extraction tools required at runtime.
- [ ] Verify install, upgrade, and uninstall behavior on the primary supported
      Ubuntu LTS target.
- [ ] Verify the installed command can pass at least smoke-check commands that
      do not require provider credentials.
- [ ] Ensure package contents are reproducible enough for CI validation and
      release automation.

## Notes

- Prefer standard Debian packaging conventions over custom installer behavior.
- If bundling third-party Linux binaries is rejected, document and enforce
  system-package dependencies explicitly.
- Keep the first artifact focused on the CLI use case; do not expand into
  distro-specific variants in this task.
