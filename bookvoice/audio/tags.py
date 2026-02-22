"""Deterministic metadata tagging for emitted audio artifacts.

Responsibilities:
- Write metadata tags for formats that support in-place tagging.
- Keep tagging deterministic and replay-safe for resume/tts-only flows.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..models.datatypes import BookMeta


@dataclass(frozen=True, slots=True)
class AudioTagContext:
    """Tag payload context for merged audio outputs.

    Attributes:
        title: Human-readable merged output title.
        chapter_scope_label: Chapter scope summary (`all`, `1-3`, etc.).
        chapter_indices_csv: Resolved chapter index list.
        source_identifier: Source identifier for run-level traceability.
        part_count: Number of chunk parts merged into output.
        part_ids_csv: Optional compact list of part identifiers.
    """

    title: str
    chapter_scope_label: str
    chapter_indices_csv: str
    source_identifier: str
    part_count: int
    part_ids_csv: str


class MetadataWriter:
    """Write deterministic metadata tags for merged audio files."""

    def write_id3(self, audio_path: Path, book: BookMeta) -> Path:
        """Write deterministic WAV tags from `BookMeta` context."""

        context = AudioTagContext(
            title=book.title,
            chapter_scope_label="all",
            chapter_indices_csv="",
            source_identifier=str(book.source_pdf),
            part_count=0,
            part_ids_csv="",
        )
        return self.write(audio_path, context)

    def write(self, audio_path: Path, context: AudioTagContext) -> Path:
        """Write tags for known formats and return output path."""

        if audio_path.suffix.lower() != ".wav":
            return audio_path

        original = audio_path.read_bytes()
        tagged = self._write_wav_info_tags(
            original,
            {
                "INAM": context.title,
                "ISBJ": self._chapter_context_value(context),
                "ICMT": self._source_context_value(context),
            },
        )
        if tagged != original:
            audio_path.write_bytes(tagged)
        return audio_path

    def _chapter_context_value(self, context: AudioTagContext) -> str:
        """Build compact deterministic chapter/part context value."""

        indices = context.chapter_indices_csv if context.chapter_indices_csv else "-"
        return (
            f"scope={context.chapter_scope_label};indices={indices};"
            f"parts={context.part_count};part_ids={context.part_ids_csv or '-'}"
        )

    def _source_context_value(self, context: AudioTagContext) -> str:
        """Build compact deterministic source identifier value."""

        return f"source={context.source_identifier}"

    def _write_wav_info_tags(self, wav_bytes: bytes, tags: dict[str, str]) -> bytes:
        """Write RIFF `LIST/INFO` tags into a WAV payload deterministically."""

        if len(wav_bytes) < 12 or wav_bytes[0:4] != b"RIFF" or wav_bytes[8:12] != b"WAVE":
            return wav_bytes

        chunk_payload = wav_bytes[12:]
        chunks: list[bytes] = []
        offset = 0
        while offset + 8 <= len(chunk_payload):
            chunk_id = chunk_payload[offset : offset + 4]
            chunk_size = int.from_bytes(chunk_payload[offset + 4 : offset + 8], "little")
            content_start = offset + 8
            content_end = content_start + chunk_size
            if content_end > len(chunk_payload):
                return wav_bytes
            full_end = content_end + (chunk_size % 2)
            content = chunk_payload[content_start:content_end]

            is_existing_info = chunk_id == b"LIST" and content.startswith(b"INFO")
            if not is_existing_info:
                chunks.append(chunk_payload[offset:full_end])
            offset = full_end

        info_chunk = self._build_wav_info_chunk(tags)
        if info_chunk:
            chunks.append(info_chunk)

        rebuilt_data = b"".join(chunks)
        riff_size = 4 + len(rebuilt_data)
        return b"RIFF" + riff_size.to_bytes(4, "little") + b"WAVE" + rebuilt_data

    def _build_wav_info_chunk(self, tags: dict[str, str]) -> bytes:
        """Build a deterministic RIFF `LIST/INFO` chunk from normalized tags."""

        subchunks: list[bytes] = []
        for key in sorted(tags):
            value = tags[key].strip()
            if len(key) != 4 or not value:
                continue

            payload = value.encode("utf-8") + b"\x00"
            padding = b"\x00" if len(payload) % 2 else b""
            subchunks.append(
                key.encode("ascii")
                + len(payload).to_bytes(4, "little")
                + payload
                + padding
            )

        info_payload = b"INFO" + b"".join(subchunks)
        if not subchunks:
            return b""
        chunk_padding = b"\x00" if len(info_payload) % 2 else b""
        return b"LIST" + len(info_payload).to_bytes(4, "little") + info_payload + chunk_padding
