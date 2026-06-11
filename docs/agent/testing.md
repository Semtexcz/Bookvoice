# Agent Testing Playbook

## Purpose

Testing should verify behavior with the smallest reliable test surface.

## Command Selection

Use project-defined commands first:

1. `justfile`
2. `Makefile`
3. `README.md`
4. Poetry fallback commands

Common fallback commands:

```bash
poetry run pytest
poetry run ruff check .
poetry run ruff format .
poetry run mypy --config-file pyproject.toml --explicit-package-bases bookvoice tests
```

## Test Strategy

- Prefer unit tests for focused logic.
- Add integration tests when multiple modules interact.
- Use end-to-end tests for critical workflows only.
- Keep tests deterministic and fast.
- Test externally visible behavior, not private implementation details.
- Add regression tests for bug fixes when practical.

Read `context/test-strategy.md` when adding tests or changing the testing approach.

## Bug Fix Testing

For bug fixes:

1. Reproduce the bug or record why reproduction is not possible.
2. Add or update a failing test when practical.
3. Implement the smallest fix.
4. Verify the new or changed test passes.
5. Run relevant regression tests.

If the bug cannot be reproduced, avoid speculative fixes. Document the investigation and recommend the next smallest step.

## AI And LLM Features

Do not rely on live LLM calls in unit tests.

For LLM-related features, prefer deterministic tests around:

- prompt construction
- input validation
- output parsing
- schema validation
- fallback behavior
- tool selection logic
- error handling

Mock model, provider, and tool boundaries. Store representative inputs and outputs in fixtures when useful.

If behavior depends on model quality, add small evaluation examples in `evals/` or `tests/fixtures/` and document how to run them. Keep these separate from fast unit tests unless they are fully deterministic.

## Reporting

In the final response, state:

- which checks were run
- whether they passed
- which checks were skipped and why
- any residual risk from incomplete verification
