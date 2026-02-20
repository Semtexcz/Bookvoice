"""Artifact storage abstraction.

Responsibilities:
- Provide deterministic filesystem storage for text, JSON, and audio artifacts.
- Offer lookup methods used by cache and resume flows.
"""

from __future__ import annotations

from pathlib import Path


class ArtifactStore:
    """Filesystem-backed artifact store scaffold."""

    def __init__(self, root: Path) -> None:
        """Initialize the store with a root output directory."""

        self.root = root

    def save_text(self, relative_path: Path, content: str) -> Path:
        """Save text content and return final path."""

        _ = content
        return self.root / relative_path

    def save_json(self, relative_path: Path, payload: dict[str, object]) -> Path:
        """Save JSON-serializable payload and return final path."""

        _ = payload
        return self.root / relative_path

    def save_audio(self, relative_path: Path, data: bytes) -> Path:
        """Save audio bytes and return final path."""

        _ = data
        return self.root / relative_path

    def load_text(self, relative_path: Path) -> str:
        """Load text content from artifact storage."""

        _ = relative_path
        return ""

    def exists(self, relative_path: Path) -> bool:
        """Return whether the given artifact exists."""

        _ = relative_path
        return False
