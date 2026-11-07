# Proposal

## Why

Bookvoice's translation and audio-rewrite interfaces cannot currently target a CEFR
proficiency level, so language learners cannot ask for deliberately simpler output.
TASK-044 covers the full feature; this bounded change only adds the library-level
adapter surface needed to evaluate it.

## What Changes

- Add an optional keyword-only `proficiency_level` argument to the concrete
  translator and audio-rewriter adapters while preserving the original legacy
  `Translator` and `Rewriter` protocol contracts.
- Introduce separate `ProficiencyAwareTranslator` and `ProficiencyAwareRewriter`
  protocols for implementations that accept the new argument.
- Accept `A0`, `A1`, `A2`, `B1`, `B2`, `C1`, and `C2` case-insensitively and expose
  the normalized uppercase label.
- Include the normalized level in translation and rewrite prompts while preserving
  meaning, factual information, names, and numbers.
- Isolate response-cache entries by normalized proficiency level.
- Keep the current prompt and cache behavior when the argument is omitted or
  explicitly `None`.
- Record the backward-compatible minor release as `0.23.0` in `CHANGELOG.md` and the
  version sources.
- Add deterministic offline tests and concise library documentation.

Out of scope: CLI controls, pipeline integration, manifest changes, replay
propagation, TTS changes, and any live provider call.

## Capabilities

### New Capabilities

- `llm-proficiency-level`: optional CEFR proficiency targeting in the translator and
  audio-rewriter interfaces, including normalization, prompt guidance, and cache
  isolation.

### Modified Capabilities

None.

## Impact

- `bookvoice/llm/proficiency.py` (new small normalization helper)
- `bookvoice/llm/prompts.py`
- `bookvoice/llm/translator.py`
- `bookvoice/llm/audio_rewriter.py`
- `bookvoice/llm/__init__.py`
- `tests/unit/test_proficiency_level.py` (new offline tests)
- `tests/unit/test_provider_concurrency.py` (protocol conformance examples)
- `docs/library-usage.md`
- `CHANGELOG.md`, `pyproject.toml`, `bookvoice/__init__.py` (release metadata)
- No dependency, configuration, CLI, pipeline, manifest, or CI changes.
