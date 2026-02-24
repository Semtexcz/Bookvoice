"""Deterministic runtime executable resolution helpers.

Responsibilities:
- Resolve external executable paths with deterministic bundled-first precedence.
- Support frozen app layouts (for example PyInstaller) and local development runs.
"""

from __future__ import annotations

from pathlib import Path
import shutil
import sys


def resolve_executable(command_name: str) -> str:
    """Resolve an executable with bundled-first precedence, then PATH.

    Resolution order:
    1. Bundled app directories (`./bin/<tool>` then `./<tool>` from app root).
    2. System `PATH`.
    3. Raw command name (allowing subprocess to raise a native missing-binary error).
    """

    normalized = command_name.strip()
    if not normalized:
        return command_name

    for candidate in _bundled_candidates(normalized):
        if candidate.is_file():
            return str(candidate)

    resolved_path = shutil.which(normalized)
    if resolved_path is not None:
        return resolved_path

    return normalized


def _bundled_candidates(command_name: str) -> list[Path]:
    """Return deterministic bundled candidate paths for one executable name."""

    app_root = _app_root()
    names = _candidate_names(command_name)
    candidates: list[Path] = []
    for name in names:
        candidates.append(app_root / "bin" / name)
        candidates.append(app_root / name)
    return candidates


def _candidate_names(command_name: str) -> tuple[str, ...]:
    """Return command name variants including Windows `.exe` fallback."""

    lowered = command_name.lower()
    if lowered.endswith(".exe"):
        return (command_name,)
    return (command_name, f"{command_name}.exe")


def _app_root() -> Path:
    """Resolve runtime application root for frozen and non-frozen execution."""

    frozen = bool(getattr(sys, "frozen", False))
    if frozen:
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]
