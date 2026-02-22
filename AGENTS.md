# Agent Rules

This file defines mandatory rules for all AI agents and automated contributors
working on this Python project. These rules are strict and non-negotiable.

---

## 1. General Principles

- Follow a **clean, explicit, and maintainable** coding style.
- Prefer **clarity over cleverness**.
- Assume the codebase is long-lived and will be maintained by other developers.
- Never remove functionality unless explicitly instructed.
- Never introduce breaking changes without clearly documenting them.

---

## 2. Language & Communication

- This project is **English-only**.
- All of the following must be written in English:
  - Code comments
  - Docstrings
  - Commit messages
  - Documentation
  - Task descriptions and status updates
  - Agent communication

---

## 3. Code Quality Rules

- Every **module, class, and function** must include a docstring.
- Use **type hints** wherever reasonably possible.
- Follow **PEP 8** and idiomatic Python conventions.
- Keep functions small and single-purpose.
- Avoid implicit behavior and magic values.

---

## 4. Versioning & Change Management (MANDATORY)

After **every code change**, the agent must:

1. **Create a Conventional Commit message**
   - Format: `type(scope): short description`
   - Examples:
     - `feat(api): add PDF text extraction`
     - `fix(cli): handle empty input gracefully`
     - `refactor(core): simplify pipeline initialization`

2. **Bump the program version**
   - Follow **Semantic Versioning (SemVer)**:
     - `MAJOR`: breaking changes
     - `MINOR`: new features, backward-compatible
     - `PATCH`: bug fixes, refactors
   - Version must be updated in the canonical version source (e.g. `pyproject.toml`).

3. **Update `CHANGELOG.md`**
   - Add a clear, human-readable description of the change.
   - Reference the version number.
   - Group changes under appropriate headings (`Added`, `Changed`, `Fixed`, etc.).

---

## 5. Task Workflow (project/backlog)

- Tasks are stored in `project/backlog/`.
- When implementing a task:
  1. Read the task file carefully.
  2. Implement exactly what is requested.
  3. After completion:
     - Set task status to `done`.
     - Move the task file to `project/done/`.
- Do **not** modify unrelated tasks.

---

## 6. Testing

- All tests must be runnable via:

```bash
  poetry run pytest
```

- If new functionality is added:

  - Add or update tests accordingly.
- Tests should be:

  - Deterministic
  - Fast
  - Focused on behavior, not implementation details

---

## 7. Dependency Management

- Use **Poetry** for dependency management.
- Do not add new dependencies unless:

  - They are clearly justified.
  - They are actively maintained.
- Prefer standard library solutions where possible.

---

## 8. What NOT to Do

- Do not skip version bumps.
- Do not skip changelog updates.
- Do not write vague commit messages.
- Do not introduce undocumented behavior.
- Do not leave TODOs without explanation.
- Do not mix multiple unrelated changes in one commit.

---

## 9. When in Doubt

- Ask for clarification rather than guessing.
- Prefer a smaller, well-documented change over a large implicit one.
- Make assumptions explicit in comments or documentation.

---

**By contributing to this project, the agent agrees to follow all rules above.**
