# Tasks

## 1. Proficiency normalization

- [x] 1.1 Add `bookvoice/llm/proficiency.py` with the supported CEFR labels and `normalize_proficiency_level()`; verify focused tests cover every label.
- [x] 1.2 Add offline unit tests for case-insensitive normalization, `None`, and rejection of unsupported values with a diagnostic listing supported labels.

## 2. Translation interface

- [x] 2.1 Add keyword-only `proficiency_level` to the translation protocol and `OpenAITranslator`; include the normalized level in prompt and cache identity only when supplied; verify translation unit tests pass.
- [x] 2.2 Add translation tests proving the prompt contains the level and preservation constraints, omitted prompts stay unchanged, and cache entries separate by level while case variants share an entry.

## 3. Audio-rewrite interface

- [x] 3.1 Add keyword-only `proficiency_level` to the rewrite protocol, `AudioRewriter`, and `DeterministicBypassRewriter`; include the level in prompt and cache identity only when supplied; verify rewrite unit tests pass.
- [x] 3.2 Add rewrite tests proving prompt guidance, omitted-prompt compatibility, cache isolation by level, and bypass pass-through with an accepted level.

## 4. Library documentation

- [x] 4.1 Document the optional keyword-only parameter, supported labels, normalization, cache behavior, and omitted-level compatibility in `docs/library-usage.md`; verify the example matches the implemented signature.

## 5. Verification

- [x] 5.1 Run `make check` and confirm Ruff, mypy, and the full test suite pass.
- [x] 5.2 Run CI-equivalent pytest coverage and confirm total coverage is at least 80%.
- [x] 5.3 Run `openspec validate add-proficiency-level-to-llm-interfaces --strict --no-interactive` and confirm the change is valid.
- [x] 5.4 Run `git diff --check` and confirm no whitespace errors.

## Workflow follow-up

- Do not archive this change during the pilot; it remains the reviewable OpenSpec record.
