"""Integration tests for the CLI chapter-only mode."""

import json
from pathlib import Path

from typer.testing import CliRunner

from bookvoice.cli import app


def test_chapters_only_command_writes_split_artifacts_only(tmp_path: Path) -> None:
    """Chapter-only command should write extract/split artifacts without downstream outputs."""

    runner = CliRunner()
    out_dir = tmp_path / "out"
    fixture_pdf = Path("tests/files/canonical_synthetic_fixture.pdf")

    result = runner.invoke(app, ["chapters-only", str(fixture_pdf), "--out", str(out_dir)])

    assert result.exit_code == 0, result.output
    assert "Chapter source:" in result.output

    manifest_path = next(out_dir.glob("run-*/run_manifest.json"))
    manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    run_root = Path(manifest_payload["extra"]["run_root"])

    assert (run_root / "text/raw.txt").exists()
    assert (run_root / "text/clean.txt").exists()
    assert (run_root / "text/chapters.json").exists()

    chapters_payload = json.loads((run_root / "text/chapters.json").read_text(encoding="utf-8"))
    assert chapters_payload["metadata"]["source"] in {"pdf_outline", "text_heuristic"}
    assert isinstance(chapters_payload["metadata"]["fallback_reason"], str)
    assert isinstance(chapters_payload["metadata"]["normalized_structure"], list)
    assert chapters_payload["metadata"]["normalized_structure"]

    assert not (run_root / "text/chunks.json").exists()
    assert not (run_root / "text/translations.json").exists()
    assert not (run_root / "text/rewrites.json").exists()
    assert not (run_root / "audio/parts.json").exists()
    assert not (run_root / "audio/bookvoice_merged.wav").exists()
