# Windows User Guide

This guide is for end users running Bookvoice on Windows from GitHub Release assets.

## Install from GitHub Releases

Bookvoice Windows releases provide two distribution types:

- Portable ZIP: `bookvoice-windows-x64-vX.Y.Z.zip`
- Installer: `bookvoice-windows-x64-vX.Y.Z-setup.exe`

Download from this repository's GitHub `Releases` page.

### Option A: Installer (`-setup.exe`)

1. Run the installer executable.
2. Complete the setup wizard.
3. Launch `Bookvoice CLI` from the Start Menu.

Default install location:

- `%LocalAppData%\Programs\Bookvoice`

### Option B: Portable ZIP (`.zip`)

1. Extract the ZIP to a folder you control, for example:
   - `C:\Tools\Bookvoice\`
2. Run `bookvoice.exe` from the extracted folder.

## Run basic commands

From PowerShell in the install/extract folder:

```powershell
.\bookvoice.exe --help
.\bookvoice.exe list-chapters "C:\path\to\book.pdf"
```

## Output location and `--out`

Bookvoice writes run artifacts to the output directory:

- If `--out` is provided, that exact path is used.
- If `--out` is not provided, Bookvoice defaults to `out` relative to your current working directory.

Examples:

```powershell
.\bookvoice.exe build "C:\Books\input.pdf" --out "C:\BookvoiceOutput"
.\bookvoice.exe chapters-only "C:\Books\input.pdf" --out "D:\Runs\bookvoice"
```

Recommendation:

- Always pass `--out` explicitly on Windows to keep artifacts in a known writable directory.

## API key setup (secure vs environment variable)

Bookvoice supports two API key paths:

### Recommended: secure credential storage (keyring)

```powershell
.\bookvoice.exe credentials --set-api-key
```

Then verify:

```powershell
.\bookvoice.exe credentials
```

This stores your key via the system keyring backend instead of keeping it in shell history.

### Alternative: environment variable

Set the API key in your current PowerShell session:

```powershell
$env:OPENAI_API_KEY="sk-..."
.\bookvoice.exe build "C:\Books\input.pdf" --out "C:\BookvoiceOutput"
```

For persistent setup, define `OPENAI_API_KEY` in Windows Environment Variables.

## Troubleshooting

### `pdftotext` missing / not found

Typical error text:

- "The `pdftotext` command is required but was not found."

What to know:

- Windows release assets bundle Poppler tools (`pdftotext.exe`, `pdfinfo.exe`) in `bin\`.
- Runtime lookup prefers bundled tools first, then `PATH`.
- If `pdftotext` is unavailable, Bookvoice falls back to `pypdf` extraction.

Actions:

1. If using ZIP, confirm `bin\pdftotext.exe` exists next to `bookvoice.exe`.
2. If using installer, repair or reinstall Bookvoice.
3. Retry with a text-based PDF; image-only/scanned PDFs are not supported.

### `ffmpeg` missing / not found

Typical packaging-stage error text:

- "Packaging tool `ffmpeg` is not available on PATH."

What to know:

- Windows release assets bundle `ffmpeg.exe` in `bin\`.
- Packaging (`--package-mode aac|mp3|both`) requires ffmpeg.

Actions:

1. Confirm `bin\ffmpeg.exe` exists in the Bookvoice app folder.
2. Reinstall/replace the release files if missing.
3. If you only need merged WAV output, run with:
   - `--package-mode none`

### Encoding / codec errors during packaging

Typical error text:

- `ffmpeg packaging failed for ...`

What to know:

- `m4a` packaging uses codec `aac`.
- `mp3` packaging uses codec `libmp3lame`.

Actions:

1. Retry with one target format first:
   - `--package-mode aac` or `--package-mode mp3`
2. If one format fails, use the other or disable packaging:
   - `--package-mode none`
3. Keep the bundled ffmpeg from the official release package; do not mix random binaries.

### Antivirus false positives

Some antivirus tools may flag freshly downloaded unsigned CLI binaries.

Recommended mitigations:

1. Download only from official GitHub Releases.
2. Verify filename/version match the published release notes.
3. If blocked, restore/quarantine exception for the Bookvoice install folder.
4. Prefer the installer build when enterprise endpoint policy is strict.
5. If needed, add allow-rules for:
   - `bookvoice.exe`
   - `bin\ffmpeg.exe`
   - `bin\pdftotext.exe`
