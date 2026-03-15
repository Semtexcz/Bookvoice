"""Reader-export contract helpers for translate-only pipeline mode.

Responsibilities:
- Parse reader-export format intent from config metadata.
- Build deterministic planned output metadata for manifest auditing.
- Keep reader-export naming/layout stable across replayed runs.
"""

from __future__ import annotations

from pathlib import Path
import re
from typing import Mapping


_READER_EXPORT_FORMAT_ORDER = ("epub", "pdf")
_READER_EXPORT_FORMATS = frozenset(_READER_EXPORT_FORMAT_ORDER)


def resolve_reader_export_formats(value: str | None) -> tuple[str, ...]:
    """Resolve canonical reader-export formats from config/CLI input."""

    if value is None:
        return tuple()
    normalized = value.strip().lower()
    if not normalized or normalized == "none":
        return tuple()

    tokens = [token.strip().lower() for token in normalized.split(",") if token.strip()]
    if not tokens:
        raise ValueError("Reader export format list cannot be empty.")

    token_set = set(tokens)
    if "none" in token_set and len(token_set) > 1:
        raise ValueError("Reader export format `none` cannot be combined with other formats.")

    invalid = sorted(token for token in token_set if token not in _READER_EXPORT_FORMATS)
    if invalid:
        values = ", ".join(invalid)
        raise ValueError(
            "Unsupported reader export format "
            f"`{values}`. Supported: `epub`, `pdf`, or `epub,pdf`."
        )

    return tuple(fmt for fmt in _READER_EXPORT_FORMAT_ORDER if fmt in token_set)


def reader_export_formats_csv(formats: tuple[str, ...]) -> str:
    """Serialize canonical reader-export format tuple to metadata string form."""

    if not formats:
        return "none"
    return ",".join(formats)


def reader_export_manifest_metadata(
    *,
    run_root: Path,
    source_path: Path,
    language: str,
    chapter_scope: Mapping[str, str],
    formats: tuple[str, ...],
) -> dict[str, str]:
    """Build deterministic manifest metadata for requested reader exports."""

    requested = bool(formats)
    output_dir = run_root / "reader"
    language_token = _slug_token(language, fallback="lang")
    source_token = _slug_token(source_path.stem, fallback="document")
    scope_token = _scope_token(chapter_scope)
    basename = f"{source_token}.{language_token}.{scope_token}.translated"

    planned_paths = [str(output_dir / f"{basename}.{fmt}") for fmt in formats]
    metadata: dict[str, str] = {
        "reader_export_requested": "true" if requested else "false",
        "reader_export_formats_csv": reader_export_formats_csv(formats),
        "reader_export_content_source": "translations",
        "reader_export_rewrite_policy": "audio_rewrite_not_applied",
        "reader_export_output_dir": str(output_dir),
        "reader_export_basename": basename,
        "reader_export_status": "planned_only",
        "reader_export_planned_count": str(len(formats)),
        "reader_export_planned_paths_csv": ",".join(planned_paths),
    }
    if "epub" in formats:
        metadata["reader_export_planned_epub"] = str(output_dir / f"{basename}.epub")
    if "pdf" in formats:
        metadata["reader_export_planned_pdf"] = str(output_dir / f"{basename}.pdf")
    return metadata


def _scope_token(chapter_scope: Mapping[str, str]) -> str:
    """Create a stable filename-safe scope token from chapter scope metadata."""

    mode = chapter_scope.get("chapter_scope_mode", "").strip().lower()
    if mode == "all":
        return "all"

    indices_csv = chapter_scope.get("chapter_scope_indices_csv", "").strip()
    if not indices_csv:
        return "selected"
    normalized = re.sub(r"[^0-9]+", "-", indices_csv).strip("-")
    if not normalized:
        return "selected"
    return f"chapters-{normalized}"


def _slug_token(value: str, *, fallback: str) -> str:
    """Normalize values into ASCII-like filename tokens."""

    normalized = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    if not normalized:
        return fallback
    return normalized
