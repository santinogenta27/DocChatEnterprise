"""
Metrics Collector - Recolecta métricas de campañas
de múltiples plataformas
"""

from __future__ import annotations

from typing import Dict, Optional, Any, Tuple
from datetime import datetime, timedelta

from ...config import AppConfig
from ..utils.logger import TopAdsLogger
from ..platforms.meta_ads import MetaAdsPlatform
from ..platforms.tiktok_ads import TikTokAdsPlatform


class MetricsCollector:
    """
    Recolector de métricas de campañas publicitarias.
    
    Recolecta métricas de:
    - Meta Ads
    - TikTok Ads
    
    Métricas principales:
    - Impressions
    - Clicks
    - CTR (Click-through rate)
    - CPC (Cost per click)
    - CPA (Cost per acquisition)
    - ROAS (Return on ad spend)
    - Conversions
    - Spend
    """
    
    def __init__(
        self,
        config: AppConfig,
        meta_ads: MetaAdsPlatform,
        tiktok_ads: TikTokAdsPlatform,
        logger: TopAdsLogger
    ):
        self.config = config
        self.meta_ads = meta_ads
        self.tiktok_ads = tiktok_ads
        self.logger = logger
    
    def collect_campaign_metrics(
        self,
        campaign_id: str,
        platform: str,
        date_range: Optional[Tuple[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Recolecta métricas de una campaña.
        
        Args:
            campaign_id: ID de la campaña
            platform: "meta" o "tiktok"
            date_range: Rango de fechas (opcional)
        
        Returns:
            Diccionario con métricas
        """
        self.logger.info(f"Recolectando métricas: {platform} - {campaign_id}")
        
        if platform == "meta":
            metrics = self.meta_ads.get_campaign_metrics(campaign_id, date_range)
        elif platform == "tiktok":
            metrics = self.tiktok_ads.get_campaign_metrics(campaign_id, date_range)
        else:
            raise ValueError(f"Plataforma no soportada: {platform}")
        
        # Calcular métricas derivadas
        if metrics:
            metrics = self._calculate_derived_metrics(metrics)
        
        return metrics
    
    def collect_multiple_campaigns_metrics(
        self,
        campaign_ids: Dict[str, List[str]],
        date_range: Optional[Tuple[str, str]] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Recolecta métricas de múltiples campañas.
        
        Args:
            campaign_ids: Dict con formato {"meta": [id1, id2], "tiktok": [id3]}
            date_range: Rango de fechas
        
        Returns:
            Diccionario con métricas por plataforma y campaña
        """
        all_metrics = {}
        
        for platform, ids in campaign_ids.items():
            all_metrics[platform] = {}
            for campaign_id in ids:
                try:
                    metrics = self.collect_campaign_metrics(
                        campaign_id=campaign_id,
                        platform=platform,
                        date_range=date_range
                    )
                    all_metrics[platform][campaign_id] = metrics
                except Exception as e:
                    self.logger.error(f"Error recolectando métricas de {campaign_id}: {e}")
                    continue
        
        return all_metrics
    
    def _calculate_derived_metrics(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Calcula métricas derivadas."""
        # Calcular CPA si hay conversiones y spend
        if metrics.get("conversions", 0) > 0 and metrics.get("spend", 0) > 0:
            metrics["cpa"] = metrics["spend"] / metrics["conversions"]
        else:
            metrics["cpa"] = 0.0
        
        # Calcular ROAS (asumiendo valor promedio por conversión)
        # En producción, esto vendría de datos reales
        avg_order_value = 50.0  # Valor promedio por conversión
        if metrics.get("conversions", 0) > 0 and metrics.get("spend", 0) > 0:
            revenue = metrics["conversions"] * avg_order_value
            metrics["roas"] = revenue / metrics["spend"]
        else:
            metrics["roas"] = 0.0
        
        # Calcular CTR si hay clicks e impressions
        if metrics.get("impressions", 0) > 0:
            metrics["ctr"] = (metrics.get("clicks", 0) / metrics["impressions"]) * 100
        else:
            metrics["ctr"] = 0.0
        
        # Calcular CPC si hay clicks y spend
        if metrics.get("clicks", 0) > 0:
            metrics["cpc"] = metrics.get("spend", 0) / metrics["clicks"]
        else:
            metrics["cpc"] = 0.0
        
        return metrics


