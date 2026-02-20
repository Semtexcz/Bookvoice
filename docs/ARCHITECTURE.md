# Architecture

## Core Data Model

Bookvoice is centered around typed immutable artifacts where practical:

- `BookMeta`: top-level metadata about the input book and run identity.
- `Chapter`: chapter-level unit produced after splitting.
- `Chunk`: bounded text segment for translation and synthesis workflows.
- `TranslationResult`: translation output per chunk.
- `RewriteResult`: spoken-style rewrite output per chunk.
- `AudioPart`: generated audio artifact metadata.
- `RunManifest`: deterministic run record tying config, artifacts, and usage data.

These models live in `bookvoice/models/datatypes.py` and are imported across modules.

## Orchestration Notes

Pipeline stages are designed as explicit steps:
1. Extract
2. Clean
3. Split chapters
4. Chunk
5. Translate
6. Rewrite for audio
7. TTS
8. Postprocess
9. Merge
10. Write manifest

Caching strategy (planned):
- Hash key format: `sha256(stage_name + normalized_input + provider_id + config_slice)`.
- Cache granularity: chunk-level for translation/rewrite/TTS artifacts.
- Cache storage: deterministic path layout under the artifact store root.

Run reproducibility (planned):
- Persist complete `RunManifest` per run.
- Include a canonical config hash in the manifest.
- Ensure stage outputs are content-addressed and resumable.

## Error Handling and Retry Strategy (Planned)

- Fail-fast on deterministic preprocessing errors (invalid PDF path, unreadable artifacts).
- Retry external-provider failures with bounded exponential backoff.
- Record retry attempts and terminal failures in telemetry.
- Keep partial artifacts to allow resume from the last successful stage.
- Distinguish recoverable vs non-recoverable errors via explicit exception categories.
