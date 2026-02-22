"""Unit tests for deterministic merged-audio postprocessing and tagging."""

from __future__ import annotations

from array import array
from pathlib import Path
import wave

from bookvoice.audio.postprocess import AudioPostProcessor
from bookvoice.audio.tags import AudioTagContext, MetadataWriter


def _write_wav(path: Path, samples: array[int], sample_rate: int = 24000) -> None:
    """Write a mono PCM16 WAV file from integer samples."""

    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(samples.tobytes())


def _read_wav_frames(path: Path) -> tuple[wave._wave_params, bytes]:
    """Read WAV params and frame bytes."""

    with wave.open(str(path), "rb") as wav_file:
        params = wav_file.getparams()
        frames = wav_file.readframes(params.nframes)
    return params, frames


def _parse_wav_info_tags(wav_bytes: bytes) -> dict[str, str]:
    """Parse RIFF `LIST/INFO` tags from a WAV payload."""

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


def _peak_abs_pcm16(frames: bytes) -> int:
    """Return absolute peak for mono/stereo PCM16 payload bytes."""

    if not frames:
        return 0
    samples = array("h")
    samples.frombytes(frames)
    return max(abs(sample) for sample in samples)


def test_postprocess_trim_and_normalize_are_deterministic(tmp_path: Path) -> None:
    """Postprocessing should trim silence, normalize peak, and stay idempotent."""

    path = tmp_path / "merged.wav"
    samples = array("h", [0] * 120 + [1000] * 1000 + [0] * 80)
    _write_wav(path, samples)

    processor = AudioPostProcessor()
    processor.process_merged(path)
    first_pass_bytes = path.read_bytes()
    processor.process_merged(path)
    second_pass_bytes = path.read_bytes()

    assert first_pass_bytes == second_pass_bytes

    params, frames = _read_wav_frames(path)
    assert params.nframes == 1000
    peak = _peak_abs_pcm16(frames)
    expected_peak = int(round(((1 << (params.sampwidth * 8 - 1)) - 1) * 0.95))
    assert abs(peak - expected_peak) <= 1


def test_metadata_writer_writes_stable_wav_info_tags(tmp_path: Path) -> None:
    """Tagging should write deterministic RIFF INFO fields and remain idempotent."""

    path = tmp_path / "merged.wav"
    _write_wav(path, array("h", [2000] * 400))

    writer = MetadataWriter()
    writer.write(
        path,
        AudioTagContext(
            title="Example Book",
            chapter_scope_label="1-2",
            chapter_indices_csv="1,2",
            source_identifier="source.pdf#run-abc",
            part_count=3,
            part_ids_csv="001_01_intro,001_02_body,002_01_end",
        ),
    )
    first_pass_bytes = path.read_bytes()
    writer.write(
        path,
        AudioTagContext(
            title="Example Book",
            chapter_scope_label="1-2",
            chapter_indices_csv="1,2",
            source_identifier="source.pdf#run-abc",
            part_count=3,
            part_ids_csv="001_01_intro,001_02_body,002_01_end",
        ),
    )
    second_pass_bytes = path.read_bytes()

    assert first_pass_bytes == second_pass_bytes

    tags = _parse_wav_info_tags(first_pass_bytes)
    assert tags["INAM"] == "Example Book"
    assert "scope=1-2" in tags["ISBJ"]
    assert "indices=1,2" in tags["ISBJ"]
    assert "parts=3" in tags["ISBJ"]
    assert "source=source.pdf#run-abc" == tags["ICMT"]
