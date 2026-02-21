"""Chapter splitting logic scaffold.

Responsibilities:
- Convert cleaned book text into chapter objects.
- Preserve deterministic chapter ordering and indexing.
"""

from __future__ import annotations

import re

from ..models.datatypes import Chapter


class ChapterSplitter:
    """Split raw book text into chapter records."""

    _HEADING_RE = re.compile(
        r"^(?P<title>\s*(?:chapter|kapitola)\s+(?:\d+|[ivxlcdm]+)(?:[ \t]*[:.\-][ \t]*[^\n]+|[ \t]+[^\n]+)?)\s*$",
        re.IGNORECASE | re.MULTILINE,
    )

    def split(self, text: str) -> list[Chapter]:
        """Split text into chapters.

        Uses simple heading-line heuristics for common formats:
        - `Chapter 1`
        - `CHAPTER 2: Title`
        - `Kapitola 3 - Nadpis`
        """

        if not text or not text.strip():
            return []

        normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
        matches = list(self._HEADING_RE.finditer(normalized))
        if not matches:
            return [Chapter(index=1, title="Chapter 1", text=normalized)]

        chapters: list[Chapter] = []
        chapter_index = 1

        leading_text = normalized[: matches[0].start()].strip()
        if leading_text:
            chapters.append(Chapter(index=chapter_index, title="Chapter 1", text=leading_text))
            chapter_index += 1

        for idx, match in enumerate(matches):
            content_start = match.end()
            content_end = matches[idx + 1].start() if idx + 1 < len(matches) else len(normalized)
            content = normalized[content_start:content_end].strip()

            title = " ".join(match.group("title").split())
            chapter_text = content if content else title
            chapters.append(Chapter(index=chapter_index, title=title, text=chapter_text))
            chapter_index += 1

        return chapters
