"""
Tipos compartidos para Top Ads Mode.
Evita importaciones circulares moviendo enums y dataclasses aquí.
"""

from enum import Enum
from dataclasses import dataclass
from typing import List, Dict, Optional, Any


class AutonomyMode(Enum):
    """Modos de autonomía del agente."""
    FULL_AUTONOMOUS = "full_autonomous"  # 🔴 100% autónomo
    APPROVAL_REQUIRED = "approval_required"  # 🟡 Human-in-the-loop
    RECOMMENDATION_ONLY = "recommendation_only"  # 🟢 Solo recomendaciones


class CampaignObjective(Enum):
    """Objetivos de campaña publicitaria."""
    CONVERSIONS = "conversions"
    LEADS = "leads"
    TRAFFIC = "traffic"
    ENGAGEMENT = "engagement"
    AWARENESS = "awareness"
    APP_INSTALLS = "app_installs"
    VIDEO_VIEWS = "video_views"


@dataclass
class UserInput:
    """Input del usuario para crear campaña."""
    images: List[str] = None  # Paths a imágenes
    videos: List[str] = None  # Paths a videos
    texts: List[str] = None  # Textos base / copys
    business_objective: CampaignObjective = CampaignObjective.CONVERSIONS
    budget: float = 100.0  # Presupuesto diario en USD
    autonomy_mode: AutonomyMode = AutonomyMode.FULL_AUTONOMOUS
    target_audience: Optional[Dict[str, Any]] = None
    campaign_name: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class CampaignResult:
    """Resultado de creación de campaña."""
    campaign_id: str
    platform: str  # "meta" o "tiktok"
    ad_set_ids: List[str]
    ad_ids: List[str]
    status: str
    created_at: str
    estimated_reach: Optional[int] = None
    estimated_impressions: Optional[int] = None


@dataclass
class CampaignMetrics:
    """Métricas de performance de campaña."""
    campaign_id: str
    platform: str
    impressions: int
    clicks: int
    ctr: float  # Click-through rate
    cpc: float  # Cost per click
    cpa: float  # Cost per acquisition
    roas: float  # Return on ad spend
    conversions: int
    spend: float
    timestamp: str



