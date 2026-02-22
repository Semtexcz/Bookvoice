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
- Structure-aware segment planning with chapter-local merging and paragraph-preferred boundaries (`chunk_size_chars` default `1800`, planner hard ceiling `9300` chars).
- Resumable artifact-driven pipeline with run manifest and cost summary.
- Chapter listing and chapter-scope processing (`--chapters`).
- Secure API-key storage via `keyring` (`bookvoice credentials`).

Still intentionally limited:

- Packaging and metadata tagging rely on local `ffmpeg` runtime and codec/container support.

## Chunk Boundary Guarantees

- Fallback chapter chunking now targets sentence-complete boundaries and prefers `.` before `!`/`?`.
- If no boundary exists near the target size, the chunker extends forward to the next sentence boundary within a bounded safety margin.
- If no sentence boundary exists within that margin (for example very long punctuation-free text), the chunker performs a deterministic forced split and marks the chunk with `boundary_strategy = "forced_split_no_sentence_boundary"`.

Current limitation:

- Structure-driven segment planning (`TextBudgetSegmentPlanner`) is paragraph-first; sentence-boundary enforcement applies to chunker fallback path.

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
                                      [Optional Chapter Packaging: M4A/MP3]
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
poetry run bookvoice build --config bookvoice.yaml
```

Common options:

- `--config`: load command defaults from YAML (`input_pdf` and `output_dir` can come from file).
- `--chapters`: process only selected 1-based chapters (`5`, `1,3,7`, `2-4`, `1,3-5`).
- `--model-translate`, `--model-rewrite`, `--model-tts`, `--tts-voice`.
- `--provider-translator`, `--provider-rewriter`, `--provider-tts` (currently `openai`).
- `--prompt-api-key`: hidden API-key prompt for this run.
- `--interactive-provider-setup`: prompts provider/model/voice values.
- `--store-api-key/--no-store-api-key`.
- `--rewrite-bypass/--no-rewrite-bypass`.
- `--package-mode`: `none`, `aac`, `mp3`, `both`.
- `--package-chapter-numbering`: `source` or `sequential`.
- `--package-keep-merged/--no-package-keep-merged`.

Runtime feedback during `build`:

- Deterministic progress lines per stage (`extract`, `clean`, `split`, `chunk`, `translate`, `rewrite`, `tts`, `merge`, `package`, `manifest`).
- Structured phase logs (`[phase]`) for stage start/complete/failure.
- Output is concise and CI-friendly, with no credential material in logs.

Example output excerpt:

```text
[progress] command=build | 1/10 stage=extract
[phase] level=INFO stage=extract event=start
[phase] level=INFO stage=extract event=complete
...
[progress] command=build / 10/10 stage=manifest
[phase] level=INFO stage=manifest event=complete
```

### Chapters-only (fast boundary inspection)

```bash
poetry run bookvoice chapters-only input.pdf --out out/
poetry run bookvoice chapters-only input.pdf --out out/ --chapters 1-3
```

### Translate-only (through translation artifacts)

```bash
poetry run bookvoice translate-only input.pdf --out out/
poetry run bookvoice translate-only input.pdf --out out/ --chapters 2-4
poetry run bookvoice translate-only --config bookvoice.yaml
```

Behavior:

- Runs stages `extract`, `clean`, `split`, `chunk`, `translate`, `manifest`.
- Persists deterministic text artifacts (`raw`, `clean`, `chapters`, `chunks`, `translations`) and `run_manifest.json`.
- Does not execute `rewrite`, `tts`, or `merge`.
- Supports the same provider/model/runtime precedence and secure credential flow as `build`.

### TTS-only (from manifest + text artifacts)

```bash
poetry run bookvoice tts-only out/run-<id>/run_manifest.json
```

Behavior:

- Runs only `tts`, `merge`, `package`, and `manifest`.
- Requires valid `text/rewrites.json` and `text/chunks.json` artifacts from a prior run.
- Preserves deterministic part naming and artifact schemas used by full `build`/`resume`.
- Reapplies deterministic merged-output postprocessing (silence trim + peak normalization)
  and WAV metadata tagging on every replay.
- Does not execute upstream text stages (`extract` through `rewrite`).

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
- TTS voice: `echo`

Resolution precedence:

- Runtime values (`provider_*`, `model_*`, `tts_voice`, `api_key`, `rewrite_bypass`):
  `CLI explicit input > secure credential storage > environment > config/defaults`
- Command fields (`input_pdf`, `output_dir`, `chapter_selection`):
  explicit CLI option/argument overrides `--config` values.

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

`ConfigLoader.from_yaml` supported keys:

- `input_pdf` (required)
- `output_dir` (required)
- `language`
- `provider_translator`
- `provider_rewriter`
- `provider_tts`
- `model_translate`
- `model_rewrite`
- `model_tts`
- `tts_voice`
- `rewrite_bypass` (`true`/`false`, `1`/`0`, `yes`/`no`)
- `api_key`
- `chunk_size_chars` (positive integer)
- `chapter_selection`
- `resume` (`true`/`false`, `1`/`0`, `yes`/`no`)
- `extra` (string-to-string mapping)

Example `bookvoice.yaml`:

```yaml
input_pdf: tests/files/zero_to_one.pdf
output_dir: out
provider_translator: openai
provider_rewriter: openai
provider_tts: openai
model_translate: gpt-4.1-mini
model_rewrite: gpt-4.1-mini
model_tts: gpt-4o-mini-tts
tts_voice: echo
rewrite_bypass: false
chapter_selection: 1-3
```

`ConfigLoader.from_env` supported keys:

- `BOOKVOICE_INPUT_PDF` (required)
- `BOOKVOICE_OUTPUT_DIR`
- `BOOKVOICE_LANGUAGE`
- `BOOKVOICE_CHUNK_SIZE_CHARS`
- `BOOKVOICE_CHAPTER_SELECTION`
- `BOOKVOICE_RESUME`
- `BOOKVOICE_PROVIDER_TRANSLATOR`
- `BOOKVOICE_PROVIDER_REWRITER`
- `BOOKVOICE_PROVIDER_TTS`
- `BOOKVOICE_MODEL_TRANSLATE`
- `BOOKVOICE_MODEL_REWRITE`
- `BOOKVOICE_MODEL_TTS`
- `BOOKVOICE_TTS_VOICE`
- `BOOKVOICE_REWRITE_BYPASS`
- `OPENAI_API_KEY`

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
- `out/run-<hash>/audio/package/chapter_<NNN>_<title-slug>.m4a|.mp3` (when enabled)
- `out/run-<hash>/audio/packaged.json`
- `out/run-<hash>/run_manifest.json`

`audio/parts.json` includes deterministic `chapter_index`, `part_index`, `part_id`,
final emitted `filename`, source `source_order_indices`, and per-part
`provider`/`model`/`voice` metadata.
`audio/bookvoice_merged*.wav` is postprocessed deterministically in-place:
leading/trailing silence trimming followed by peak normalization to `95%`.
Merged WAV outputs include RIFF `LIST/INFO` tags: `INAM` (title), `ISBJ`
(chapter/part context), and `ICMT` (source identifier).
When packaging is enabled, chapter-split AAC (`.m4a`) and/or MP3 outputs are emitted
under `audio/package/` with deterministic `chapter_<NNN>_<slug>.<ext>` naming.
Chapter numbering can follow source indices or sequential ordering.
Packaged chapter metadata tags are written deterministically for both formats:
- Canonical payload: `title`, `album`, `track`, `chapter_context`, `source_identifier`.
- MP3 (ID3): `title`, `album`, `track`, `comment` (chapter context), `publisher` (source/run).
- M4A (MP4 atoms): `title`, `album`, `track`, `description` (chapter context), `comment` (source/run).
Player support for `description`/`publisher` may vary by platform; `title`/`album`/`track` remain primary.
`run_manifest.json` `extra` includes compact chapter/part mapping and referenced
structure indices for resume/rebuild stability, packaging intent metadata,
packaged-tag summary metadata (`packaging_tags_*`), and packaged artifact references.
`text/chunks.json` includes planner metadata under `metadata.planner` and chunk-level
`boundary_strategy` metadata.

Filename examples:

- `001_01_chapter-one.wav`
- `007_03_cesky-nazev-uvod.wav` (non-ASCII title normalized to ASCII slug)

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
