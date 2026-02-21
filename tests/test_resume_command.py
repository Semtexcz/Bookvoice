import json
from pathlib import Path

from typer.testing import CliRunner

from bookvoice.cli import app


def test_resume_command_recovers_from_interrupted_run(tmp_path: Path) -> None:
    runner = CliRunner()
    out_dir = tmp_path / "out"
    fixture_pdf = Path("tests/files/zero_to_one.pdf")

    build_result = runner.invoke(app, ["build", str(fixture_pdf), "--out", str(out_dir)])
    assert build_result.exit_code == 0, build_result.output

    manifest_path = next(out_dir.glob("run-*/run_manifest.json"))
    manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))

    raw_text_path = Path(manifest_payload["extra"]["raw_text"])
    raw_before = raw_text_path.read_text(encoding="utf-8")

    Path(manifest_payload["extra"]["translations"]).unlink()
    Path(manifest_payload["extra"]["rewrites"]).unlink()
    Path(manifest_payload["extra"]["audio_parts"]).unlink()
    Path(manifest_payload["merged_audio_path"]).unlink()

    resume_result = runner.invoke(app, ["resume", str(manifest_path)])
    assert resume_result.exit_code == 0, resume_result.output
    assert "Resumed from stage: translate" in resume_result.output

    resumed_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert Path(resumed_payload["extra"]["translations"]).exists()
    assert Path(resumed_payload["extra"]["rewrites"]).exists()
    assert Path(resumed_payload["extra"]["audio_parts"]).exists()
    assert Path(resumed_payload["merged_audio_path"]).exists()
    assert raw_text_path.read_text(encoding="utf-8") == raw_before
