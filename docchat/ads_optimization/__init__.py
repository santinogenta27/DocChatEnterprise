"""
Ads Optimization Module - Módulos avanzados para optimización de anuncios
Incluye: Meta Lattice, LLM-AUCTION IRPO, Meta Hacks, Compliance, Videos, etc.
"""

from .database import DatabaseManager
from .creative_generator import CreativeGenerator, GeneratedCreative, BusinessInfo
from .video_generator import VideoGenerator, GeneratedVideo, VideoGenerationRequest
from .compliance_validator import ComplianceValidator, ComplianceLevel, ComplianceIssue
from .meta_lattice import (
    MetaLatticeOptimizer,
    LatticeZipper,
    LatticeFilter,
    LatticeKTAP,
    AttributionWindow,
    FeatureImportance
)
from .llm_auction_irpo import IRPOOptimizer, RewardModel, ResponsePair
from .meta_hacks import (
    MetaAdsHacks,
    ClusterBombConfig,
    PopularKidConfig
)
from .logging_config import setup_logging, get_logger
from .retry_logic import APIClient, APIError, RateLimitError, CircuitOpenError

__all__ = [
    "DatabaseManager",
    "CreativeGenerator",
    "GeneratedCreative",
    "BusinessInfo",
    "VideoGenerator",
    "GeneratedVideo",
    "VideoGenerationRequest",
    "ComplianceValidator",
    "ComplianceLevel",
    "ComplianceIssue",
    "MetaLatticeOptimizer",
    "LatticeZipper",
    "LatticeFilter",
    "LatticeKTAP",
    "AttributionWindow",
    "FeatureImportance",
    "IRPOOptimizer",
    "RewardModel",
    "ResponsePair",
    "MetaAdsHacks",
    "ClusterBombConfig",
    "PopularKidConfig",
    "setup_logging",
    "get_logger",
    "APIClient",
    "APIError",
    "RateLimitError",
    "CircuitOpenError"
]
