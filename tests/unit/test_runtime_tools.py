"""Unit tests for deterministic runtime executable resolution."""

from __future__ import annotations

from pathlib import Path

from pytest import MonkeyPatch

from bookvoice import runtime_tools


def test_resolve_executable_prefers_bundled_bin_over_path(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Bundled `bin` executable should take precedence over PATH discovery."""

    bundled_bin = tmp_path / "bin"
    bundled_bin.mkdir(parents=True, exist_ok=True)
    bundled_tool = bundled_bin / "ffmpeg"
    bundled_tool.write_text("stub", encoding="utf-8")
    monkeypatch.setattr(runtime_tools, "_app_root", lambda: tmp_path)
    monkeypatch.setattr(runtime_tools.shutil, "which", lambda _: "/usr/bin/ffmpeg")

    resolved = runtime_tools.resolve_executable("ffmpeg")

    assert resolved == str(bundled_tool)


def test_resolve_executable_falls_back_to_path_when_not_bundled(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    """PATH lookup should be used when no bundled executable is present."""

    monkeypatch.setattr(runtime_tools, "_app_root", lambda: tmp_path)
    monkeypatch.setattr(runtime_tools.shutil, "which", lambda _: "/usr/bin/pdftotext")

    resolved = runtime_tools.resolve_executable("pdftotext")

    assert resolved == "/usr/bin/pdftotext"
