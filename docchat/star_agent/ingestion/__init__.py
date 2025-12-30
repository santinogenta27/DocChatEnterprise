"""Sistema de Ingesta Multi-Fuente para STAR AGENT."""

from .multi_source_ingester import (
    MultiSourceIngester,
    IngestedDocument,
    WebCrawler,
    InstagramExtractor,
    FacebookExtractor,
    GoogleBusinessExtractor,
)

__all__ = [
    "MultiSourceIngester",
    "IngestedDocument",
    "WebCrawler",
    "InstagramExtractor",
    "FacebookExtractor",
    "GoogleBusinessExtractor",
]
