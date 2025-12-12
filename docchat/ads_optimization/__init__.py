"""Ads Optimization Engine - Módulo de optimización de anuncios"""

from .models import (
    BaseCTRPredictor,
    SoWideV2Predictor,
    XGBoostCTRPredictor,
    ModelManager
)
from .database import (
    DatabaseManager,
    CreativeAssetDB,
    AdVariationDB,
    CampaignDB,
    PerformanceMetricsDB
)
from .engine_production import ProductionAdsOptimizationEngine
from .tenant_manager import TenantManager, Tenant
from .billing import BillingManager
from .auth import AuthManager, User, Role, Permission
from .caching import CacheManager, PredictionCache, APICache
from .monitoring import MonitoringSystem, AlertManager
from .google_ads_integration import GoogleAdsIntegration

__all__ = [
    # Models
    "BaseCTRPredictor",
    "SoWideV2Predictor",
    "XGBoostCTRPredictor",
    "ModelManager",
    # Database
    "DatabaseManager",
    "CreativeAssetDB",
    "AdVariationDB",
    "CampaignDB",
    "PerformanceMetricsDB",
    # Production Engine
    "ProductionAdsOptimizationEngine",
    # Tenant & Billing
    "TenantManager",
    "Tenant",
    "BillingManager",
    # Auth
    "AuthManager",
    "User",
    "Role",
    "Permission",
    # Caching
    "CacheManager",
    "PredictionCache",
    "APICache",
    # Monitoring
    "MonitoringSystem",
    "AlertManager",
    # Integrations
    "GoogleAdsIntegration"
]

