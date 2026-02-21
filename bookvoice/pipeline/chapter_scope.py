"""Chapter-scope resolution helpers for Bookvoice pipeline.

Responsibilities:
- Parse user chapter selection expressions.
- Reconstruct chapter selection scope from manifest metadata.
- Build deterministic chapter-scope metadata used across artifacts.
"""

from __future__ import annotations

from ..errors import PipelineStageError
from ..models.datatypes import Chapter
from ..text.chapter_selection import (
    format_chapter_selection,
    parse_chapter_indices_csv,
    parse_chapter_selection,
)


class PipelineChapterScopeMixin:
    """Provide chapter-selection and chapter-scope helper methods."""

    def _resolve_chapter_scope(
        self, chapters: list[Chapter], chapter_selection: str | None
    ) -> tuple[list[Chapter], dict[str, str]]:
        """Resolve selected chapters for a run from chapter selection expression."""

        available_indices = [chapter.index for chapter in chapters]
        try:
            selected_indices = parse_chapter_selection(chapter_selection, available_indices)
        except ValueError as exc:
            raise PipelineStageError(
                stage="chapter-selection",
                detail=str(exc),
                hint=(
                    "Use `--chapters` syntax like `5`, `1,3,7`, `2-4`, or mixed `1,3-5`."
                ),
            ) from exc

        chapter_scope = self._build_chapter_scope_metadata(
            available_indices=available_indices,
            selected_indices=selected_indices,
            selection_input=chapter_selection,
        )
        selected_set = set(selected_indices)
        selected_chapters = sorted(
            (chapter for chapter in chapters if chapter.index in selected_set),
            key=lambda chapter: chapter.index,
        )
        return selected_chapters, chapter_scope

    def _resolve_resume_chapter_scope(
        self, chapters: list[Chapter], extra: dict[str, object]
    ) -> tuple[list[Chapter], dict[str, str]]:
        """Resolve selected chapters for resume from persisted manifest metadata."""

        available_indices = [chapter.index for chapter in chapters]
        selected_indices = available_indices
        selection_input = ""

        raw_indices_csv = extra.get("chapter_scope_indices_csv")
        if isinstance(raw_indices_csv, str) and raw_indices_csv.strip():
            try:
                selected_indices = parse_chapter_indices_csv(raw_indices_csv, available_indices)
            except ValueError as exc:
                raise PipelineStageError(
                    stage="resume-artifacts",
                    detail=f"Invalid chapter scope metadata in manifest: {exc}",
                    hint="Regenerate run artifacts or rerun `bookvoice build`.",
                ) from exc
            selection_input = format_chapter_selection(selected_indices)
        else:
            raw_selection_input = extra.get("chapter_scope_selection_input")
            if (
                isinstance(raw_selection_input, str)
                and raw_selection_input.strip()
                and raw_selection_input.strip().lower() != "all"
            ):
                selection_input = raw_selection_input.strip()
                try:
                    selected_indices = parse_chapter_selection(selection_input, available_indices)
                except ValueError as exc:
                    raise PipelineStageError(
                        stage="resume-artifacts",
                        detail=f"Invalid chapter scope metadata in manifest: {exc}",
                        hint="Regenerate run artifacts or rerun `bookvoice build`.",
                    ) from exc

        chapter_scope = self._build_chapter_scope_metadata(
            available_indices=available_indices,
            selected_indices=selected_indices,
            selection_input=selection_input or None,
        )
        selected_set = set(selected_indices)
        selected_chapters = sorted(
            (chapter for chapter in chapters if chapter.index in selected_set),
            key=lambda chapter: chapter.index,
        )
        return selected_chapters, chapter_scope

    def _build_chapter_scope_metadata(
        self,
        available_indices: list[int],
        selected_indices: list[int],
        selection_input: str | None,
    ) -> dict[str, str]:
        """Build string metadata describing selected chapter scope for artifacts."""

        available_unique = sorted(set(int(index) for index in available_indices))
        selected_unique = sorted(set(int(index) for index in selected_indices))
        is_all_scope = selected_unique == available_unique
        selection_label = "all" if is_all_scope else format_chapter_selection(selected_unique)
        return {
            "chapter_scope_mode": "all" if is_all_scope else "selected",
            "chapter_scope_label": selection_label,
            "chapter_scope_selection_input": (
                "all"
                if is_all_scope
                else (selection_input.strip() if isinstance(selection_input, str) else "")
            ),
            "chapter_scope_indices_csv": ",".join(str(index) for index in selected_unique),
            "chapter_scope_available_indices_csv": ",".join(
                str(index) for index in available_unique
            ),
            "chapter_scope_selected_count": str(len(selected_unique)),
            "chapter_scope_available_count": str(len(available_unique)),
        }
