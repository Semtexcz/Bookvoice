"""Artifact storage abstraction.

Responsibilities:
- Provide deterministic filesystem storage for text, JSON, and audio artifacts.
- Offer lookup methods used by cache and resume flows.
"""

from __future__ import annotations

import json
from pathlib import Path


class ArtifactStore:
    """Filesystem-backed artifact store scaffold."""

    def __init__(self, root: Path) -> None:
        """Initialize the store with a root output directory."""

        self.root = root

    def save_text(self, relative_path: Path, content: str) -> Path:
        """Save text content and return final path."""

        path = self.root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def save_json(self, relative_path: Path, payload: dict[str, object]) -> Path:
        """Save JSON-serializable payload and return final path."""

        path = self.root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return path

    def save_audio(self, relative_path: Path, data: bytes) -> Path:
        """Save audio bytes and return final path."""

        path = self.root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    def load_text(self, relative_path: Path) -> str:
        """Load text content from artifact storage."""

        path = self.root / relative_path
        return path.read_text(encoding="utf-8")

    def exists(self, relative_path: Path) -> bool:
        """Return whether the given artifact exists."""

        return (self.root / relative_path).exists()
