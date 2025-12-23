"""
Módulo para control básico de campañas: pausar y activar
Versión simple MVP
"""
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


def pause_campaign(
    mode_instance,
    campaign_id: str
) -> Dict[str, Any]:
    """
    Pausa una campaña completa usando la API de Meta/Google
    
    Args:
        mode_instance: Instancia de AdvertisingTopManagerMode
        campaign_id: ID interno de campaña
    
    Returns:
        Dict con resultado de la operación
    """
    if not mode_instance:
        return {"success": False, "error": "Mode instance no disponible"}
    
    try:
        # Obtener información de la campaña
        campaign = mode_instance.db_manager.get_campaign(campaign_id)
        if not campaign:
            return {"success": False, "error": f"Campaña {campaign_id} no encontrada"}
        
        platform_campaign_ids = campaign.get("platform_campaign_ids", {})
        platforms = campaign.get("platforms", "")
        
        paused_platforms = []
        errors = []
        
        # Pausar campaña en Meta si está disponible
        if "meta" in platforms and "meta" in platform_campaign_ids and mode_instance.agent:
            try:
                meta_service = getattr(mode_instance.agent, 'meta_service', None)
                if meta_service:
                    meta_campaign_id = platform_campaign_ids["meta"]
                    # Meta permite pausar campañas directamente usando Campaign.update
                    try:
                        from facebook_business.adobjects.campaign import Campaign
                        from facebook_business.exceptions import FacebookRequestError
                        
                        campaign_obj = Campaign(meta_campaign_id)
                        campaign_obj.update({'status': 'PAUSED'})
                        paused_platforms.append("Meta")
                        logger.info(f"✅ Campaña Meta pausada: {meta_campaign_id}")
                    except FacebookRequestError as e:
                        logger.error(f"Error pausando campaña Meta: {e}")
                        errors.append(f"Meta: {str(e)}")
                    except Exception as e:
                        logger.error(f"Error pausando campaña Meta: {e}")
                        errors.append(f"Meta: {str(e)}")
            except Exception as e:
                logger.error(f"Error pausando campaña de Meta: {e}")
                errors.append(f"Meta: {str(e)}")
        
        # Pausar campaña en Google si está disponible
        if "google" in platforms and "google" in platform_campaign_ids and mode_instance.agent:
            try:
                google_service = getattr(mode_instance.agent, 'google_service', None)
                if google_service:
                    google_campaign_id = platform_campaign_ids["google"]
                    # Google también permite pausar campañas directamente
                    try:
                        from google.ads.googleads.errors import GoogleAdsException
                        
                        campaign_service = google_service.client.get_service("CampaignService")
                        campaign_operation = google_service.client.get_type("CampaignOperation")
                        campaign = campaign_operation.update
                        campaign.resource_name = google_campaign_id
                        
                        from google.ads.googleads.v14.enums.types.campaign_status import CampaignStatusEnum
                        campaign.status = CampaignStatusEnum.CampaignStatus.PAUSED
                        
                        campaign_service.mutate_campaigns(
                            customer_id=google_service.customer_id,
                            operations=[campaign_operation]
                        )
                        paused_platforms.append("Google")
                        logger.info(f"✅ Campaña Google pausada: {google_campaign_id}")
                    except GoogleAdsException as e:
                        logger.error(f"Error pausando campaña Google: {e}")
                        errors.append(f"Google: {str(e)}")
                    except Exception as e:
                        logger.error(f"Error pausando campaña Google: {e}")
                        errors.append(f"Google: {str(e)}")
            except Exception as e:
                logger.error(f"Error pausando campaña de Google: {e}")
                errors.append(f"Google: {str(e)}")
        
        # Actualizar estado de campaña en BD
        try:
            _update_campaign_status(mode_instance.db_manager, campaign_id, "paused")
        except Exception as e:
            logger.error(f"Error actualizando estado de campaña en BD: {e}")
            errors.append(f"BD: {str(e)}")
        
        if paused_platforms or not errors:
            return {
                "success": True,
                "campaign_id": campaign_id,
                "platforms_paused": paused_platforms,
                "errors": errors if errors else None
            }
        else:
            return {
                "success": False,
                "error": f"No se pudieron pausar campañas. Errores: {errors}"
            }
        
    except Exception as e:
        logger.error(f"Error en pause_campaign: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e)
        }


