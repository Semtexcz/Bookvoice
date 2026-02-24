"""Deterministic packaged-audio export helpers.

Responsibilities:
- Parse packaging intent from config metadata.
- Export chapter-split packaged outputs from deterministic WAV chunk artifacts.
- Keep packaged naming and chapter numbering deterministic across replays.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
import subprocess

from ..errors import PipelineStageError
from ..models.datatypes import AudioPart, PackagedAudio
from ..parsing import normalize_optional_string, parse_permissive_boolean
from ..runtime_tools import resolve_executable
from ..text.slug import slugify_audio_title


@dataclass(frozen=True, slots=True)
class PackagingOptions:
    """Resolved packaging options for one run.

    Attributes:
        formats: Ordered packaged output formats (`m4a`, `mp3`), empty when disabled.
        chapter_numbering_mode: Chapter numbering mode (`source` or `sequential`).
        keep_merged_deliverable: Whether to include full merged WAV in package outputs.
    """

    formats: tuple[str, ...]
    chapter_numbering_mode: str
    keep_merged_deliverable: bool


@dataclass(frozen=True, slots=True)
class PackagedTagContext:
    """Run-level context used to build deterministic packaged metadata tags.

    Attributes:
        book_title: Human-readable run/book title for packaged chapter outputs.
        chapter_scope_label: Chapter scope summary (`all`, `1-3`, etc.).
        chapter_indices_csv: Resolved chapter index list in CSV form.
        source_identifier: Compact run identifier (`<source.pdf>#<run-id>`).
    """

    book_title: str
    chapter_scope_label: str
    chapter_indices_csv: str
    source_identifier: str


@dataclass(frozen=True, slots=True)
class PackagedTagPayload:
    """Canonical packaged metadata payload independent of audio container format.

    Attributes:
        title: Chapter title shown in playback UIs.
        album: Book/run-level title context for chapter outputs.
        track_number: Chapter number used in output naming policy.
        track_total: Total chapter count for the packaged run scope.
        chapter_context: Compact chapter-scope context string.
        source_identifier: Source/run identifier for traceability.
    """

    title: str
    album: str
    track_number: int
    track_total: int
    chapter_context: str
    source_identifier: str


class AudioPackager:
    """Export chapter-split packaged audio files using a deterministic ffmpeg policy."""

    _VALID_FORMATS = frozenset({"m4a", "mp3"})
    _VALID_NUMBERING_MODES = frozenset({"source", "sequential"})

    def resolve_options(self, extra: dict[str, str]) -> PackagingOptions:
        """Resolve packaging options from config/manifest `extra` values."""

        mode = normalize_optional_string(extra.get("packaging_mode")) or "none"
        numbering_mode = (
            normalize_optional_string(extra.get("packaging_chapter_numbering")) or "source"
        ).lower()
        keep_merged_raw = extra.get("packaging_keep_merged")
        parsed_keep_merged = parse_permissive_boolean(keep_merged_raw)
        keep_merged = True if parsed_keep_merged is None else parsed_keep_merged

        normalized_mode = mode.lower()
        if normalized_mode == "none":
            formats: tuple[str, ...] = tuple()
        elif normalized_mode in {"aac", "m4a"}:
            formats = ("m4a",)
        elif normalized_mode == "mp3":
            formats = ("mp3",)
        elif normalized_mode in {"both", "all"}:
            formats = ("m4a", "mp3")
        else:
            raise PipelineStageError(
                stage="package",
                detail=(
                    "Unsupported packaging mode "
                    f"`{mode}`. Supported: `none`, `aac`, `mp3`, `both`."
                ),
                hint="Use `--package-mode` with one of: `none`, `aac`, `mp3`, `both`.",
            )

        if numbering_mode not in self._VALID_NUMBERING_MODES:
            raise PipelineStageError(
                stage="package",
                detail=(
                    "Unsupported chapter numbering mode "
                    f"`{numbering_mode}`. Supported: `source`, `sequential`."
                ),
                hint="Use `--package-chapter-numbering` with `source` or `sequential`.",
            )

        return PackagingOptions(
            formats=formats,
            chapter_numbering_mode=numbering_mode,
            keep_merged_deliverable=keep_merged,
        )

    def package(
        self,
        *,
        audio_parts: list[AudioPart],
        merged_path: Path,
        output_root: Path,
        options: PackagingOptions,
        tag_context: PackagedTagContext | None = None,
    ) -> list[PackagedAudio]:
        """Export packaged outputs according to resolved deterministic options."""

        output_root.mkdir(parents=True, exist_ok=True)
        packaged_outputs: list[PackagedAudio] = []
        chapter_groups = self._group_parts_by_chapter(audio_parts)
        chapter_total = len(chapter_groups)

        for format_id in options.formats:
            for sequence_number, chapter_entry in enumerate(chapter_groups, start=1):
                chapter_index = chapter_entry[0]
                chapter_parts = chapter_entry[1]
                chapter_title = chapter_parts[0].part_title or f"chapter-{chapter_index:03d}"
                chapter_number = (
                    chapter_index
                    if options.chapter_numbering_mode == "source"
                    else sequence_number
                )
                output_path = output_root / self._chapter_filename(
                    chapter_number=chapter_number,
                    chapter_title=chapter_title,
                    format_id=format_id,
                )
                tag_payload = self._chapter_tag_payload(
                    chapter_title=chapter_title,
                    chapter_index=chapter_index,
                    chapter_number=chapter_number,
                    chapter_total=chapter_total,
                    numbering_mode=options.chapter_numbering_mode,
                    context=tag_context,
                )
                self._encode_chapter(
                    chapter_parts=chapter_parts,
                    format_id=format_id,
                    output_path=output_path,
                    tag_payload=tag_payload,
                )
                packaged_outputs.append(
                    PackagedAudio(
                        output_kind="chapter",
                        format=format_id,
                        chapter_index=chapter_index,
                        chapter_number=chapter_number,
                        chapter_title=chapter_title,
                        path=output_path,
                        source_part_filenames=tuple(part.path.name for part in chapter_parts),
                    )
                )

        if options.formats and options.keep_merged_deliverable and merged_path.exists():
            merged_output_path = output_root / "bookvoice_merged.wav"
            shutil.copyfile(merged_path, merged_output_path)
            packaged_outputs.append(
                PackagedAudio(
                    output_kind="merged",
                    format="wav",
                    chapter_index=None,
                    chapter_number=None,
                    chapter_title=None,
                    path=merged_output_path,
                    source_part_filenames=tuple(),
                )
            )

        return packaged_outputs

    def _group_parts_by_chapter(self, audio_parts: list[AudioPart]) -> list[tuple[int, list[AudioPart]]]:
        """Group sorted audio parts by chapter index."""

        grouped: dict[int, list[AudioPart]] = {}
        for part in sorted(audio_parts, key=lambda item: (item.chapter_index, item.chunk_index)):
            grouped.setdefault(part.chapter_index, []).append(part)
        return [(index, grouped[index]) for index in sorted(grouped)]

    def _chapter_filename(self, *, chapter_number: int, chapter_title: str, format_id: str) -> str:
        """Build deterministic package filename for one chapter output."""

        slug = slugify_audio_title(chapter_title)
        extension = format_id.lower()
        return f"chapter_{chapter_number:03d}_{slug}.{extension}"

    def _encode_chapter(
        self,
        *,
        chapter_parts: list[AudioPart],
        format_id: str,
        output_path: Path,
        tag_payload: PackagedTagPayload | None = None,
    ) -> None:
        """Encode one chapter from ordered WAV parts into the target packaged format."""

        if format_id not in self._VALID_FORMATS:
            raise PipelineStageError(
                stage="package",
                detail=f"Unsupported packaging format `{format_id}`.",
                hint="Use `m4a` or `mp3` packaging targets.",
            )

        concat_path = output_path.with_suffix(f".{format_id}.concat.txt")
        concat_content = "\n".join(
            f"file '{self._escape_concat_path(part.path.resolve())}'"
            for part in chapter_parts
        )
        concat_path.write_text(concat_content + "\n", encoding="utf-8")

        codec, bitrate = self._encoding_profile(format_id)
        command = [
            resolve_executable("ffmpeg"),
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_path),
            "-vn",
            "-map_metadata",
            "-1",
            "-fflags",
            "+bitexact",
            "-ac",
            "1",
            "-ar",
            "24000",
            "-c:a",
            codec,
            "-b:a",
            bitrate,
        ]
        command.extend(self._format_metadata_arguments(format_id, tag_payload))
        command.append(str(output_path))

        try:
            subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError as exc:
            raise PipelineStageError(
                stage="package",
                detail="Packaging tool `ffmpeg` is not available on PATH.",
                hint=(
                    "Install ffmpeg and rerun. Packaging is optional; you can also run with "
                    "`--package-mode none`."
                ),
            ) from exc
        except subprocess.CalledProcessError as exc:
            stderr = normalize_optional_string(exc.stderr) or "no stderr output"
            raise PipelineStageError(
                stage="package",
                detail=f"ffmpeg packaging failed for `{output_path.name}`: {stderr}",
                hint=(
                    "Verify local ffmpeg codec support for requested target "
                    "(`aac` for m4a or `libmp3lame` for mp3)."
                ),
            ) from exc
        finally:
            if concat_path.exists():
                concat_path.unlink()

    def _encoding_profile(self, format_id: str) -> tuple[str, str]:
        """Return explicit deterministic codec profile for one packaged format."""

        if format_id == "m4a":
            return "aac", "128k"
        return "libmp3lame", "128k"

    def _chapter_tag_payload(
        self,
        *,
        chapter_title: str,
        chapter_index: int,
        chapter_number: int,
        chapter_total: int,
        numbering_mode: str,
        context: PackagedTagContext | None,
    ) -> PackagedTagPayload:
        """Build canonical chapter tag payload from deterministic packaging context."""

        book_title = context.book_title if context is not None else "Bookvoice"
        chapter_context = self._chapter_context_value(
            chapter_index=chapter_index,
            chapter_number=chapter_number,
            numbering_mode=numbering_mode,
            chapter_scope_label=context.chapter_scope_label if context is not None else "all",
            chapter_indices_csv=context.chapter_indices_csv if context is not None else "",
        )
        source_identifier = (
            context.source_identifier if context is not None else "unknown#unknown"
        )
        return PackagedTagPayload(
            title=chapter_title,
            album=book_title,
            track_number=chapter_number,
            track_total=chapter_total,
            chapter_context=chapter_context,
            source_identifier=source_identifier,
        )

    def _chapter_context_value(
        self,
        *,
        chapter_index: int,
        chapter_number: int,
        numbering_mode: str,
        chapter_scope_label: str,
        chapter_indices_csv: str,
    ) -> str:
        """Build compact deterministic chapter context value for packaged tag payloads."""

        indices = chapter_indices_csv if chapter_indices_csv else "-"
        return (
            f"scope={chapter_scope_label};indices={indices};"
            f"source_index={chapter_index};chapter_number={chapter_number};"
            f"numbering={numbering_mode}"
        )

    def _format_metadata_arguments(
        self,
        format_id: str,
        payload: PackagedTagPayload | None,
    ) -> list[str]:
        """Build deterministic ffmpeg metadata arguments for one output container."""

        if payload is None:
            return []

        track_value = f"{payload.track_number}/{payload.track_total}"
        if format_id == "mp3":
            tag_pairs = [
                ("title", payload.title),
                ("album", payload.album),
                ("track", track_value),
                ("comment", payload.chapter_context),
                ("publisher", payload.source_identifier),
            ]
            args = ["-id3v2_version", "3"]
        else:
            tag_pairs = [
                ("title", payload.title),
                ("album", payload.album),
                ("track", track_value),
                ("description", payload.chapter_context),
                ("comment", payload.source_identifier),
            ]
            args = []

        for key, value in tag_pairs:
            normalized = value.strip()
            if normalized:
                args.extend(["-metadata", f"{key}={normalized}"])
        return args

    def _escape_concat_path(self, path: Path) -> str:
        """Escape one file path for ffmpeg concat list format."""

        return str(path).replace("'", "'\\''")
