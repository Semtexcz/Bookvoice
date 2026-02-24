"""PyInstaller build definition for the Windows Bookvoice CLI executable."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from PyInstaller.utils.hooks import collect_submodules
from rich._unicode_data._versions import VERSIONS


_PROJECT_ROOT = Path(SPECPATH).resolve().parents[2]
_ENTRYPOINT = _PROJECT_ROOT / "bookvoice" / "__main__.py"
_WINDOWS_THIRD_PARTY_ROOT = _PROJECT_ROOT / "packaging" / "windows" / "third_party"
_WINDOWS_THIRD_PARTY_BIN = _WINDOWS_THIRD_PARTY_ROOT / "bin"
_WINDOWS_THIRD_PARTY_LICENSES = _WINDOWS_THIRD_PARTY_ROOT / "licenses"


def _existing_files(paths: Iterable[Path]) -> list[Path]:
    """Return only paths that currently exist on disk."""

    return [path for path in paths if path.is_file()]


def _bundled_dependency_binaries() -> list[tuple[str, str]]:
    """Collect vendored Windows tool binaries to ship under `bin/`."""

    files = _existing_files(
        [
            _WINDOWS_THIRD_PARTY_BIN / "ffmpeg.exe",
            _WINDOWS_THIRD_PARTY_BIN / "pdftotext.exe",
            _WINDOWS_THIRD_PARTY_BIN / "pdfinfo.exe",
        ]
    )
    return [(str(path), "bin") for path in files]


def _third_party_notice_datas() -> list[tuple[str, str]]:
    """Collect third-party notices/licenses to include in distribution artifacts."""

    files = _existing_files(
        [
            _WINDOWS_THIRD_PARTY_ROOT / "THIRD_PARTY_NOTICES.txt",
            _WINDOWS_THIRD_PARTY_ROOT / "README.md",
            _WINDOWS_THIRD_PARTY_LICENSES / "FFMPEG-LICENSE.txt",
            _WINDOWS_THIRD_PARTY_LICENSES / "POPPLER-LICENSE.txt",
        ]
    )
    return [(str(path), "licenses") for path in files]

hiddenimports = collect_submodules("keyring.backends")
hiddenimports += collect_submodules("rich._unicode_data")
hiddenimports += [
    f"rich._unicode_data.unicode{version.replace('.', '-')}" for version in VERSIONS
]
binaries = _bundled_dependency_binaries()
datas = _third_party_notice_datas()

a = Analysis(
    [str(_ENTRYPOINT)],
    pathex=[str(_PROJECT_ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="bookvoice",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="bookvoice",
)
