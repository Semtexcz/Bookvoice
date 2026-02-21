# Artifacts Reference

This document lists filesystem artifacts produced by `bookvoice build`.
`bookvoice chapters-only` produces a deterministic subset and does not synthesize audio.

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

- Raw extracted PDF text before cleanup.

### `text/clean.txt`

- Deterministically cleaned and normalized text.

### `text/chapters.json`

- Chapter list after split stage.
- Includes extraction metadata and normalized structure used by planner.

Minimal shape:

```json
{
  "chapters": [
    { "index": 1, "title": "Chapter 1", "text": "..." }
  ],
  "metadata": {
    "source": "pdf_outline",
    "fallback_reason": "",
    "chapter_scope": {
      "chapter_scope_mode": "all",
      "chapter_scope_label": "all"
    },
    "normalized_structure": [
      {
        "order_index": 1,
        "chapter_index": 1,
        "chapter_title": "Chapter 1",
        "subchapter_index": null,
        "subchapter_title": null,
        "text": "...",
        "char_start": 0,
        "char_end": 1200,
        "source": "pdf_outline"
      }
    ]
  }
}
```

### `text/chunks.json`

- Chunk list derived from planner or chunker fallback.

Minimal shape:

```json
{
  "chunks": [
    {
      "chapter_index": 1,
      "chunk_index": 0,
      "text": "...",
      "char_start": 0,
      "char_end": 1800,
      "part_index": 1,
      "part_title": "Chapter 1",
      "part_id": "001_01_chapter-1",
      "source_order_indices": [1],
      "boundary_strategy": "sentence_complete"
    }
  ],
  "metadata": {
    "chapter_scope": {
      "chapter_scope_mode": "all",
      "chapter_scope_label": "all"
    },
    "planner": {
      "strategy": "text_budget_segment_planner",
      "budget_chars": 1800,
      "budget_ceiling_chars": 9300,
      "segment_count": 1,
      "source_structure_unit_count": 1,
      "source_structure_order_indices": [1]
    }
  }
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
      "model": "gpt-4.1-mini"
    }
  ],
  "metadata": {
    "chapter_scope": {
      "chapter_scope_mode": "all",
      "chapter_scope_label": "all"
    },
    "provider": "openai",
    "model": "gpt-4.1-mini"
  }
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
        "model": "gpt-4.1-mini"
      },
      "rewritten_text": "...",
      "provider": "openai",
      "model": "gpt-4.1-mini"
    }
  ],
  "metadata": {
    "chapter_scope": {
      "chapter_scope_mode": "all",
      "chapter_scope_label": "all"
    },
    "provider": "openai",
    "model": "gpt-4.1-mini",
    "rewrite_bypass": "false"
  }
}
```

## Audio Artifacts

### `audio/chunks/<chapter>_<part>_<title-slug>.wav`

- Per-part synthesized WAV files (`001_01_chapter-title.wav`).

### `audio/parts.json`

- Metadata for synthesized chunk-level audio parts.

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
      "filename": "001_01_chapter-1.wav",
      "path": "out/run-.../audio/chunks/001_01_chapter-1.wav",
      "duration_seconds": 1.23,
      "provider": "openai",
      "model": "gpt-4o-mini-tts",
      "voice": "echo"
    }
  ],
  "metadata": {
    "chapter_scope": {
      "chapter_scope_mode": "all",
      "chapter_scope_label": "all"
    },
    "provider": "openai",
    "model": "gpt-4o-mini-tts",
    "voice": "echo",
    "chapter_part_map": [
      {
        "chapter_index": 1,
        "part_index": 1,
        "part_id": "001_01_chapter-1",
        "source_order_indices": [1],
        "filename": "001_01_chapter-1.wav"
      }
    ]
  }
}
```

### `audio/bookvoice_merged.wav`

- Final merged audiobook output for the run.
- For chapter-scoped runs, the filename remains deterministic and scope metadata is stored in manifest `extra`.

## Manifest

### `run_manifest.json`

- Deterministic run record with config identity, costs, output paths, and runtime metadata.

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
  "total_cost_usd": 0.0,
  "extra": {
    "run_root": "out/run-...",
    "raw_text": "out/run-.../text/raw.txt",
    "clean_text": "out/run-.../text/clean.txt",
    "chapters": "out/run-.../text/chapters.json",
    "chunks": "out/run-.../text/chunks.json",
    "translations": "out/run-.../text/translations.json",
    "rewrites": "out/run-.../text/rewrites.json",
    "audio_parts": "out/run-.../audio/parts.json",
    "manifest_path": "out/run-.../run_manifest.json",
    "provider_translator": "openai",
    "provider_rewriter": "openai",
    "provider_tts": "openai",
    "model_translate": "gpt-4.1-mini",
    "model_rewrite": "gpt-4.1-mini",
    "model_tts": "gpt-4o-mini-tts",
    "tts_voice": "echo",
    "chapter_scope_mode": "all",
    "chapter_scope_label": "all"
  }
}
```

## Chapters-Only Output

`bookvoice chapters-only` writes:

- `text/raw.txt`
- `text/clean.txt`
- `text/chapters.json`
- `run_manifest.json`

It does not write `chunks`, `translations`, `rewrites`, or audio artifacts.
