---
task: TASK-051
status: "done"
priority: P1
type: chore
---

# Resolve current mypy baseline errors and enforce blocking CI gate

Task: TASK-051
Status: done
Priority: P1
Type: chore
Author:
Created: 2026-02-24
Related: .github/workflows/ci.yml

## Problem

The repository currently contains existing `mypy` baseline errors, so CI must run `mypy` in non-blocking mode to avoid failing all pull requests. This weakens type-safety enforcement for new changes.

## Definition of Done

- [x] Fix all current `mypy` errors reported by `poetry run mypy --config-file pyproject.toml --explicit-package-bases bookvoice tests`.
- [x] Ensure required third-party type stubs are available in development and CI environments.
- [x] Update CI workflow to remove non-blocking behavior for the `mypy` step.
- [x] Verify CI passes with blocking `mypy`, `ruff`, and `pytest` coverage gate.
- [x] Document any relevant typing conventions or constraints introduced during fixes.

## Notes

- Keep the remediation incremental and deterministic; avoid broad refactors unrelated to typing correctness.
- Prefer explicit typing fixes over suppressions. Use `# type: ignore[...]` only with a clear, justified reason.
