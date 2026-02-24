---
task: TASK-051
status: "backlog"
priority: P2
type: chore
---

# Resolve current mypy baseline errors and enforce blocking CI gate

Task: TASK-051
Status: backlog
Priority: P2
Type: chore
Author:
Created: 2026-02-24
Related: TASK-050

## Problem

The repository currently contains existing `mypy` baseline errors, so CI must run `mypy` in non-blocking mode to avoid failing all pull requests. This weakens type-safety enforcement for new changes.

## Definition of Done

- [ ] Fix all current `mypy` errors reported by `poetry run mypy --config-file pyproject.toml --explicit-package-bases bookvoice tests`.
- [ ] Ensure required third-party type stubs are available in development and CI environments.
- [ ] Update CI workflow to remove non-blocking behavior for the `mypy` step.
- [ ] Verify CI passes with blocking `mypy`, `ruff`, and `pytest` coverage gate.
- [ ] Document any relevant typing conventions or constraints introduced during fixes.

## Notes

- Keep the remediation incremental and deterministic; avoid broad refactors unrelated to typing correctness.
- Prefer explicit typing fixes over suppressions. Use `# type: ignore[...]` only with a clear, justified reason.
