# bookvoice

`bookvoice` is a Python project scaffold for a deterministic, pay-as-you-go pipeline that converts text-based PDF books into Czech audiobook outputs.

What it is not:

- It is not a DRM bypass tool.
- It is not intended for copyrighted material without proper rights.
- It does not ship real provider integrations yet.

## Design Principles

- No subscriptions: provider integrations are intended to be pay-per-use.
- Deterministic pipeline: reproducible outputs from explicit config + input artifacts.
- Chapter-level reproducibility: each stage should be resumable and auditable.
- Minimal abstraction: straightforward modules with clear responsibilities.

## Pipeline Overview

```text
PDF Input
  |
  v
[Extract Text] --> [Clean/Normalize] --> [Split Chapters] --> [Chunk]
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

Stage summary:

- Extract text: pull raw text (and optionally page-wise text) from a PDF backend.
- Clean/normalize: apply deterministic text rules.
- Split chapters/chunk: segment text for translation and synthesis boundaries.
- Translate/rewrite: prepare Czech narration text.
- TTS/postprocess/merge: synthesize, polish, and combine audio outputs.
- Manifest: persist run metadata, costs, and reproducibility details.

## Future Work (Planned Integrations)

- PDF text extraction backends (for scanned and text-native PDFs).
- LLM translation providers.
- TTS providers for Czech voices.
- `ffmpeg` integration for robust audio postprocessing/merging.

These are planned and intentionally not implemented in this scaffold.

## CLI Examples

```bash
bookvoice build input.pdf --out out/
bookvoice build input.pdf --out out/ --interactive-provider-setup
bookvoice build input.pdf --out out/ --model-translate gpt-4.1-mini --model-rewrite gpt-4.1-mini --model-tts gpt-4o-mini-tts
bookvoice build input.pdf --out out/ --prompt-api-key
bookvoice credentials
bookvoice credentials --set-api-key
bookvoice credentials --clear-api-key
bookvoice build input.pdf --out out/ --chapters 5
bookvoice build input.pdf --out out/ --chapters 1,3,7
bookvoice build input.pdf --out out/ --chapters 2-4
bookvoice build input.pdf --out out/ --chapters 1,3-5
bookvoice chapters-only input.pdf --out out/
bookvoice chapters-only input.pdf --out out/ --chapters 1-3
bookvoice list-chapters input.pdf
bookvoice list-chapters --chapters-artifact out/run-*/text/chapters.json
bookvoice translate-only input.pdf
bookvoice tts-only out/run_manifest.json
bookvoice resume out/run_manifest.json
```

CLI currently supports full `build` and basic manifest-driven `resume` flows.
Use `chapters-only` to run only extract/clean/split and inspect chapter boundaries quickly.
The command writes `text/raw.txt`, `text/clean.txt`, `text/chapters.json`, and `run_manifest.json`,
including chapter source metadata (`pdf_outline` or `text_heuristic`) and fallback reason.
Use `--chapters` on `build` and `chapters-only` to select a subset of 1-based chapter indices.
Accepted syntax: single (`5`), comma list (`1,3,7`), closed range (`2-4`), and mixed (`1,3-5`).
Selection is validated (malformed syntax, overlap/duplicates, and out-of-bound indices fail fast).
Runs with selected scope persist chapter-scope metadata in artifacts and manifest, and `resume` keeps
the same scope for regenerated artifacts.
Use `list-chapters` to print compact `index. title` output either directly from a PDF
via extract/clean/split flow or from an existing `text/chapters.json` artifact.
`translate-only` and `tts-only` remain placeholders.
Provider runtime values resolve with deterministic precedence:
`CLI explicit input > secure credential storage > environment > defaults`.
The secure credential path is managed through `bookvoice credentials` and is used
automatically by `build` when an API key is not explicitly provided.
For hidden API-key entry during `build`, use `--prompt-api-key` or
`--interactive-provider-setup`.

For faster and cheaper integration testing, first inspect chapters with `list-chapters` and then run
`build --chapters <small-scope>` (for example `--chapters 1` or `--chapters 1-2`).

## Troubleshooting

- `build failed at stage extract`: ensure the input PDF path exists and the `pdftotext` tool is installed.
- `resume failed at stage resume-manifest`: check that the manifest file exists and contains valid JSON.
- `resume failed at stage resume-artifacts`: one or more artifact JSON files are corrupted; delete the broken artifact and rerun `bookvoice resume`.
- `list-chapters failed at stage chapters-artifact`: verify `--chapters-artifact` points to a valid `text/chapters.json` file.
- `build failed at stage tts` or `merge`: verify output directories are writable and intermediate audio files are present.

## Development

### Local setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Quality checks (placeholders)

```bash
# Planned tools (future)
# ruff check .
# mypy bookvoice
# pytest
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
