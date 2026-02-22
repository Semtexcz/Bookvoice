"""Audio postprocessing, merging, and tagging components.

This package contains scaffolds for final audio polish and metadata writing.
"""

from .merger import AudioMerger
from .packaging import AudioPackager, PackagingOptions
from .postprocess import AudioPostProcessor
from .tags import MetadataWriter

__all__ = [
    "AudioPostProcessor",
    "AudioMerger",
    "AudioPackager",
    "PackagingOptions",
    "MetadataWriter",
]
