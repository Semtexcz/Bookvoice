"""Shared pytest fixtures for the full Bookvoice test suite."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.fixture_paths import (
    canonical_content_pdf_fixture_path as resolve_canonical_content_pdf_fixture_path,
)


@pytest.fixture
def canonical_content_pdf_fixture_path() -> Path:
    """Provide the canonical content PDF fixture path for tests that need real PDF input."""

    return resolve_canonical_content_pdf_fixture_path()
