"""Build command integration tests for output artifacts and cost summary."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from bookvoice.cli import app


def _parse_wav_info_tags(wav_bytes: bytes) -> dict[str, str]:
    """Parse RIFF `LIST/INFO` tags from WAV bytes for integration assertions."""

    if len(wav_bytes) < 12 or wav_bytes[:4] != b"RIFF" or wav_bytes[8:12] != b"WAVE":
        return {}

    tags: dict[str, str] = {}
    payload = wav_bytes[12:]
    offset = 0
    while offset + 8 <= len(payload):
        chunk_id = payload[offset : offset + 4]
        chunk_size = int.from_bytes(payload[offset + 4 : offset + 8], "little")
        content_start = offset + 8
        content_end = content_start + chunk_size
        if content_end > len(payload):
            break
        content = payload[content_start:content_end]
        if chunk_id == b"LIST" and content.startswith(b"INFO"):
            info = content[4:]
            info_offset = 0
            while info_offset + 8 <= len(info):
                key = info[info_offset : info_offset + 4].decode("ascii", errors="ignore")
                value_size = int.from_bytes(info[info_offset + 4 : info_offset + 8], "little")
                value_start = info_offset + 8
                value_end = value_start + value_size
                if value_end > len(info):
                    break
                raw_value = info[value_start:value_end]
                tags[key] = raw_value.rstrip(b"\x00").decode("utf-8", errors="ignore")
                info_offset = value_end + (value_size % 2)
        offset = content_end + (chunk_size % 2)
    return tags


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
    tags = _parse_wav_info_tags(merged_files[0].read_bytes())
    assert tags["INAM"] == fixture_pdf.stem
    assert "scope=all" in tags["ISBJ"]
    assert "source=" in tags["ICMT"]
    assert raw_texts and raw_texts[0].read_text(encoding="utf-8").strip()
    assert rewrites and rewrites[0].read_text(encoding="utf-8").strip()

    payload = json.loads(manifests[0].read_text(encoding="utf-8"))
    assert payload["total_llm_cost_usd"] > 0.0
    assert payload["total_tts_cost_usd"] > 0.0
    assert payload["total_cost_usd"] == pytest.approx(
        payload["total_llm_cost_usd"] + payload["total_tts_cost_usd"]
    )
    assert payload["extra"]["chapter_source"] in {"pdf_outline", "text_heuristic"}
    assert isinstance(payload["extra"]["chapter_fallback_reason"], str)
    assert payload["extra"]["provider_translator"] == "openai"
    assert payload["extra"]["provider_rewriter"] == "openai"
    assert payload["extra"]["provider_tts"] == "openai"
    assert payload["extra"]["model_translate"]
    assert payload["extra"]["model_rewrite"]
    assert payload["extra"]["model_tts"]
    assert payload["extra"]["tts_voice"]

    assert "Chapter source:" in result.output
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


def test_build_command_emits_progress_and_phase_logs(tmp_path: Path) -> None:
    """Build command should emit deterministic progress lines and phase-level logs."""

    runner = CliRunner()
    out_dir = tmp_path / "out"
    fixture_pdf = Path("tests/files/zero_to_one.pdf")

    result = runner.invoke(app, ["build", str(fixture_pdf), "--out", str(out_dir)])

    assert result.exit_code == 0, result.output
    assert "[progress] command=build | 1/9 stage=extract" in result.output
    assert "[progress] command=build | 9/9 stage=manifest" in result.output
    assert "[phase] level=INFO stage=extract event=start" in result.output
    assert "[phase] level=INFO stage=extract event=complete" in result.output
    assert "[phase] level=INFO stage=translate event=start" in result.output
    assert "[phase] level=INFO stage=manifest event=complete" in result.output
