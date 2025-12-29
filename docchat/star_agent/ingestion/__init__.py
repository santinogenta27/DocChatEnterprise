"""Sistema de ingesta multi-fuente para STAR AGENT."""

from .multi_source_ingester import MultiSourceIngester, SourceType, IngestedDocument

__all__ = [
    "MultiSourceIngester",
    "SourceType",
    "IngestedDocument",
]

