# bookvoice

`bookvoice` is a deterministic, pay-as-you-go pipeline for converting text-based PDF books into Czech audiobook outputs.

What it is not:

- It is not a DRM bypass tool.
- It is not intended for copyrighted material without proper rights.

## Current Status

Implemented today:

- Real OpenAI translation (`chat/completions`).
- Real OpenAI rewrite-for-audio (`chat/completions`), plus `--rewrite-bypass`.
- Real OpenAI TTS per segmented part (`audio/speech`) with deterministic `<chapter>_<part>_<title-slug>.wav` naming.
- Resumable artifact-driven pipeline with run manifest and cost summary.
- Chapter listing and chapter-scope processing (`--chapters`).
- Secure API-key storage via `keyring` (`bookvoice credentials`).

Still intentionally limited:

- `translate-only` and `tts-only` are placeholders.
- Audio postprocessing/tagging are minimal scaffolds.

## Pipeline Overview

```text
PDF Input
  |
  v
[Extract Text] --> [Clean/Normalize] --> [Split Chapters] --> [Plan Segments + Chunk]
  |                                                     |
  |                                                     v
  |                                               [Translate]
  |                                                     |
  |                                                     v
  |                                              [Rewrite for Audio]
  |                                                     |
  v                                                     v
Artifacts + Cache <-------------------------------- [TTS Synthesis]
                                                        |
                                                        v
                                           [Postprocess + Merge + Tags]
                                                        |
                                                        v
                                               Run Manifest + Outputs
```

## Quickstart

### 1. Install

```bash
poetry install
```

### 2. Verify CLI

```bash
poetry run bookvoice --help
```

### 3. Provide API key (recommended)

```bash
poetry run bookvoice credentials --set-api-key
```

### 4. Run build

```bash
poetry run bookvoice build input.pdf --out out/
```

## Core Commands

### Build (full pipeline)

```bash
poetry run bookvoice build input.pdf --out out/
```

Common options:

- `--chapters`: process only selected 1-based chapters (`5`, `1,3,7`, `2-4`, `1,3-5`).
- `--model-translate`, `--model-rewrite`, `--model-tts`, `--tts-voice`.
- `--provider-translator`, `--provider-rewriter`, `--provider-tts` (currently `openai`).
- `--prompt-api-key`: hidden API-key prompt for this run.
- `--interactive-provider-setup`: prompts provider/model/voice values.
- `--store-api-key/--no-store-api-key`.
- `--rewrite-bypass/--no-rewrite-bypass`.

Runtime feedback during `build`:

- Deterministic progress lines per phase (`extract`, `clean`, `split`, `chunk`, `translate`, `rewrite`, `tts`, `merge`, `manifest`).
- Structured phase logs (`[phase]`) for stage start/complete/failure.
- Output is concise and CI-friendly, with no credential material in logs.

Example output excerpt:

```text
[progress] command=build | 1/9 stage=extract
[phase] level=INFO stage=extract event=start
[phase] level=INFO stage=extract event=complete
...
[progress] command=build | 9/9 stage=manifest
[phase] level=INFO stage=manifest event=complete
```

### Chapters-only (fast boundary inspection)

```bash
poetry run bookvoice chapters-only input.pdf --out out/
poetry run bookvoice chapters-only input.pdf --out out/ --chapters 1-3
```

### List chapters

```bash
poetry run bookvoice list-chapters input.pdf
poetry run bookvoice list-chapters --chapters-artifact out/run-*/text/chapters.json
```

### Resume interrupted run

```bash
poetry run bookvoice resume out/run-<id>/run_manifest.json
```

### Credentials

```bash
poetry run bookvoice credentials
poetry run bookvoice credentials --set-api-key
poetry run bookvoice credentials --clear-api-key
```

## Runtime Defaults and Precedence

Default models/voice:

- Translate model: `gpt-4.1-mini`
- Rewrite model: `gpt-4.1-mini`
- TTS model: `gpt-4o-mini-tts`
- TTS voice: `alloy`

Resolution precedence:

- `CLI explicit input > secure credential storage > environment > defaults`

Environment keys:

- `OPENAI_API_KEY`
- `BOOKVOICE_PROVIDER_TRANSLATOR`
- `BOOKVOICE_PROVIDER_REWRITER`
- `BOOKVOICE_PROVIDER_TTS`
- `BOOKVOICE_MODEL_TRANSLATE`
- `BOOKVOICE_MODEL_REWRITE`
- `BOOKVOICE_MODEL_TTS`
- `BOOKVOICE_TTS_VOICE`
- `BOOKVOICE_REWRITE_BYPASS`

## Artifacts You Can Expect

Each build creates a deterministic run directory:

- `out/run-<hash>/text/raw.txt`
- `out/run-<hash>/text/clean.txt`
- `out/run-<hash>/text/chapters.json`
- `out/run-<hash>/text/chunks.json`
- `out/run-<hash>/text/translations.json`
- `out/run-<hash>/text/rewrites.json`
- `out/run-<hash>/audio/chunks/001_01_<title-slug>.wav`
- `out/run-<hash>/audio/parts.json`
- `out/run-<hash>/audio/bookvoice_merged.wav` (or chapter-scope variant)
- `out/run-<hash>/run_manifest.json`

`audio/parts.json` includes deterministic `chapter_index`, `part_index`, `part_id`,
source `source_order_indices`, and per-part `provider`/`model`/`voice` metadata.
`run_manifest.json` `extra` includes compact chapter/part mapping and referenced
structure indices for resume/rebuild stability.

## Troubleshooting

- `build failed at stage extract`: verify input PDF path and `pdftotext` availability.
- `build failed at stage translate`/`rewrite`/`tts`: verify API key and model/provider config.
- `build failed at stage credentials`: configure a working keyring backend or use `--no-store-api-key`.
- `list-chapters failed at stage chapters-artifact`: verify artifact path points to valid `text/chapters.json`.
- `resume failed at stage resume-manifest`: manifest missing or malformed JSON.
- `resume failed at stage resume-artifacts`: artifact JSON is missing/corrupted; remove broken artifact and rerun `resume`.

## Development

### Test suite

```bash
poetry run pytest
```

### Project layout

- `bookvoice/`: core package modules.
- `bookvoice/models/`: shared typed dataclasses.
- `bookvoice/io|text|llm|tts|audio|telemetry/`: pipeline stage modules.
- `docs/`: architecture and module overviews.

### Project docs

- `docs/ARCHITECTURE.md`: data model and orchestration strategy.
- `docs/ARTIFACTS.md`: generated run artifacts and file formats.
- `docs/MODULES.md`: module responsibilities and dependencies.
- `docs/ROADMAP.md`: phased implementation plan and milestones.

## License

MIT. See `LICENSE`.
