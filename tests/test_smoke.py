"""Basic smoke tests for project wiring.

These tests intentionally verify only import-level and basic object creation
behavior for the initial scaffold.
"""

from pathlib import Path

from bookvoice.config import BookvoiceConfig
from bookvoice.pipeline import BookvoicePipeline


def test_pipeline_can_be_instantiated() -> None:
    """Pipeline class should be constructible."""

    pipeline = BookvoicePipeline()
    assert pipeline is not None


def test_config_dataclass_defaults() -> None:
    """Config should keep expected defaults for MVP scaffolding."""

    config = BookvoiceConfig(input_pdf=Path("input.pdf"), output_dir=Path("out"))
    assert config.language == "cs"
    assert config.chunk_size_chars > 0
