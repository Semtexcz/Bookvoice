---
task: TASK-045
status: "done"
priority: P1
type: fix
---

# Drop-cap and sentence-continuity normalization in PDF text extraction

Task: TASK-045
Status: done
Priority: P1
Type: fix
Author:
Created: 2026-02-23
Related: TASK-014

## Problem

Some books use decorative drop caps at paragraph start (for example `E` rendered separately from `VERY`), and current extraction can split this into separate lines/tokens:

- Extracted: `E` + `VERY MOMENT IN BUSINESS ...`
- Intended text: `EVERY MOMENT IN BUSINESS ...`

This harms readability and can cascade into lower translation/rewrite quality.

The same artifact can also break chunk boundaries in the middle of one sentence:

- Chunk A ends with a sentence fragment (for example `... this question: "What`).
- Chunk B starts with the continuation (for example `important truth ...`).

This creates non-natural translation/rewrite segments and degrades output quality.

## Proposed Solution

Add a deterministic normalization pass after raw extraction and before chapter splitting/chunking:

- merge decorative drop-cap initials into the first word,
- preserve sentence continuity at chunk boundaries when a split occurs mid-sentence.

Suggested detection and merge policy:

- Candidate pattern:
  - A standalone single-letter token line (`^[A-Z]$`) followed by a non-empty line.
  - The next line starts with uppercase letters and has at least 3 alphabetic characters.
  - Optional: there is one blank line between the single-letter line and the next line.
- Safe-merge guards:
  - Do not merge when the next line is all-caps short heading-like text (for example <= 2 words).
  - Do not merge when the single letter is likely a list marker or section marker (surrounded by numbered/bulleted context).
  - Keep behavior deterministic and locale-agnostic for Latin scripts.
- Merge action:
  - Replace the two-line pattern with one line where the single letter is prefixed to the next token (`E` + `VERY` -> `EVERY`).
  - Preserve remaining spacing and punctuation exactly.
- Diagnostics:
  - Track number of applied merges in extraction metadata for debugging (for example `drop_cap_merges_count`).

Suggested sentence-continuity boundary policy:

- Prefer chunk boundaries at sentence terminators (`.`, `!`, `?`, closing quote + terminator).
- If a boundary still lands mid-sentence, apply deterministic carry-over stitching:
  - Detect when previous chunk ends with an unfinished clause or unmatched opening quote.
  - Detect when next chunk starts with lowercase or continuation-like token pattern.
  - Move the minimum continuation text from next chunk to previous chunk until the sentence boundary is complete, while preserving deterministic max-size guardrails.
- Keep chapter titles/headings isolated from body sentence segmentation where possible.
- Diagnostics:
  - Track corrected boundary count in chunk metadata (for example `sentence_boundary_repairs_count`).

## Definition of Done

- [x] Implement drop-cap merge normalization in text cleanup flow with deterministic behavior.
- [x] Implement sentence-continuity boundary repair so chunks are not split in the middle of one sentence when avoidable.
- [x] Add focused unit tests for:
  - positive merge (`E` + `VERY` -> `EVERY`),
  - blank-line-separated merge,
  - heading/list false-positive avoidance,
  - fragment/continuation boundary repair (`"What` + `important truth ...`).
- [x] Add integration fixture/assertion proving the normalized extracted text no longer contains the split initial pattern.
- [x] Add integration fixture/assertion proving sentence continuity in produced chunks for drop-cap opening paragraphs.
- [x] Persist merge/repair counts in artifact metadata and expose them in manifest `extra` for audit visibility.
- [x] Update docs (`README.md` or `docs/ARTIFACTS.md`) with a short note about drop-cap normalization behavior and limitations.

## Notes

- Keep this pass conservative: prefer a missed merge over an incorrect merge.
- If false positives appear in real books, gate with a config switch in a follow-up task.
