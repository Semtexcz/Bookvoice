# Test Strategy

- Prefer unit tests first.
- Add integration tests when multiple modules interact.
- Use e2e tests only for critical workflows.
- Tests must be deterministic.
- Run tests with: `poetry run pytest`
- Run type checks with: `poetry run mypy --config-file pyproject.toml --explicit-package-bases bookvoice tests`
