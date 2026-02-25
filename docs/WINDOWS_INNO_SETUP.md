# Windows Inno Setup Installer

This document defines the maintainer workflow for packaging a Windows installer
wizard (`.exe`) for Bookvoice.

## Prerequisites

- Windows 10 or Windows 11
- Built PyInstaller one-folder output at `dist/windows/pyinstaller/bookvoice/`
- Inno Setup 6 installed (`ISCC.exe` available)

Build the PyInstaller output first (see `docs/WINDOWS_PYINSTALLER.md`).

## Build Command

Run from the repository root in `cmd.exe` or PowerShell:

```powershell
ISCC.exe packaging\windows\inno\bookvoice.iss /DMyAppVersion=X.Y.Z /DSourceDir=dist\windows\pyinstaller\bookvoice /DOutputDir=dist\windows\installer
```

Resulting artifact path:

- `dist/windows/installer/bookvoice-windows-x64-vX.Y.Z-setup.exe`

The script defaults to:

- Per-user install location: `%LocalAppData%\Programs\Bookvoice`
- Non-admin install (`PrivilegesRequired=lowest`)
- Stable app identity for upgrades (`AppId`)
- Recursive inclusion of the PyInstaller tree, including bundled tools and
  third-party notices/licenses

## Installer Behavior

- Creates Start Menu entries:
  - `Bookvoice Command Line` (opens `cmd` with `/K` in the install directory and runs `bookvoice.exe --help`)
  - `Uninstall Bookvoice`
- Optionally creates a desktop shortcut (`Bookvoice Command Line`)
- Includes an `Add Bookvoice to the user PATH` task (enabled by default)
- Registers a standard uninstaller entry in Windows Apps/Programs

## Validation

After installing, run a local smoke check:

```powershell
"$env:LOCALAPPDATA\Programs\Bookvoice\bookvoice.exe" --help
"$env:LOCALAPPDATA\Programs\Bookvoice\bookvoice.exe" list-chapters "C:\path\to\book.pdf"
```

The `list-chapters` command is local-only and should not require provider API
calls.
