"""
TikTok Ads Platform Integration
Integración con TikTok Marketing API
"""

from __future__ import annotations

import os
from typing import List, Dict, Optional, Any, Tuple
import requests
from datetime import datetime

from ...config import AppConfig
from ..utils.logger import TopAdsLogger


class TikTokAdsPlatform:
    """
    Integración con TikTok Marketing API.
    
    Funciones:
    - Crear campañas
    - Crear ad groups
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
        self.access_token = os.getenv("TIKTOK_ACCESS_TOKEN") or getattr(config, 'tiktok_access_token', None)
        self.app_id = os.getenv("TIKTOK_APP_ID") or getattr(config, 'tiktok_app_id', None)
        self.app_secret = os.getenv("TIKTOK_APP_SECRET") or getattr(config, 'tiktok_app_secret', None)
        self.advertiser_id = os.getenv("TIKTOK_ADVERTISER_ID") or getattr(config, 'tiktok_advertiser_id', None)
        self.api_base_url = "https://business-api.tiktok.com/open_api/v1.3"
        
        if self.access_token and self.advertiser_id:
            self.connected = True
            self.logger.info("TikTok Ads API configurada")
        else:
            self.logger.warning("TikTok Ads API no configurada completamente")
    
    def is_connected(self) -> bool:
        """Verifica si la conexión con TikTok Ads está activa."""
        return self.connected
    
    def _make_api_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Hace una petición a la TikTok Ads API."""
        if not self.connected:
            self.logger.warning("TikTok Ads no conectado, simulando request")
            return {"code": 0, "message": "OK", "data": {}}
        
        url = f"{self.api_base_url}/{endpoint}"
        headers = {
            "Access-Token": self.access_token,
            "Content-Type": "application/json"
        }
        
        try:
            if method == "GET":
                response = requests.get(url, headers=headers, params=data)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=data)
            else:
                raise ValueError(f"Método no soportado: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            self.logger.error(f"Error en request a TikTok API: {e}")
            raise
    
    def create_campaign(
        self,
        name: str,
        objective: str,
        budget: float
    ) -> str:
        """
        Crea una campaña en TikTok Ads.
        
        Args:
            name: Nombre de la campaña
            objective: Objetivo
            budget: Presupuesto
        
        Returns:
            ID de la campaña creada
        """
        if not self.connected:
            self.logger.warning("TikTok Ads no conectado, simulando creación de campaña")
            return f"mock_tiktok_campaign_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        try:
            # Mapear objetivo
            objective_map = {
                "conversions": "CONVERSIONS",
                "leads": "LEAD_GENERATION",
                "traffic": "TRAFFIC",
                "engagement": "ENGAGEMENT",
                "awareness": "AWARENESS",
                "app_installs": "APP_INSTALL",
                "video_views": "VIDEO_VIEWS"
            }
            
            tiktok_objective = objective_map.get(objective.lower(), "CONVERSIONS")
            
            data = {
                "advertiser_id": self.advertiser_id,
                "campaign_name": name,
                "budget_mode": "BUDGET_MODE_DAY",
                "budget": budget,
                "operation_status": "ENABLE",
                "objective_type": tiktok_objective
            }
            
            result = self._make_api_request("POST", "campaign/create/", data)
            
            if result.get("code") == 0:
                campaign_id = result.get("data", {}).get("campaign_id")
                self.logger.info(f"Campaña creada en TikTok: {campaign_id}")
                return str(campaign_id)
            else:
                raise Exception(f"Error de TikTok API: {result.get('message')}")
                
        except Exception as e:
            self.logger.error(f"Error creando campaña en TikTok: {e}")
            raise
    
    def create_ad_group(
        self,
        campaign_id: str,
        name: str,
        budget: float,
        targeting: Dict[str, Any]
    ) -> str:
        """
        Crea un ad group en TikTok Ads.
        
        Args:
            campaign_id: ID de la campaña
            name: Nombre del ad group
            budget: Presupuesto
            targeting: Configuración de targeting
        
        Returns:
            ID del ad group creado
        """
        if not self.connected:
            self.logger.warning("TikTok Ads no conectado, simulando creación de ad group")
            return f"mock_tiktok_adgroup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        try:
            data = {
                "advertiser_id": self.advertiser_id,
                "campaign_id": campaign_id,
                "adgroup_name": name,
                "budget_mode": "BUDGET_MODE_DAY",
                "budget": budget,
                "operation_status": "ENABLE",
                "targeting": {
                    "age_range": [targeting.get("age_min", 18), targeting.get("age_max", 65)],
                    "genders": targeting.get("genders", [1, 2])
                }
            }
            
            result = self._make_api_request("POST", "adgroup/create/", data)
            
            if result.get("code") == 0:
                ad_group_id = result.get("data", {}).get("adgroup_id")
                self.logger.info(f"Ad group creado en TikTok: {ad_group_id}")
                return str(ad_group_id)
            else:
                raise Exception(f"Error de TikTok API: {result.get('message')}")
                
        except Exception as e:
            self.logger.error(f"Error creando ad group en TikTok: {e}")
            raise
    
    def create_ad(
        self,
        ad_group_id: str,
        name: str,
        creative: Dict[str, Any]
    ) -> str:
        """
        Crea un anuncio en TikTok Ads.
        
        Args:
            ad_group_id: ID del ad group
            name: Nombre del anuncio
            creative: Creative con headline, primary_text, etc.
        
        Returns:
            ID del anuncio creado
        """
        if not self.connected:
            self.logger.warning("TikTok Ads no conectado, simulando creación de ad")
            return f"mock_tiktok_ad_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        try:
            data = {
                "advertiser_id": self.advertiser_id,
                "adgroup_id": ad_group_id,
                "ad_name": name,
                "operation_status": "ENABLE",
                "creative": {
                    "ad_text": creative.get("primary_text", ""),
                    "ad_format": "SINGLE_VIDEO"
                }
            }
            
            result = self._make_api_request("POST", "ad/create/", data)
            
            if result.get("code") == 0:
                ad_id = result.get("data", {}).get("ad_id")
                self.logger.info(f"Anuncio creado en TikTok: {ad_id}")
                return str(ad_id)
            else:
                raise Exception(f"Error de TikTok API: {result.get('message')}")
                
        except Exception as e:
            self.logger.error(f"Error creando ad en TikTok: {e}")
            raise
    
    def pause_campaign(self, campaign_id: str) -> bool:
        """Pausa una campaña."""
        if not self.connected:
            return True
        
        try:
            data = {
                "advertiser_id": self.advertiser_id,
                "campaign_ids": [campaign_id],
                "operation_status": "DISABLE"
            }
            
            result = self._make_api_request("POST", "campaign/update/", data)
            return result.get("code") == 0
            
        except Exception as e:
            self.logger.error(f"Error pausando campaña: {e}")
            return False
    
    def resume_campaign(self, campaign_id: str) -> bool:
        """Reanuda una campaña."""
        if not self.connected:
            return True
        
        try:
            data = {
                "advertiser_id": self.advertiser_id,
                "campaign_ids": [campaign_id],
                "operation_status": "ENABLE"
            }
            
            result = self._make_api_request("POST", "campaign/update/", data)
            return result.get("code") == 0
            
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
            params = {
                "advertiser_id": self.advertiser_id,
                "campaign_ids": [campaign_id],
                "metrics": ["impressions", "clicks", "ctr", "cpc", "spend", "conversions"]
            }
            
            if date_range:
                params["start_date"] = date_range[0]
                params["end_date"] = date_range[1]
            
            result = self._make_api_request("GET", "report/integrated/get/", params)
            
            if result.get("code") == 0:
                data = result.get("data", {}).get("list", [])
                if data:
                    metrics = data[0]
                    return {
                        "impressions": int(metrics.get("impressions", 0)),
                        "clicks": int(metrics.get("clicks", 0)),
                        "ctr": float(metrics.get("ctr", 0)),
                        "cpc": float(metrics.get("cpc", 0)),
                        "spend": float(metrics.get("spend", 0)),
                        "conversions": int(metrics.get("conversions", 0))
                    }
            
            return {}
            
        except Exception as e:
            self.logger.error(f"Error obteniendo métricas: {e}")
            return {}






































