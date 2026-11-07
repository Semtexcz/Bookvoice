# Tasks

## 1. Proficiency normalization

- [x] 1.1 Add `bookvoice/llm/proficiency.py` with the supported CEFR labels and `normalize_proficiency_level()`; verify focused tests cover every label.
- [x] 1.2 Add offline unit tests for case-insensitive normalization, `None`, and rejection of unsupported values with a diagnostic listing supported labels.

## 2. Translation interface

- [x] 2.1 Add keyword-only `proficiency_level` to `OpenAITranslator` and the extended `ProficiencyAwareTranslator` protocol; keep the legacy `Translator` contract unchanged; include the normalized level in prompt and cache identity only when supplied; verify translation unit tests pass.
- [x] 2.2 Add translation tests proving the prompt contains the level and preservation constraints, omitted prompts stay unchanged, and cache entries separate by level while case variants share an entry.

## 3. Audio-rewrite interface

- [x] 3.1 Add keyword-only `proficiency_level` to `AudioRewriter`, `DeterministicBypassRewriter`, and the extended `ProficiencyAwareRewriter` protocol; keep the legacy `Rewriter` contract unchanged; include the level in prompt and cache identity only when supplied; verify rewrite unit tests pass.
- [x] 3.2 Add rewrite tests proving prompt guidance, omitted-prompt compatibility, cache isolation by level, and bypass pass-through with an accepted level.

## 4. Library documentation

- [x] 4.1 Document the optional keyword-only parameter, supported labels, normalization, cache behavior, and omitted-level compatibility in `docs/library-usage.md`; verify the example matches the implemented signature.

## 5. Verification

- [x] 5.1 Run `make check` and confirm Ruff, mypy, and the full test suite pass.
- [x] 5.2 Run CI-equivalent pytest coverage and confirm total coverage is at least 80%.
- [x] 5.3 Run `openspec validate add-proficiency-level-to-llm-interfaces --strict --no-interactive` and confirm the change is valid.
- [x] 5.4 Run `git diff --check` and confirm no whitespace errors.

## 6. Review repairs

- [x] 6.1 Restore the legacy `Translator` and `Rewriter` protocols and add `ProficiencyAwareTranslator` and `ProficiencyAwareRewriter`; verify mypy conformance examples for `SlowTranslator`, `SlowRewriter`, concrete adapters, and pipeline signatures.
- [x] 6.2 Add legacy cache identity regression tests for omitted, explicit `None`, `A2`/`a2`, different levels, and preseeded entries in both adapters.
- [x] 6.3 Add `AudioRewriter` validation tests for invalid, empty, and whitespace-only levels; verify cache entries and hit/miss counters are unchanged.
- [x] 6.4 Bump `pyproject.toml` and `bookvoice.__version__` to `0.23.0` and add the changelog entry.
- [x] 6.5 Update library documentation and OpenSpec artifacts for protocol compatibility, validation, cache identity, and release metadata.
- [x] 6.6 Re-run `make check`, CI-equivalent coverage, OpenSpec strict validation, and `git diff --check`.

## Workflow follow-up

- Do not archive this change during the pilot; it remains the reviewable OpenSpec record.
