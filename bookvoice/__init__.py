"""Top-level package for Bookvoice.

This package provides a deterministic scaffold for converting text-based PDF books
into Czech audiobook outputs. The main orchestration entry point is
`BookvoicePipeline`.
"""

from .pipeline import BookvoicePipeline

__all__ = ["BookvoicePipeline", "__version__"]

__version__ = "0.1.55"
