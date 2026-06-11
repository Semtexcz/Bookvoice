# Agent Review Playbook

## Purpose

Use this playbook when reviewing code, pull requests, diffs, or proposed changes.

## Review Priorities

Prioritize findings in this order:

1. correctness bugs
2. regressions
3. security issues
4. missing or weak tests
5. maintainability risks

Do not lead with style comments unless style creates real risk or violates project automation.

## Findings Format

List findings first, ordered by severity.

For each finding, include:

- file and line reference when possible
- concrete behavior or risk
- why it matters
- the smallest useful fix

If no issues are found, say so clearly and mention residual test gaps or risks.

## Review Scope

- Review only the requested diff or files unless broader context is needed.
- Do not request unrelated refactors.
- Distinguish confirmed defects from questions or preferences.
- Verify claims against code when practical.

## Questions And Summary

After findings, include open questions or assumptions if needed.

Keep summaries brief. Findings are more important than describing the patch.
