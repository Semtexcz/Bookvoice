# Changelog

All notable changes to this project will be documented in this file.

## [0.1.14] - 2026-02-21

- Fixed `test_parse_chapter_selection_rejects_out_of_bounds_indices` to assert invalid 1-based index diagnostics for `0` and out-of-bounds diagnostics for `6`.

## [0.1.13] - 2026-02-21

- Completed `TASK-018` by adding `--chapters` chapter-scope selection support to `bookvoice build` and `bookvoice chapters-only`.
- Added canonical chapter selection parsing and validation for single/list/range/mixed syntax with actionable overlap and bounds errors.
- Updated pipeline orchestration and resume flow to process only selected chapters downstream and persist deterministic chapter scope metadata across artifacts and manifest.
- Added coverage for parser validation, selected-scope build behavior, invalid CLI selection failures, and resume regeneration with preserved selected scope.
- Updated README chapter-selection syntax, examples, and testing-focused partial-run usage guidance.

## [0.1.12] - 2026-02-21

- Completed `TASK-017` by adding a dedicated `bookvoice list-chapters` CLI command.
- Added chapter listing support for both direct PDF extract/clean/split flow and existing `text/chapters.json` artifacts.
- Added deterministic CLI output with chapter index/title rows plus chapter source and optional fallback reason metadata.
- Added integration test coverage for successful artifact-based listing and stage-aware failure diagnostics for missing artifacts.

## [0.1.11] - 2026-02-21

- Added `TASK-017` to backlog for a CLI command that lists extracted book chapters with source metadata.
- Added `TASK-018` to backlog for CLI chapter selection (single/list/range) to support partial processing for faster testing.

## [0.1.10] - 2026-02-21

- Completed `TASK-016` by adding a dedicated `bookvoice chapters-only` CLI command for extract/clean/chapter-split only.
- Added deterministic chapter-only artifact coverage and verified downstream stage artifacts are not created.
- Updated README and artifacts documentation with chapter-only usage and `text/chapters.json` metadata shape.

## [0.1.9] - 2026-02-21

- Added `TASK-016` to backlog for a CLI chapter-only mode that splits PDF into chapters without running downstream stages.

## [0.1.8] - 2026-02-21

- Added `pytest-cov` to development test dependencies.
- Enabled optional coverage runs through `pytest-cov` (for example `pytest --cov=bookvoice --cov-report=term-missing`).

## [0.1.7] - 2026-02-21

- Added integration coverage for real PDF outline chapter splitting using a generated outline-enabled PDF fixture.
- Verified that pipeline chapter splitting prefers `pdf_outline` source even when cleaned text lacks chapter heading markers.

## [0.1.6] - 2026-02-21

- Completed `TASK-013` by adding first-level PDF outline chapter extraction with deterministic text-split fallback.
- Updated pipeline chapter splitting to prefer PDF outline boundaries and persist source/fallback metadata in chapter artifacts and run manifest.
- Added test coverage for both chapter extraction paths (outline-present and fallback-to-text), and surfaced chapter source details in CLI output.

## [0.1.5] - 2026-02-21

- Added `TASK-015` to backlog for online model-based pricing integration in cost tracking and manifest reporting.

## [0.1.4] - 2026-02-21

- Completed `TASK-011` by integrating deterministic LLM/TTS cost tracking into build and resume pipeline paths.
- Added `total_cost_usd` into run manifest payload and CLI run summaries (`build`, `resume`).
- Added integration test coverage for cost fields and deterministic CLI cost summary output.

## [0.1.3] - 2026-02-21

- Completed `TASK-010` by adding smoke coverage for `bookvoice build` on the canonical PDF fixture.
- Added smoke assertion for stage-aware failure output to keep pipeline diagnostics explicit.
- Moved `TASK-010` from `project/backlog/` to `project/done/`.

## [0.1.2] - 2026-02-21

- Added `TASK-014` to backlog for real LLM and TTS provider API integration.
- Clarified in `TASK-005` and `TASK-006` that completed MVP paths are deterministic stubs.

## [0.1.1] - 2026-02-21

- Added stage-scoped pipeline exceptions for core build and resume failures.
- Unified CLI failure diagnostics with concise actionable hints and stable exit code `1`.
- Added CLI error-handling tests and README troubleshooting guidance.

## [0.1.0] - 2026-02-20

- Initial open-source scaffold.
- Added package structure, typed stubs, and project documentation.
