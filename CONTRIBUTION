# Contribution Rules

Thank you for contributing to `bookvoice`.

This project accepts pull requests, but every contribution must follow the rules below.

## Pull Request Requirements

Before opening a PR, ensure all items are complete:

1. Code quality and style:
   - Follow clean, explicit, maintainable Python style.
   - Prefer clarity over cleverness.
   - Keep functions small and single-purpose.
   - Use type hints where reasonably possible.
   - Follow PEP 8 and idiomatic Python conventions.
   - Add docstrings to every module, class, and function.
2. Language:
   - All code comments, docstrings, commit messages, and documentation must be in English.
3. Testing:
   - Run the full test suite with:
     - `poetry run pytest`
   - If you add or change behavior, add or update tests.
4. Versioning and release notes (mandatory for every code change):
   - Use a Conventional Commit message:
     - Format: `type(scope): short description`
     - Example: `fix(cli): handle empty input`
   - Bump the version in `pyproject.toml` using SemVer:
     - `MAJOR` for breaking changes
     - `MINOR` for backward-compatible features
     - `PATCH` for fixes/refactors/docs-only adjustments
   - Update `CHANGELOG.md`:
     - Add the new version section
     - Write clear human-readable notes
     - Use headings such as `Added`, `Changed`, and `Fixed`
5. Scope control:
   - Do not include unrelated changes in one PR.
   - Do not remove existing functionality unless explicitly requested.
   - Do not introduce breaking changes without documenting them.

## Task Files (`project/backlog`)

If your PR implements a backlog task:

1. Implement exactly what the task requests.
2. Mark the task status as `done`.
3. Move the task file from `project/backlog/` to `project/done/`.
4. Do not modify unrelated tasks.

## Dependencies

- Use Poetry for dependency management.
- Avoid adding dependencies unless clearly justified and actively maintained.
- Prefer Python standard library solutions where possible.

## Final PR Checklist

- [ ] Tests pass with `poetry run pytest`
- [ ] Version bumped in `pyproject.toml`
- [ ] `CHANGELOG.md` updated with the new version entry
- [ ] Commit message follows Conventional Commits
- [ ] Documentation/comments/docstrings are in English
- [ ] PR contains only related changes

By submitting a PR, you confirm compliance with these contribution rules.
