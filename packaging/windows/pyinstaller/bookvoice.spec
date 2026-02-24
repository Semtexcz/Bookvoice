"""PyInstaller build definition for the Windows Bookvoice CLI executable."""

from __future__ import annotations

from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules
from rich._unicode_data._versions import VERSIONS


_PROJECT_ROOT = Path(SPECPATH).resolve().parents[2]
_ENTRYPOINT = _PROJECT_ROOT / "bookvoice" / "__main__.py"

hiddenimports = collect_submodules("keyring.backends")
hiddenimports += collect_submodules("rich._unicode_data")
hiddenimports += [
    f"rich._unicode_data.unicode{version.replace('.', '-')}" for version in VERSIONS
]

a = Analysis(
    [str(_ENTRYPOINT)],
    pathex=[str(_PROJECT_ROOT)],
    binaries=[],
    datas=[],
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
