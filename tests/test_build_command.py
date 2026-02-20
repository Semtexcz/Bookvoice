from pathlib import Path

from typer.testing import CliRunner

from bookvoice.cli import app


def test_build_command_creates_outputs(tmp_path: Path) -> None:
    runner = CliRunner()
    out_dir = tmp_path / "out"
    fixture_pdf = Path("tests/files/zero_to_one.pdf")

    result = runner.invoke(app, ["build", str(fixture_pdf), "--out", str(out_dir)])

    assert result.exit_code == 0, result.output

    manifests = sorted(out_dir.glob("run-*/run_manifest.json"))
    merged_files = sorted(out_dir.glob("run-*/audio/bookvoice_merged.wav"))
    raw_texts = sorted(out_dir.glob("run-*/text/raw.txt"))
    rewrites = sorted(out_dir.glob("run-*/text/rewrites.json"))

    assert manifests, "manifest should be written"
    assert merged_files, "merged audio should be written"
    assert merged_files[0].stat().st_size > 44, "merged WAV should contain audio data"
    assert raw_texts and raw_texts[0].read_text(encoding="utf-8").strip()
    assert rewrites and rewrites[0].read_text(encoding="utf-8").strip()
