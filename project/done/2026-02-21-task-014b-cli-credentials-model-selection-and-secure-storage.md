---
task: TASK-014B
status: "done"
priority: P1
type: feature
---

# CLI credential and model selection with secure API key storage

Task: TASK-014B
Status: done
Priority: P1
Type: feature
Author:
Created: 2026-02-21
Related: TASK-014, TASK-014A

## Problem

Many CLI users cannot reliably work with `.env` files. Current flow does not provide a user-friendly path to enter provider credentials and model settings interactively.

## Definition of Done

- [x] Add CLI options and prompts for provider API key and model selection for translation, rewrite, and TTS.
- [x] API key input in CLI is hidden and never echoed in plain text logs or errors.
- [x] CLI-entered API key is stored securely for reuse in future runs (OS keychain or equivalent secure credential store).
- [x] Provide a CLI path to update or clear stored credentials.
- [x] Document deterministic precedence of values (CLI explicit input > secure storage > environment > defaults).
- [x] Add tests for interactive prompt path and non-interactive option path.

## Notes

- Storage must be secure by default; plain text files are not acceptable for secrets.
- Keep UX simple: a first-time setup experience plus explicit override options.
