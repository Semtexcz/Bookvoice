# Windows PyInstaller CLI Build

This document defines the maintainer workflow for producing a one-folder
Windows CLI distributable (`bookvoice.exe`) without requiring Poetry on the
target machine.

## Build Prerequisites

- Windows 10 or Windows 11
- Python 3.12+ installed
- Poetry installed
- Repository cloned locally

## Build Command

Run from the repository root:

```bash
poetry install --no-root
poetry run python -m pip install pyinstaller
poetry run pyinstaller --noconfirm --clean packaging/windows/pyinstaller/bookvoice.spec --distpath dist/windows/pyinstaller --workpath build/windows/pyinstaller
```

This produces deterministic paths:

- Executable: `dist/windows/pyinstaller/bookvoice/bookvoice.exe`
- Bundled external tools: `dist/windows/pyinstaller/bookvoice/bin/ffmpeg.exe`, `dist/windows/pyinstaller/bookvoice/bin/pdftotext.exe`
- Third-party notices/licenses: `dist/windows/pyinstaller/bookvoice/licenses/`
- PyInstaller work files: `build/windows/pyinstaller/`

## Bundled Dependency Inputs

Before building distributable artifacts, place pinned binaries and notices under:

- `packaging/windows/third_party/bin/ffmpeg.exe`
- `packaging/windows/third_party/bin/pdftotext.exe`
- `packaging/windows/third_party/bin/pdfinfo.exe` (recommended)
- `packaging/windows/third_party/licenses/FFMPEG-LICENSE.txt`
- `packaging/windows/third_party/licenses/POPPLER-LICENSE.txt`
- `packaging/windows/third_party/THIRD_PARTY_NOTICES.txt`

Pinned versions tracked in this repository:

- ffmpeg `7.1.1`
- Poppler `24.08.0`

## Smoke Check

Validate command discovery without triggering provider API calls:

```bash
dist/windows/pyinstaller/bookvoice/bookvoice.exe --help
dist/windows/pyinstaller/bookvoice/bookvoice.exe build --help
dist/windows/pyinstaller/bookvoice/bookvoice.exe resume --help
dist/windows/pyinstaller/bookvoice/bookvoice.exe translate-only --help
dist/windows/pyinstaller/bookvoice/bookvoice.exe tts-only --help
dist/windows/pyinstaller/bookvoice/bookvoice.exe list-chapters --help
dist/windows/pyinstaller/bookvoice/bookvoice.exe credentials --help
```

## Notes

- The current build uses one-folder mode for easier debugging of bundled files.
- Runtime tool lookup order is deterministic: bundled app folder first (`./bin`), then system `PATH`.
