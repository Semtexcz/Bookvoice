"""Deterministic packaged-audio export helpers.

Responsibilities:
- Parse packaging intent from config metadata.
- Export chapter-split packaged outputs from deterministic WAV chunk artifacts.
- Keep packaged naming and chapter numbering deterministic across replays.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
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
        output_format: Canonical output format intent (`wav`, `m4a`, `mp3`, `both`).
        formats: Ordered packaged chapter output formats (`m4a`, `mp3`), empty when disabled.
        chapter_outputs_enabled: Whether chapter-split packaged outputs are enabled.
        chapter_numbering_mode: Chapter numbering mode (`source` or `sequential`).
        naming_mode: Chapter filename policy (`deterministic` or `reader_friendly`).
        encoding_bitrate: Target packaged audio bitrate token (`96k`, `128k`, etc.).
        encoding_profile: Target packaging profile (`balanced`, `voice`, or `music`).
        keep_merged_deliverable: Whether to include full merged WAV in package outputs.
    """

    output_format: str
    formats: tuple[str, ...]
    chapter_outputs_enabled: bool
    chapter_numbering_mode: str
    naming_mode: str
    encoding_bitrate: str
    encoding_profile: str
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
    _VALID_NAMING_MODES = frozenset({"deterministic", "reader_friendly"})
    _VALID_ENCODING_PROFILES = frozenset({"balanced", "voice", "music"})
    _PROFILE_DEFAULT_BITRATE = {
        "balanced": "128k",
        "voice": "96k",
        "music": "160k",
    }
    _VALID_BITRATE_PATTERN = re.compile(r"^\d{2,3}k$")

    def resolve_options(self, extra: dict[str, str]) -> PackagingOptions:
        """Resolve packaging options from config/manifest `extra` values."""

        mode = normalize_optional_string(extra.get("packaging_output_format")) or normalize_optional_string(
            extra.get("packaging_mode")
        ) or "wav"
        chapter_outputs_raw = extra.get("packaging_chapter_outputs")
        numbering_mode = (
            normalize_optional_string(extra.get("packaging_chapter_numbering")) or "source"
        ).lower()
        naming_mode = (
            normalize_optional_string(extra.get("packaging_naming_mode")) or "deterministic"
        ).lower()
        encoding_profile = (
            normalize_optional_string(extra.get("packaging_encoding_profile")) or "balanced"
        ).lower()
        encoding_bitrate = normalize_optional_string(extra.get("packaging_encoding_bitrate"))
        keep_merged_raw = extra.get("packaging_keep_merged")
        parsed_chapter_outputs = parse_permissive_boolean(chapter_outputs_raw)
        chapter_outputs_enabled = (
            True if parsed_chapter_outputs is None else parsed_chapter_outputs
        )
        parsed_keep_merged = parse_permissive_boolean(keep_merged_raw)
        keep_merged = True if parsed_keep_merged is None else parsed_keep_merged

        normalized_mode, formats = self._resolve_output_format(mode)
        if not chapter_outputs_enabled:
            formats = tuple()

        if numbering_mode not in self._VALID_NUMBERING_MODES:
            raise PipelineStageError(
                stage="package",
                detail=(
                    "Unsupported chapter numbering mode "
                    f"`{numbering_mode}`. Supported: `source`, `sequential`."
                ),
                hint="Use `--package-chapter-numbering` with `source` or `sequential`.",
            )
        if naming_mode not in self._VALID_NAMING_MODES:
            raise PipelineStageError(
                stage="package",
                detail=(
                    "Unsupported naming mode "
                    f"`{naming_mode}`. Supported: `deterministic`, `reader_friendly`."
                ),
                hint="Use `--package-naming` with `deterministic` or `reader_friendly`.",
            )
        if encoding_profile not in self._VALID_ENCODING_PROFILES:
            raise PipelineStageError(
                stage="package",
                detail=(
                    "Unsupported encoding profile "
                    f"`{encoding_profile}`. Supported: `balanced`, `voice`, `music`."
                ),
                hint="Use `--package-encoding-profile` with `balanced`, `voice`, or `music`.",
            )

        resolved_bitrate = encoding_bitrate or self._PROFILE_DEFAULT_BITRATE[encoding_profile]
        if self._VALID_BITRATE_PATTERN.fullmatch(resolved_bitrate.lower()) is None:
            raise PipelineStageError(
                stage="package",
                detail=(
                    "Unsupported encoding bitrate "
                    f"`{resolved_bitrate}`. Expected token like `96k` or `128k`."
                ),
                hint="Use `--package-encoding-bitrate` with a bitrate like `96k` or `128k`.",
            )

        return PackagingOptions(
            output_format=normalized_mode,
            formats=formats,
            chapter_outputs_enabled=chapter_outputs_enabled,
            chapter_numbering_mode=numbering_mode,
            naming_mode=naming_mode,
            encoding_bitrate=resolved_bitrate.lower(),
            encoding_profile=encoding_profile,
            keep_merged_deliverable=keep_merged,
        )

    def _resolve_output_format(self, value: str) -> tuple[str, tuple[str, ...]]:
        """Resolve canonical output format and chapter-package format tuple from one value."""

        normalized = value.strip().lower()
        if normalized in {"wav", "none"}:
            return "wav", tuple()
        if normalized in {"m4a", "aac"}:
            return "m4a", ("m4a",)
        if normalized == "mp3":
            return "mp3", ("mp3",)
        if normalized in {"both", "all"}:
            return "both", ("m4a", "mp3")
        if "," in normalized:
            tokens = {
                token.strip()
                for token in normalized.split(",")
                if token.strip()
            }
            if not tokens:
                raise PipelineStageError(
                    stage="package",
                    detail="Output format list cannot be empty.",
                    hint="Use `--output-format` with `wav`, `m4a`, `mp3`, or `m4a,mp3`.",
                )
            if tokens.issubset({"wav"}):
                return "wav", tuple()
            if tokens.issubset({"m4a", "aac"}):
                return "m4a", ("m4a",)
            if tokens.issubset({"mp3"}):
                return "mp3", ("mp3",)
            if tokens.issubset({"m4a", "aac", "mp3", "wav"}):
                if "mp3" in tokens and ("m4a" in tokens or "aac" in tokens):
                    return "both", ("m4a", "mp3")
                if "mp3" in tokens:
                    return "mp3", ("mp3",)
                return "m4a", ("m4a",)
        raise PipelineStageError(
            stage="package",
            detail=(
                "Unsupported output format "
                f"`{value}`. Supported: `wav`, `m4a`, `mp3`, `both`, or `m4a,mp3`."
            ),
            hint=(
                "Use `--output-format` for the new surface or keep legacy "
                "`--package-mode` (`none`, `aac`, `mp3`, `both`)."
            ),
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

        if options.chapter_outputs_enabled:
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
                        naming_mode=options.naming_mode,
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
                        encoding_bitrate=options.encoding_bitrate,
                        encoding_profile=options.encoding_profile,
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

        if (
            options.chapter_outputs_enabled
            and options.formats
            and options.keep_merged_deliverable
            and merged_path.exists()
        ):
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

    def _chapter_filename(
        self,
        *,
        chapter_number: int,
        chapter_title: str,
        format_id: str,
        naming_mode: str,
    ) -> str:
        """Build deterministic package filename for one chapter output."""

        extension = format_id.lower()
        if naming_mode == "reader_friendly":
            safe_title = re.sub(r"[\\/:*?\"<>|]+", "-", chapter_title).strip()
            normalized_title = " ".join(safe_title.split()) or "Untitled Chapter"
            return f"{chapter_number:03d} - {normalized_title}.{extension}"
        slug = slugify_audio_title(chapter_title)
        return f"chapter_{chapter_number:03d}_{slug}.{extension}"

    def _encode_chapter(
        self,
        *,
        chapter_parts: list[AudioPart],
        format_id: str,
        output_path: Path,
        tag_payload: PackagedTagPayload | None = None,
        encoding_bitrate: str = "128k",
        encoding_profile: str = "balanced",
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

        codec, bitrate = self._encoding_profile(
            format_id,
            encoding_bitrate=encoding_bitrate,
            encoding_profile=encoding_profile,
        )
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

    def _encoding_profile(
        self,
        format_id: str,
        *,
        encoding_bitrate: str,
        encoding_profile: str,
    ) -> tuple[str, str]:
        """Return explicit deterministic codec profile for one packaged format."""

        if encoding_profile not in self._VALID_ENCODING_PROFILES:
            raise PipelineStageError(
                stage="package",
                detail=(
                    "Unsupported encoding profile "
                    f"`{encoding_profile}`. Supported: `balanced`, `voice`, `music`."
                ),
                hint="Set `packaging_encoding_profile` to `balanced`, `voice`, or `music`.",
            )
        if format_id == "m4a":
            return "aac", encoding_bitrate
        return "libmp3lame", encoding_bitrate

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
