"""Integration tests for chapter-packaged output generation and replay behavior."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from bookvoice.audio.packaging import AudioPackager
from bookvoice.cli import app
from bookvoice.models.datatypes import AudioPart


def _fake_encode_chapter(
    self: AudioPackager,
    *,
    chapter_parts: list[AudioPart],
    format_id: str,
    output_path: Path,
    tag_payload: object | None = None,
) -> None:
    """Write deterministic placeholder bytes for packaged outputs in tests."""

    _ = self
    _ = chapter_parts
    _ = tag_payload
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(f"packaged-{format_id}".encode("utf-8"))


def test_build_creates_deterministic_packaged_outputs_and_manifest_references(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Build should persist chapter-split package outputs with deterministic metadata."""

    monkeypatch.setattr(AudioPackager, "_encode_chapter", _fake_encode_chapter)

    runner = CliRunner()
    out_dir = tmp_path / "out"
    fixture_pdf = Path("tests/files/zero_to_one.pdf")
    result = runner.invoke(
        app,
        [
            "build",
            str(fixture_pdf),
            "--out",
            str(out_dir),
            "--package-mode",
            "both",
            "--package-chapter-numbering",
            "sequential",
            "--package-keep-merged",
        ],
    )

    assert result.exit_code == 0, result.output
    manifest_path = next(out_dir.glob("run-*/run_manifest.json"))
    manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest_payload["extra"]["packaging_mode"] == "both"
    assert manifest_payload["extra"]["packaging_chapter_numbering"] == "sequential"
    assert manifest_payload["extra"]["packaging_keep_merged"] == "true"
    assert manifest_payload["extra"]["packaging_tags_schema"] == "bookvoice-packaged-v1"
    assert manifest_payload["extra"]["packaging_tags_enabled"] == "true"
    assert (
        manifest_payload["extra"]["packaging_tags_fields_csv"]
        == "title,album,track,chapter_context,source_identifier"
    )
    assert manifest_payload["extra"]["packaging_tags_source_identifier"].endswith(
        f"#{manifest_path.parent.name}"
    )

    packaged_path = Path(manifest_payload["extra"]["packaged_audio"])
    assert packaged_path.exists()
    packaged_payload = json.loads(packaged_path.read_text(encoding="utf-8"))
    assert packaged_payload["metadata"]["packaging_tags_schema"] == "bookvoice-packaged-v1"
    assert packaged_payload["metadata"]["packaging_tags_enabled"] == "true"
    packaged_entries = packaged_payload["packaged_audio"]
    assert packaged_entries, "packaged outputs should be persisted"

    chapter_entries = [
        item for item in packaged_entries if item["output_kind"] == "chapter"
    ]
    merged_entries = [
        item for item in packaged_entries if item["output_kind"] == "merged"
    ]
    assert chapter_entries
    assert {item["format"] for item in chapter_entries} == {"m4a", "mp3"}
    assert len(merged_entries) == 1
    assert merged_entries[0]["format"] == "wav"

    m4a_numbers = sorted(
        int(item["chapter_number"]) for item in chapter_entries if item["format"] == "m4a"
    )
    assert m4a_numbers == list(range(1, len(m4a_numbers) + 1))
    for item in packaged_entries:
        assert Path(item["path"]).exists()
        assert item["filename"].startswith("chapter_") or item["filename"] == "bookvoice_merged.wav"


def test_resume_reuses_packaged_outputs_without_reencoding(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Resume should not re-encode packaged chapter files when all artifacts are reusable."""

    monkeypatch.setattr(AudioPackager, "_encode_chapter", _fake_encode_chapter)

    runner = CliRunner()
    out_dir = tmp_path / "out"
    fixture_pdf = Path("tests/files/zero_to_one.pdf")
    build_result = runner.invoke(
        app,
        [
            "build",
            str(fixture_pdf),
            "--out",
            str(out_dir),
            "--package-mode",
            "aac",
        ],
    )
    assert build_result.exit_code == 0, build_result.output

    manifest_path = next(out_dir.glob("run-*/run_manifest.json"))

    def _unexpected_encode(*_: object, **__: object) -> None:
        """Fail test if resume unexpectedly re-encodes packaged chapter outputs."""

        raise AssertionError("Packaged outputs should be reused during full resume.")

    monkeypatch.setattr(AudioPackager, "_encode_chapter", _unexpected_encode)
    resume_result = runner.invoke(app, ["resume", str(manifest_path)])
    assert resume_result.exit_code == 0, resume_result.output
    assert "Resumed from stage: done" in resume_result.output


def test_tts_only_replays_with_packaging_metadata_and_outputs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """TTS-only replay should preserve packaging settings and regenerate package artifacts."""

    monkeypatch.setattr(AudioPackager, "_encode_chapter", _fake_encode_chapter)

    runner = CliRunner()
    out_dir = tmp_path / "out"
    fixture_pdf = Path("tests/files/zero_to_one.pdf")
    build_result = runner.invoke(
        app,
        [
            "build",
            str(fixture_pdf),
            "--out",
            str(out_dir),
            "--package-mode",
            "mp3",
            "--no-package-keep-merged",
        ],
    )
    assert build_result.exit_code == 0, build_result.output

    manifest_path = next(out_dir.glob("run-*/run_manifest.json"))
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    Path(payload["extra"]["audio_parts"]).unlink()
    Path(payload["merged_audio_path"]).unlink()

    replay_result = runner.invoke(app, ["tts-only", str(manifest_path)])
    assert replay_result.exit_code == 0, replay_result.output

    replayed_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert replayed_payload["extra"]["packaging_mode"] == "mp3"
    assert replayed_payload["extra"]["packaging_keep_merged"] == "false"
    assert replayed_payload["extra"]["packaging_tags_schema"] == "bookvoice-packaged-v1"
    assert replayed_payload["extra"]["packaging_tags_enabled"] == "true"
    packaged_payload = json.loads(
        Path(replayed_payload["extra"]["packaged_audio"]).read_text(encoding="utf-8")
    )
    chapter_entries = [
        item
        for item in packaged_payload["packaged_audio"]
        if item["output_kind"] == "chapter"
    ]
    assert chapter_entries
    assert {item["format"] for item in chapter_entries} == {"mp3"}


def test_build_source_numbering_preserves_selected_chapter_indices(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Build should keep source chapter indices in packaged outputs by default."""

    monkeypatch.setattr(AudioPackager, "_encode_chapter", _fake_encode_chapter)

    runner = CliRunner()
    out_dir = tmp_path / "out"
    fixture_pdf = Path("tests/files/zero_to_one.pdf")
    result = runner.invoke(
        app,
        [
            "build",
            str(fixture_pdf),
            "--out",
            str(out_dir),
            "--chapters",
            "2-3",
            "--package-mode",
            "aac",
        ],
    )

    assert result.exit_code == 0, result.output
    manifest_path = next(out_dir.glob("run-*/run_manifest.json"))
    manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    packaged_payload = json.loads(
        Path(manifest_payload["extra"]["packaged_audio"]).read_text(encoding="utf-8")
    )
    chapter_entries = [
        item
        for item in packaged_payload["packaged_audio"]
        if item["output_kind"] == "chapter" and item["format"] == "m4a"
    ]

    assert [int(item["chapter_index"]) for item in chapter_entries] == [2, 3]
    assert [int(item["chapter_number"]) for item in chapter_entries] == [2, 3]
    filenames = [item["filename"] for item in chapter_entries]
    assert filenames[0].startswith("chapter_002_")
    assert filenames[1].startswith("chapter_003_")
    assert all(name.endswith(".m4a") for name in filenames)
