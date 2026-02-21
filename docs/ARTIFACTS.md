# Artifacts Reference

This document lists filesystem artifacts produced by `bookvoice build`.
The `bookvoice chapters-only` command produces a deterministic subset:
`text/raw.txt`, `text/clean.txt`, `text/chapters.json`, and `run_manifest.json`.

## Run Root

Each run is stored under:

- `<out>/run-<config_hash_prefix>/`

Example layout:

```text
out/
  run-1a2b3c4d5e6f/
    run_manifest.json
    text/
      raw.txt
      clean.txt
      chapters.json
      chunks.json
      translations.json
      rewrites.json
    audio/
      parts.json
      bookvoice_merged.wav
      chunks/
        001_01_chapter-1.wav
        001_02_chapter-1.wav
        ...
```

## Text Artifacts

### `text/raw.txt`

- Raw extracted PDF text before cleaning.

### `text/clean.txt`

- Deterministically cleaned/normalized text.

### `text/chapters.json`

- Chapter list after split stage.
- Includes extraction metadata for outline-vs-fallback diagnostics.

Minimal shape:

```json
{
  "chapters": [
    { "index": 1, "title": "Chapter 1", "text": "..." }
  ],
  "metadata": {
    "source": "pdf_outline",
    "fallback_reason": ""
  }
}
```

### `text/chunks.json`

- Chunk list derived from chapters.

Minimal shape:

```json
{
  "chunks": [
    {
      "chapter_index": 1,
      "chunk_index": 0,
      "text": "...",
      "char_start": 0,
      "char_end": 1800
    }
  ]
}
```

### `text/translations.json`

- Translation output per chunk.

Minimal shape:

```json
{
  "translations": [
    {
      "chunk": {
        "chapter_index": 1,
        "chunk_index": 0,
        "text": "...",
        "char_start": 0,
        "char_end": 1800
      },
      "translated_text": "...",
      "provider": "openai",
      "model": "stub-model"
    }
  ]
}
```

### `text/rewrites.json`

- Audio-oriented rewrite output per translated chunk.

Minimal shape:

```json
{
  "rewrites": [
    {
      "translation": {
        "chunk": {
          "chapter_index": 1,
          "chunk_index": 0,
          "text": "...",
          "char_start": 0,
          "char_end": 1800
        },
        "translated_text": "...",
        "provider": "openai",
        "model": "stub-model"
      },
      "rewritten_text": "...",
      "provider": "stub",
      "model": "stub-model"
    }
  ]
}
```

## Audio Artifacts

### `audio/chunks/<chapter>_<part>_<title-slug>.wav`

- Per-part synthesized WAV files (`001_01_chapter-title.wav`).

### `audio/parts.json`

- Metadata for chunk-level audio parts.

Minimal shape:

```json
{
  "audio_parts": [
    {
      "chapter_index": 1,
      "chunk_index": 0,
      "part_index": 1,
      "part_title": "Chapter 1",
      "part_id": "001_01_chapter-1",
      "source_order_indices": [1],
      "path": "out/run-.../audio/chunks/001_01_chapter-1.wav",
      "duration_seconds": 1.23,
      "provider": "openai",
      "model": "gpt-4o-mini-tts",
      "voice": "alloy"
    }
  ]
}
```

### `audio/bookvoice_merged.wav`

- Final merged audiobook output for the run.

## Manifest

### `run_manifest.json`

- Deterministic run record with config identity and key output paths.

Minimal shape:

```json
{
  "run_id": "run-1a2b3c4d5e6f",
  "config_hash": "1a2b3c...",
  "book": {
    "source_pdf": "tests/files/zero_to_one.pdf",
    "title": "zero_to_one",
    "author": null,
    "language": "cs"
  },
  "merged_audio_path": "out/run-.../audio/bookvoice_merged.wav",
  "total_llm_cost_usd": 0.0,
  "total_tts_cost_usd": 0.0,
  "extra": {
    "run_root": "out/run-...",
    "raw_text": "out/run-.../text/raw.txt",
    "clean_text": "out/run-.../text/clean.txt",
    "chapters": "out/run-.../text/chapters.json",
    "chunks": "out/run-.../text/chunks.json",
    "translations": "out/run-.../text/translations.json",
    "rewrites": "out/run-.../text/rewrites.json",
    "audio_parts": "out/run-.../audio/parts.json",
    "manifest_path": "out/run-.../run_manifest.json"
  }
}
```
