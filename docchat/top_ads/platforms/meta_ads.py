"""
Meta Ads Platform Integration
Integración real con Meta Marketing API (Facebook, Instagram, WhatsApp)
"""

from __future__ import annotations

import os
from typing import List, Dict, Optional, Any, Tuple
import requests
from datetime import datetime

try:
    from facebook_business.api import FacebookAdsApi
    from facebook_business.adobjects.campaign import Campaign
    from facebook_business.adobjects.adset import AdSet
    from facebook_business.adobjects.ad import Ad
    from facebook_business.adobjects.adcreative import AdCreative
    from facebook_business.adobjects.adimage import AdImage
    from facebook_business.adobjects.advideo import AdVideo
    FACEBOOK_BUSINESS_AVAILABLE = True
except ImportError:
    FACEBOOK_BUSINESS_AVAILABLE = False

from ...config import AppConfig
from ..utils.logger import TopAdsLogger


class MetaAdsPlatform:
    """
    Integración con Meta Marketing API.
    
    Funciones:
    - Crear campañas
    - Crear ad sets
    - Subir creativos
    - Publicar anuncios
    - Leer métricas
    - Pausar/escalar campañas
    """
    
    def __init__(
        self,
        config: AppConfig,
        logger: TopAdsLogger
    ):
        self.config = config
        self.logger = logger
        self.connected = False
        self.access_token = os.getenv("META_ACCESS_TOKEN") or config.meta_access_token if hasattr(config, 'meta_access_token') else None
        self.app_id = os.getenv("META_APP_ID") or getattr(config, 'meta_app_id', None)
        self.app_secret = os.getenv("META_APP_SECRET") or getattr(config, 'meta_app_secret', None)
        self.ad_account_id = os.getenv("META_AD_ACCOUNT_ID") or getattr(config, 'meta_ad_account_id', None)
        
        if FACEBOOK_BUSINESS_AVAILABLE and self.access_token:
            try:
                FacebookAdsApi.init(
                    access_token=self.access_token,
                    app_id=self.app_id,
                    app_secret=self.app_secret
                )
                self.connected = True
                self.logger.info("Meta Ads API inicializada correctamente")
            except Exception as e:
                self.logger.error(f"Error inicializando Meta Ads API: {e}")
                self.connected = False
        else:
            self.logger.warning("Facebook Business SDK no disponible o falta ACCESS_TOKEN")
    
    def is_connected(self) -> bool:
        """Verifica si la conexión con Meta Ads está activa."""
        return self.connected
    
    def create_campaign(
        self,
        name: str,
        objective: str,
        status: str = "PAUSED"
    ) -> str:
        """
        Crea una campaña en Meta Ads.
        
        Args:
            name: Nombre de la campaña
            objective: Objetivo (CONVERSIONS, LEADS, TRAFFIC, etc.)
            status: Estado (ACTIVE, PAUSED)
        
        Returns:
            ID de la campaña creada
        """
        if not self.connected:
            self.logger.warning("Meta Ads no conectado, simulando creación de campaña")
            return f"mock_campaign_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        try:
            # Mapear objetivo
            objective_map = {
                "conversions": Campaign.Objective.conversions,
                "leads": Campaign.Objective.lead_generation,
                "traffic": Campaign.Objective.link_clicks,
                "engagement": Campaign.Objective.post_engagement,
                "awareness": Campaign.Objective.brand_awareness,
                "app_installs": Campaign.Objective.app_installs,
                "video_views": Campaign.Objective.video_views
            }
            
            fb_objective = objective_map.get(objective.lower(), Campaign.Objective.conversions)
            
            campaign = Campaign(self.ad_account_id)
            result = campaign.create(
                params={
                    'name': name,
                    'objective': fb_objective,
                    'status': status,
                    'special_ad_categories': []
                }
            )
            
            campaign_id = result.get('id')
            self.logger.info(f"Campaña creada en Meta: {campaign_id}")
            return campaign_id
            
        except Exception as e:
            self.logger.error(f"Error creando campaña en Meta: {e}")
            raise
    
    def create_ad_set(
        self,
        campaign_id: str,
        name: str,
        budget: float,
        targeting: Dict[str, Any],
        optimization_goal: str
    ) -> str:
        """
        Crea un ad set en Meta Ads.
        
        Args:
            campaign_id: ID de la campaña
            name: Nombre del ad set
            budget: Presupuesto diario
            targeting: Configuración de targeting
            optimization_goal: Objetivo de optimización
        
        Returns:
            ID del ad set creado
        """
        if not self.connected:
            self.logger.warning("Meta Ads no conectado, simulando creación de ad set")
            return f"mock_adset_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        try:
            ad_set = AdSet(self.ad_account_id)
            
            # Construir targeting
            targeting_spec = {
                'age_min': targeting.get('age_min', 18),
                'age_max': targeting.get('age_max', 65),
                'genders': targeting.get('genders', [1, 2])
            }
            
            if 'geo_locations' in targeting:
                targeting_spec['geo_locations'] = targeting['geo_locations']
            
            if 'interests' in targeting:
                targeting_spec['interests'] = targeting['interests']
            
            result = ad_set.create(
                params={
                    'name': name,
                    'campaign_id': campaign_id,
                    'daily_budget': int(budget * 100),  # En centavos
                    'billing_event': 'IMPRESSIONS',
                    'optimization_goal': optimization_goal.upper(),
                    'targeting': targeting_spec,
                    'status': 'ACTIVE'
                }
            )
            
            ad_set_id = result.get('id')
            self.logger.info(f"Ad set creado en Meta: {ad_set_id}")
            return ad_set_id
            
        except Exception as e:
            self.logger.error(f"Error creando ad set en Meta: {e}")
            raise
    
    def upload_asset(
        self,
        asset_path: str,
        asset_type: str = "image"
    ) -> str:
        """
        Sube un asset (imagen o video) a Meta Ads.
        
        Args:
            asset_path: Path al archivo
            asset_type: "image" o "video"
        
        Returns:
            ID del asset subido
        """
        if not self.connected:
            self.logger.warning("Meta Ads no conectado, simulando subida de asset")
            return f"mock_asset_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        try:
            if asset_type == "image":
                ad_image = AdImage(self.ad_account_id)
                result = ad_image.create(
                    params={
                        'bytes': open(asset_path, 'rb').read()
                    }
                )
                return result.get('hash')
            elif asset_type == "video":
                ad_video = AdVideo(self.ad_account_id)
                result = ad_video.create(
                    params={
                        'bytes': open(asset_path, 'rb').read()
                    }
                )
                return result.get('id')
            else:
                raise ValueError(f"Tipo de asset no soportado: {asset_type}")
                
        except Exception as e:
            self.logger.error(f"Error subiendo asset a Meta: {e}")
            raise
    
    def create_ad(
        self,
        ad_set_id: str,
        name: str,
        creative: Dict[str, Any],
        status: str = "ACTIVE"
    ) -> str:
        """
        Crea un anuncio en Meta Ads.
        
        Args:
            ad_set_id: ID del ad set
            name: Nombre del anuncio
            creative: Creative con headline, primary_text, etc.
            status: Estado del anuncio
        
        Returns:
            ID del anuncio creado
        """
        if not self.connected:
            self.logger.warning("Meta Ads no conectado, simulando creación de ad")
            return f"mock_ad_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        try:
            # Crear creative primero
            ad_creative = AdCreative(self.ad_account_id)
            creative_result = ad_creative.create(
                params={
                    'name': f"{name}_creative",
                    'object_story_spec': {
                        'page_id': self.ad_account_id,  # Necesita page_id real
                        'link_data': {
                            'message': creative.get('primary_text', ''),
                            'headline': creative.get('headline', ''),
                            'description': creative.get('description', ''),
                            'call_to_action': {
                                'type': creative.get('cta', 'LEARN_MORE')
                            }
                        }
                    }
                }
            )
            creative_id = creative_result.get('id')
            
            # Crear ad
            ad = Ad(self.ad_account_id)
            result = ad.create(
                params={
                    'name': name,
                    'adset_id': ad_set_id,
                    'creative': {'creative_id': creative_id},
                    'status': status
                }
            )
            
            ad_id = result.get('id')
            self.logger.info(f"Anuncio creado en Meta: {ad_id}")
            return ad_id
            
        except Exception as e:
            self.logger.error(f"Error creando ad en Meta: {e}")
            raise
    
    def pause_campaign(self, campaign_id: str) -> bool:
        """Pausa una campaña."""
        if not self.connected:
            return True
        
        try:
            campaign = Campaign(campaign_id)
            campaign.update({'status': 'PAUSED'})
            self.logger.info(f"Campaña pausada: {campaign_id}")
            return True
        except Exception as e:
            self.logger.error(f"Error pausando campaña: {e}")
            return False
    
    def resume_campaign(self, campaign_id: str) -> bool:
        """Reanuda una campaña."""
        if not self.connected:
            return True
        
        try:
            campaign = Campaign(campaign_id)
            campaign.update({'status': 'ACTIVE'})
            self.logger.info(f"Campaña reanudada: {campaign_id}")
            return True
        except Exception as e:
            self.logger.error(f"Error reanudando campaña: {e}")
            return False
    
    def get_campaign_metrics(
        self,
        campaign_id: str,
        date_range: Optional[Tuple[str, str]] = None
    ) -> Dict[str, Any]:
        """Obtiene métricas de una campaña."""
        if not self.connected:
            return {
                "impressions": 0,
                "clicks": 0,
                "ctr": 0.0,
                "cpc": 0.0,
                "spend": 0.0
            }
        
        try:
            campaign = Campaign(campaign_id)
            insights = campaign.get_insights(
                params={
                    'fields': ['impressions', 'clicks', 'ctr', 'cpc', 'spend', 'actions']
                }
            )
            
            if insights:
                insight = insights[0]
                return {
                    "impressions": int(insight.get('impressions', 0)),
                    "clicks": int(insight.get('clicks', 0)),
                    "ctr": float(insight.get('ctr', 0)),
                    "cpc": float(insight.get('cpc', 0)),
                    "spend": float(insight.get('spend', 0)),
                    "conversions": self._extract_conversions(insight)
                }
            else:
                return {}
                
        except Exception as e:
            self.logger.error(f"Error obteniendo métricas: {e}")
            return {}
    
    def _extract_conversions(self, insight: Dict[str, Any]) -> int:
        """Extrae número de conversiones de insights."""
        actions = insight.get('actions', [])
        for action in actions:
            if action.get('action_type') == 'purchase' or action.get('action_type') == 'lead':
                return int(action.get('value', 0))
        return 0

