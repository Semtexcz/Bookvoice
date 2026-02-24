# Windows third-party runtime bundle

This folder defines deterministic, pinned external binaries that are packaged with
`bookvoice.exe` for Windows distribution.

## Expected layout

- `bin/ffmpeg.exe`
- `bin/pdftotext.exe`
- `bin/pdfinfo.exe` (recommended for Poppler page-count support)
- `licenses/FFMPEG-LICENSE.txt`
- `licenses/POPPLER-LICENSE.txt`
- `THIRD_PARTY_NOTICES.txt`

## Pinned versions

- ffmpeg: `7.1.1` (Windows x64 static build)
- Poppler: `24.08.0` (Windows x64 build, tools `pdftotext.exe`, `pdfinfo.exe`)

Maintain pinned version updates explicitly in this file, `THIRD_PARTY_NOTICES.txt`,
and release notes.
