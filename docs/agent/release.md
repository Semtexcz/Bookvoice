# Agent Release Playbook

## Purpose

This playbook covers version, changelog, commit, and release preparation rules.

## Release-Relevant Changes

Update version and `CHANGELOG.md` only for release-relevant changes.

Release-relevant means:

- user-visible behavior change
- public API change
- CLI behavior change
- dependency change that affects users
- task explicitly marked as release-relevant
- actual release preparation

## Semantic Versioning

When a version bump is required:

- MAJOR for breaking changes
- MINOR for backward-compatible features
- PATCH for backward-compatible fixes

Update the version source used by the project, usually `pyproject.toml`.

## Changelog

When changelog updates are required:

- use clear user-facing language
- group entries under `Added`, `Changed`, `Fixed`, or another existing project heading
- avoid implementation trivia unless it affects users

## Commits

Do not commit unless explicitly requested.

When asked to commit:

1. Inspect `git status` and the diff.
2. Include only files related to the requested change.
3. Run relevant checks first.
4. Use a Conventional Commit message.
5. Do not commit secrets.
6. Do not commit failing tests unless explicitly requested.

Examples:

```text
feat(cli): add dataset export command
fix(api): reject empty export paths
docs(agent): split guidance into playbooks
```

## Release Preparation

For an actual release:

- confirm the intended version
- run the full documented test suite
- verify changelog completeness
- verify generated files if the project has them
- keep release commits focused and auditable
