"""Build command integration tests for output artifacts and cost summary."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from bookvoice.cli import app


def test_build_command_creates_outputs(tmp_path: Path) -> None:
    """Build command should create run artifacts and include deterministic cost fields."""

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

    payload = json.loads(manifests[0].read_text(encoding="utf-8"))
    assert payload["total_llm_cost_usd"] > 0.0
    assert payload["total_tts_cost_usd"] > 0.0
    assert payload["total_cost_usd"] == pytest.approx(
        payload["total_llm_cost_usd"] + payload["total_tts_cost_usd"]
    )

    assert "Cost LLM (USD):" in result.output
    assert "Cost TTS (USD):" in result.output
    assert "Cost Total (USD):" in result.output


def test_build_command_cost_summary_is_deterministic(tmp_path: Path) -> None:
    """Build cost summary should be stable for the same deterministic fixture run."""

    runner = CliRunner()
    out_dir = tmp_path / "out"
    fixture_pdf = Path("tests/files/zero_to_one.pdf")

    first_result = runner.invoke(app, ["build", str(fixture_pdf), "--out", str(out_dir)])
    second_result = runner.invoke(app, ["build", str(fixture_pdf), "--out", str(out_dir)])

    assert first_result.exit_code == 0, first_result.output
    assert second_result.exit_code == 0, second_result.output

    first_cost_lines = [
        line
        for line in first_result.output.splitlines()
        if line.startswith("Cost ") and "(USD):" in line
    ]
    second_cost_lines = [
        line
        for line in second_result.output.splitlines()
        if line.startswith("Cost ") and "(USD):" in line
    ]
    assert first_cost_lines == second_cost_lines

    manifest_path = next(out_dir.glob("run-*/run_manifest.json"))
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected_total = payload["total_llm_cost_usd"] + payload["total_tts_cost_usd"]
    assert payload["total_cost_usd"] == pytest.approx(expected_total)
