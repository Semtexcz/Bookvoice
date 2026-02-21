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
bookvoice translate-only input.pdf
bookvoice tts-only out/run_manifest.json
bookvoice resume out/run_manifest.json
```

The current CLI is a stub and prints planned actions.

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
