"""
ADVERTISING TOP MANAGER - AI-Powered Autonomous Advertising Manager
====================================================================

Sistema completo de gestión de anuncios con IA que:
- Recibe imágenes/videos/textos de usuarios
- Analiza assets con visión y audio
- Genera creativos de anuncios con IA
- Publica campañas automáticamente en Meta y Google Ads
- Optimiza en tiempo real basado en métricas de desempeño

Versión: 1.0.0 (Production Ready)
"""

from .advertising_top_manager_mode import AdvertisingTopManagerMode
from .database import DatabaseManager
from .models.schemas import (
    AssetUpload,
    AssetAnalysis,
    CreativeGeneration,
    CampaignRequest,
    CampaignResponse,
    AdPerformance,
    OptimizationResult
)

__version__ = "1.0.0"
__all__ = [
    'AdvertisingTopManagerMode',
    'DatabaseManager',
    'AssetUpload',
    'AssetAnalysis',
    'CreativeGeneration',
    'CampaignRequest',
    'CampaignResponse',
    'AdPerformance',
    'OptimizationResult'
]
