"""
Módulo simple para obtener métricas reales de Meta y Google Ads API
Versión MVP - Solo lo esencial
"""
from __future__ import annotations

from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


def get_meta_campaign_metrics(
    meta_service,
    campaign_id: str,
    date_range: Optional[int] = 30
) -> Dict[str, Any]:
    """
    Obtiene métricas reales de Meta Ads API - VERSIÓN SIMPLE MVP
    
    Args:
        meta_service: Instancia de MetaAdsService
        campaign_id: ID de campaña en Meta (platform_campaign_id)
        date_range: Días hacia atrás (default 30)
    
    Returns:
        Dict con métricas: impressions, clicks, spend, conversions, ctr, cpc
    """
    if not meta_service:
        logger.warning("MetaAdsService no disponible")
        return {
            "impressions": 0,
            "clicks": 0,
            "spend": 0.0,
            "conversions": 0,
            "ctr": 0.0,
            "cpc": 0.0
        }
    
    try:
        # Meta usa date_preset en lugar de fechas específicas
        # Mapear días a presets comunes de Meta
        if date_range <= 7:
            date_preset = "last_7d"
        elif date_range <= 28:
            date_preset = "last_28d"
        elif date_range <= 90:
            date_preset = "last_90d"
        else:
            date_preset = "lifetime"
        
        # Llamar al método existente del servicio
        metrics = meta_service.get_campaign_metrics(
            campaign_id=campaign_id,
            date_preset=date_preset
        )
        
        # Extraer métricas básicas
        impressions = int(metrics.get("impressions", 0))
        clicks = int(metrics.get("clicks", 0))
        spend = float(metrics.get("spend", 0.0))
        conversions = int(metrics.get("conversions", 0))
        
        # Meta devuelve CTR como decimal (ej: 0.025 = 2.5%), pero verificamos y convertimos
        # Meta devuelve CPC en dólares directamente
        ctr_raw = float(metrics.get("ctr", 0.0))
        if ctr_raw > 0:
            # Si CTR viene como decimal (ej: 0.025), convertimos a porcentaje
            # Si ya viene como porcentaje (ej: 2.5), lo usamos tal cual
            ctr = ctr_raw * 100 if ctr_raw < 1 else ctr_raw
        elif impressions > 0:
            ctr = (clicks / impressions) * 100  # Calcular si no viene
        else:
            ctr = 0.0
        
        cpc = float(metrics.get("cpc", 0.0))
        if cpc == 0.0 and clicks > 0:
            cpc = spend / clicks  # Calcular si no viene
        
        return {
            "impressions": impressions,
            "clicks": clicks,
            "spend": round(spend, 2),
            "conversions": conversions,
            "ctr": round(ctr, 2),
            "cpc": round(cpc, 2)
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo métricas de Meta: {e}")
        import traceback
        traceback.print_exc()
        return {
            "impressions": 0,
            "clicks": 0,
            "spend": 0.0,
            "conversions": 0,
            "ctr": 0.0,
            "cpc": 0.0,
            "error": str(e)
        }


def get_google_campaign_metrics(
    google_service,
    campaign_id: str,
    date_range: Optional[int] = 30
) -> Dict[str, Any]:
    """
    Obtiene métricas reales de Google Ads API - VERSIÓN SIMPLE MVP
    
    Args:
        google_service: Instancia de GoogleAdsService
        campaign_id: Resource name de campaña en Google (ej: customers/123/campaigns/456)
        date_range: Días hacia atrás (default 30)
    
    Returns:
        Dict con métricas: impressions, clicks, spend, conversions, ctr, cpc
    """
    if not google_service:
        logger.warning("GoogleAdsService no disponible")
        return {
            "impressions": 0,
            "clicks": 0,
            "spend": 0.0,
            "conversions": 0,
            "ctr": 0.0,
            "cpc": 0.0
        }
    
    try:
        # Calcular fechas
        end_date = datetime.now()
        start_date = end_date - timedelta(days=date_range or 30)
        
        # Llamar al método existente del servicio (acepta datetime)
        metrics = google_service.get_campaign_metrics(
            campaign_resource_name=campaign_id,
            start_date=start_date,
            end_date=end_date
        )
        
        # Extraer métricas básicas (Google ya calcula spend desde cost_micros)
        impressions = int(metrics.get("impressions", 0))
        clicks = int(metrics.get("clicks", 0))
        spend = float(metrics.get("spend", 0.0))  # Google ya lo calcula en el servicio
        conversions = int(metrics.get("conversions", 0))
        
        # Google ya devuelve CTR y CPC calculados, pero verificamos y recalculamos si es necesario
        ctr = float(metrics.get("ctr", 0.0))
        if ctr == 0.0 and impressions > 0:
            ctr = (clicks / impressions) * 100  # Porcentaje
        
        cpc = float(metrics.get("cpc", 0.0))
        if cpc == 0.0 and clicks > 0:
            cpc = spend / clicks
        
        return {
            "impressions": impressions,
            "clicks": clicks,
            "spend": round(spend, 2),
            "conversions": conversions,
            "ctr": round(ctr, 2),
            "cpc": round(cpc, 2)
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo métricas de Google: {e}")
        import traceback
        traceback.print_exc()
        return {
            "impressions": 0,
            "clicks": 0,
            "spend": 0.0,
            "conversions": 0,
            "ctr": 0.0,
            "cpc": 0.0,
            "error": str(e)
        }


def fetch_and_save_campaign_metrics(
    mode_instance,
    campaign_id: str,
    date_range: int = 30
) -> Dict[str, Any]:
    """
    Obtiene métricas reales de todas las plataformas y las guarda en BD
    
    Args:
        mode_instance: Instancia de AdvertisingTopManagerMode
        campaign_id: ID interno de campaña
        date_range: Días hacia atrás
    
    Returns:
        Dict con resumen de métricas obtenidas
    """
    if not mode_instance:
        return {"error": "Mode instance no disponible"}
    
    try:
        # Obtener información de la campaña
        campaign = mode_instance.db_manager.get_campaign(campaign_id)
        if not campaign:
            return {"error": f"Campaña {campaign_id} no encontrada"}
        
        platform_campaign_ids = campaign.get("platform_campaign_ids", {})
        platforms = campaign.get("platforms", "")
        
        total_metrics = {
            "impressions": 0,
            "clicks": 0,
            "spend": 0.0,
            "conversions": 0,
            "ctr": 0.0,
            "cpc": 0.0
        }
        
        # Obtener métricas de Meta si está disponible
        if "meta" in platforms and "meta" in platform_campaign_ids:
            meta_campaign_id = platform_campaign_ids["meta"]
            try:
                # Obtener meta_service del agent
                meta_service = None
                if hasattr(mode_instance, 'agent') and mode_instance.agent:
                    if hasattr(mode_instance.agent, 'meta_service'):
                        meta_service = mode_instance.agent.meta_service
                
                meta_metrics = get_meta_campaign_metrics(
                    meta_service,
                    meta_campaign_id,
                    date_range
                )
                
                # Agregar a totales
                total_metrics["impressions"] += meta_metrics.get("impressions", 0)
                total_metrics["clicks"] += meta_metrics.get("clicks", 0)
                total_metrics["spend"] += meta_metrics.get("spend", 0.0)
                total_metrics["conversions"] += meta_metrics.get("conversions", 0)
                
                # Guardar métricas en BD
                ad_id = f"meta_{campaign_id}"
                mode_instance.db_manager.save_metrics(
                    ad_id=ad_id,
                    campaign_id=campaign_id,
                    platform="meta",
                    metrics=meta_metrics
                )
                
                logger.info(f"✅ Métricas de Meta obtenidas y guardadas para campaña {campaign_id}")
                
            except Exception as e:
                logger.error(f"Error obteniendo métricas de Meta: {e}")
        
        # Obtener métricas de Google si está disponible
        if "google" in platforms and "google" in platform_campaign_ids:
            google_campaign_id = platform_campaign_ids["google"]
            try:
                # Obtener google_service del agent
                google_service = None
                if hasattr(mode_instance, 'agent') and mode_instance.agent:
                    if hasattr(mode_instance.agent, 'google_service'):
                        google_service = mode_instance.agent.google_service
                
                google_metrics = get_google_campaign_metrics(
                    google_service,
                    google_campaign_id,
                    date_range
                )
                
                # Agregar a totales
                total_metrics["impressions"] += google_metrics.get("impressions", 0)
                total_metrics["clicks"] += google_metrics.get("clicks", 0)
                total_metrics["spend"] += google_metrics.get("spend", 0.0)
                total_metrics["conversions"] += google_metrics.get("conversions", 0)
                
                # Guardar métricas en BD
                ad_id = f"google_{campaign_id}"
                mode_instance.db_manager.save_metrics(
                    ad_id=ad_id,
                    campaign_id=campaign_id,
                    platform="google",
                    metrics=google_metrics
                )
                
                logger.info(f"✅ Métricas de Google obtenidas y guardadas para campaña {campaign_id}")
                
            except Exception as e:
                logger.error(f"Error obteniendo métricas de Google: {e}")
        
        # Calcular totales CTR y CPC
        if total_metrics["impressions"] > 0:
            total_metrics["ctr"] = (total_metrics["clicks"] / total_metrics["impressions"]) * 100
        
        if total_metrics["clicks"] > 0:
            total_metrics["cpc"] = total_metrics["spend"] / total_metrics["clicks"]
        
        total_metrics["ctr"] = round(total_metrics["ctr"], 2)
        total_metrics["cpc"] = round(total_metrics["cpc"], 2)
        total_metrics["spend"] = round(total_metrics["spend"], 2)
        
        logger.info(f"✅ Métricas totales para campaña {campaign_id}: {total_metrics}")
        
        return {
            "success": True,
            "campaign_id": campaign_id,
            "metrics": total_metrics
        }
        
    except Exception as e:
        logger.error(f"Error en fetch_and_save_campaign_metrics: {e}")
        import traceback
        traceback.print_exc()
        return {
            "error": str(e),
            "success": False
        }

