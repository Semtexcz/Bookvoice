"""Unit tests for deterministic packaged-audio export behavior."""

from __future__ import annotations

from pathlib import Path

import pytest

from bookvoice.audio.packaging import AudioPackager, PackagingOptions
from bookvoice.errors import PipelineStageError
from bookvoice.models.datatypes import AudioPart


def _fake_encode_chapter(
    self: AudioPackager,
    *,
    chapter_parts: list[AudioPart],
    format_id: str,
    output_path: Path,
) -> None:
    """Write deterministic placeholder bytes for encoded chapter outputs."""

    _ = self
    _ = chapter_parts
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(f"encoded-{format_id}".encode("utf-8"))


def _build_part(
    *,
    chapter_index: int,
    chunk_index: int,
    title: str,
    root: Path,
) -> AudioPart:
    """Create one deterministic audio-part record for packaging tests."""

    part_path = root / f"c{chapter_index:03d}_p{chunk_index:03d}.wav"
    part_path.write_bytes(b"wav")
    return AudioPart(
        chapter_index=chapter_index,
        chunk_index=chunk_index,
        path=part_path,
        duration_seconds=1.0,
        part_title=title,
        part_id=f"chapter-{chapter_index}-part-{chunk_index}",
    )


def test_package_uses_source_numbering_for_deterministic_chapter_filenames(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Source numbering mode should preserve source chapter indices in filenames."""

    monkeypatch.setattr(AudioPackager, "_encode_chapter", _fake_encode_chapter)
    packager = AudioPackager()
    audio_parts = [
        _build_part(chapter_index=12, chunk_index=1, title="Beta Chapter", root=tmp_path),
        _build_part(chapter_index=7, chunk_index=0, title="Alpha Chapter", root=tmp_path),
        _build_part(chapter_index=12, chunk_index=0, title="Beta Chapter", root=tmp_path),
    ]
    merged_path = tmp_path / "bookvoice_merged.wav"
    merged_path.write_bytes(b"merged")

    outputs = packager.package(
        audio_parts=audio_parts,
        merged_path=merged_path,
        output_root=tmp_path / "package",
        options=PackagingOptions(
            formats=("m4a",),
            chapter_numbering_mode="source",
            keep_merged_deliverable=True,
        ),
    )

    chapter_entries = [item for item in outputs if item.output_kind == "chapter"]
    assert [item.chapter_number for item in chapter_entries] == [7, 12]
    assert [item.path.name for item in chapter_entries] == [
        "chapter_007_alpha-chapter.m4a",
        "chapter_012_beta-chapter.m4a",
    ]
    assert (tmp_path / "package" / "bookvoice_merged.wav").exists()


def test_package_uses_sequential_numbering_for_selected_chapters(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Sequential numbering mode should renumber chapter outputs from one."""

    monkeypatch.setattr(AudioPackager, "_encode_chapter", _fake_encode_chapter)
    packager = AudioPackager()
    audio_parts = [
        _build_part(chapter_index=9, chunk_index=0, title="Gamma Chapter", root=tmp_path),
        _build_part(chapter_index=5, chunk_index=0, title="Delta Chapter", root=tmp_path),
    ]

    outputs = packager.package(
        audio_parts=audio_parts,
        merged_path=tmp_path / "bookvoice_merged.wav",
        output_root=tmp_path / "package",
        options=PackagingOptions(
            formats=("mp3",),
            chapter_numbering_mode="sequential",
            keep_merged_deliverable=False,
        ),
    )

    chapter_entries = [item for item in outputs if item.output_kind == "chapter"]
    assert [item.chapter_number for item in chapter_entries] == [1, 2]
    assert [item.path.name for item in chapter_entries] == [
        "chapter_001_delta-chapter.mp3",
        "chapter_002_gamma-chapter.mp3",
    ]


def test_package_mode_none_does_not_emit_packaged_outputs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Disabled packaging mode should not encode chapters or copy merged WAV."""

    def _unexpected_encode(*_: object, **__: object) -> None:
        """Fail the test if chapter encoding is called in disabled mode."""

        raise AssertionError("Packaging should not encode chapters when format list is empty.")

    monkeypatch.setattr(AudioPackager, "_encode_chapter", _unexpected_encode)
    packager = AudioPackager()
    merged_path = tmp_path / "bookvoice_merged.wav"
    merged_path.write_bytes(b"merged")

    outputs = packager.package(
        audio_parts=[],
        merged_path=merged_path,
        output_root=tmp_path / "package",
        options=PackagingOptions(
            formats=tuple(),
            chapter_numbering_mode="source",
            keep_merged_deliverable=True,
        ),
    )

    assert outputs == []
    assert not (tmp_path / "package" / "bookvoice_merged.wav").exists()


def test_encode_chapter_reports_missing_ffmpeg_deterministically(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Missing ffmpeg runtime should map to a stage-aware package error."""

    def _missing_ffmpeg(*_: object, **__: object) -> None:
        """Raise deterministic missing-binary error for subprocess execution."""

        raise FileNotFoundError("ffmpeg")

    monkeypatch.setattr("bookvoice.audio.packaging.subprocess.run", _missing_ffmpeg)
    packager = AudioPackager()
    chapter_part = _build_part(
        chapter_index=1,
        chunk_index=0,
        title="Intro",
        root=tmp_path,
    )
    output_path = tmp_path / "package" / "chapter_001_intro.m4a"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with pytest.raises(PipelineStageError) as exc_info:
        packager._encode_chapter(
            chapter_parts=[chapter_part],
            format_id="m4a",
            output_path=output_path,
        )

    assert exc_info.value.stage == "package"
    assert "ffmpeg" in exc_info.value.detail.lower()
