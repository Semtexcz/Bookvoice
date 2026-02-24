---
task: TASK-053
status: "done"
priority: P2
type: feature
---

# Bundle `ffmpeg` and `pdftotext` for Windows distribution

Task: TASK-053
Status: done
Priority: P2
Type: feature
Author:
Created: 2026-02-24
Related: TASK-052

## Problem

Even with `bookvoice.exe`, the pipeline still depends on external tools:

- `pdftotext` (Poppler) for PDF text extraction.
- `ffmpeg` for audio packaging/encoding (and potentially postprocessing depending on the runtime path).

To keep the Windows install friction low, these tools should be shipped alongside the executable.

## Definition of Done

- [x] Add a distribution layout that includes `ffmpeg.exe` and `pdftotext.exe` next to `bookvoice.exe` (or under a deterministic `bin/` folder shipped with the app).
- [x] Update runtime invocation logic to resolve these tools in the following deterministic order:
  1) bundled app directory (for example `./bin/ffmpeg.exe`, `./bin/pdftotext.exe`)
  2) system `PATH`
- [x] Ensure missing-tool errors remain stage-scoped and actionable (for example `extract` hints `pdftotext`, `package` hints `ffmpeg`).
- [x] Add a small unit/integration test that validates tool-resolution precedence (bundled path beats PATH) without executing provider calls.
- [x] Add required third-party license notices to the Windows distribution artifacts (Poppler/ffmpeg licensing requirements reviewed and complied with).

## Notes

- Keep bundled binaries versioned and pinned explicitly (document versions used).
- Avoid downloading binaries during CI unless release jobs explicitly allow it; prefer vendoring or a controlled fetch step only for release builds.