def activate_campaign(
    mode_instance,
    campaign_id: str
) -> Dict[str, Any]:
    """
    Activa una campaña completa usando la API de Meta/Google
    
    Args:
        mode_instance: Instancia de AdvertisingTopManagerMode
        campaign_id: ID interno de campaña
    
    Returns:
        Dict con resultado de la operación
    """
    if not mode_instance:
        return {"success": False, "error": "Mode instance no disponible"}
    
    try:
        # Obtener información de la campaña
        campaign = mode_instance.db_manager.get_campaign(campaign_id)
        if not campaign:
            return {"success": False, "error": f"Campaña {campaign_id} no encontrada"}
        
        platform_campaign_ids = campaign.get("platform_campaign_ids", {})
        platforms = campaign.get("platforms", "")
        
        activated_platforms = []
        errors = []
        
        # Activar campaña en Meta si está disponible
        if "meta" in platforms and "meta" in platform_campaign_ids and mode_instance.agent:
            try:
                meta_service = getattr(mode_instance.agent, 'meta_service', None)
                if meta_service:
                    meta_campaign_id = platform_campaign_ids["meta"]
                    # Meta permite activar campañas directamente usando Campaign.update
                    try:
                        from facebook_business.adobjects.campaign import Campaign
                        from facebook_business.exceptions import FacebookRequestError
                        
                        campaign_obj = Campaign(meta_campaign_id)
                        campaign_obj.update({'status': 'ACTIVE'})
                        activated_platforms.append("Meta")
                        logger.info(f"✅ Campaña Meta activada: {meta_campaign_id}")
                    except FacebookRequestError as e:
                        logger.error(f"Error activando campaña Meta: {e}")
                        errors.append(f"Meta: {str(e)}")
                    except Exception as e:
                        logger.error(f"Error activando campaña Meta: {e}")
                        errors.append(f"Meta: {str(e)}")
            except Exception as e:
                logger.error(f"Error activando campaña de Meta: {e}")
                errors.append(f"Meta: {str(e)}")
        
        # Activar campaña en Google si está disponible
        if "google" in platforms and "google" in platform_campaign_ids and mode_instance.agent:
            try:
                google_service = getattr(mode_instance.agent, 'google_service', None)
                if google_service:
                    google_campaign_id = platform_campaign_ids["google"]
                    # Google también permite activar campañas directamente
                    try:
                        from google.ads.googleads.errors import GoogleAdsException
                        
                        campaign_service = google_service.client.get_service("CampaignService")
                        campaign_operation = google_service.client.get_type("CampaignOperation")
                        campaign = campaign_operation.update
                        campaign.resource_name = google_campaign_id
                        
                        from google.ads.googleads.v14.enums.types.campaign_status import CampaignStatusEnum
                        campaign.status = CampaignStatusEnum.CampaignStatus.ENABLED
                        
                        campaign_service.mutate_campaigns(
                            customer_id=google_service.customer_id,
                            operations=[campaign_operation]
                        )
                        activated_platforms.append("Google")
                        logger.info(f"✅ Campaña Google activada: {google_campaign_id}")
                    except GoogleAdsException as e:
                        logger.error(f"Error activando campaña Google: {e}")
                        errors.append(f"Google: {str(e)}")
                    except Exception as e:
                        logger.error(f"Error activando campaña Google: {e}")
                        errors.append(f"Google: {str(e)}")
            except Exception as e:
                logger.error(f"Error activando campaña de Google: {e}")
                errors.append(f"Google: {str(e)}")
        
        # Actualizar estado de campaña en BD
        try:
            _update_campaign_status(mode_instance.db_manager, campaign_id, "active")
        except Exception as e:
            logger.error(f"Error actualizando estado de campaña en BD: {e}")
            errors.append(f"BD: {str(e)}")
        
        if activated_platforms or not errors:
            return {
                "success": True,
                "campaign_id": campaign_id,
                "platforms_activated": activated_platforms,
                "errors": errors if errors else None
            }
        else:
            return {
                "success": False,
                "error": f"No se pudieron activar campañas. Errores: {errors}"
            }
        
    except Exception as e:
        logger.error(f"Error en activate_campaign: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e)
        }


def _get_campaign_ads(
    db_manager,
    campaign_id: str,
    platform: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Obtiene todos los ads asociados a una campaña
    
    Args:
        db_manager: Instancia de DatabaseManager
        campaign_id: ID de campaña
        platform: Plataforma opcional (meta, google)
    
    Returns:
        Lista de ads
    """
    if not db_manager or not hasattr(db_manager, 'SQLALCHEMY_AVAILABLE') or not db_manager.SQLALCHEMY_AVAILABLE:
        return []
    
    try:
        from .database import AdDB
        
        session = db_manager.get_session()
        if not session:
            return []
        
        query = session.query(AdDB).filter(AdDB.campaign_id == campaign_id)
        
        if platform:
            query = query.filter(AdDB.platform == platform)
        
        ads = query.all()
        
        results = []
        for ad in ads:
            results.append({
                "ad_id": ad.ad_id,
                "platform_ad_id": ad.platform_ad_id,
                "platform": ad.platform,
                "status": ad.status,
                "creative_id": ad.creative_id
            })
        
        session.close()
        return results
        
    except Exception as e:
        logger.error(f"Error obteniendo ads de campaña: {e}")
        return []


def _update_campaign_status(
    db_manager,
    campaign_id: str,
    status: str
) -> bool:
    """
    Actualiza el estado de una campaña en la BD
    
    Args:
        db_manager: Instancia de DatabaseManager
        campaign_id: ID de campaña
        status: Nuevo estado (active, paused, etc.)
    
    Returns:
        True si se actualizó correctamente
    """
    if not db_manager or not hasattr(db_manager, 'SQLALCHEMY_AVAILABLE') or not db_manager.SQLALCHEMY_AVAILABLE:
        return False
    
    try:
        from .database import CampaignDB
        from datetime import datetime
        
        session = db_manager.get_session()
        if not session:
            return False
        
        campaign = session.query(CampaignDB).filter(CampaignDB.campaign_id == campaign_id).first()
        if campaign:
            campaign.status = status
            campaign.updated_at = datetime.utcnow()
            session.commit()
            session.close()
            return True
        
        session.close()
        return False
        
    except Exception as e:
        logger.error(f"Error actualizando estado de campaña: {e}")
        return False

