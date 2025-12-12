"""
Integración completa con Google Ads API
Implementación production-ready con OAuth2 y manejo de tokens
"""

from __future__ import annotations

import os
from typing import Dict, Any, Optional, List
from datetime import datetime

try:
    from google.ads.googleads.client import GoogleAdsClient
    from google.ads.googleads.errors import GoogleAdsException
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    GOOGLE_ADS_AVAILABLE = True
except ImportError:
    GOOGLE_ADS_AVAILABLE = False
    print("⚠️ Google Ads library no disponible. Instala con: pip install google-ads")


class GoogleAdsIntegration:
    """Integración completa con Google Ads API"""
    
    SCOPES = ['https://www.googleapis.com/auth/adwords']
    
    def __init__(self, config: Any):
        self.config = config
        self.client: Optional[GoogleAdsClient] = None
        self.customer_id = os.getenv("GOOGLE_ADS_CUSTOMER_ID", "")
        self.developer_token = os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN", "")
        self.client_id = os.getenv("GOOGLE_ADS_CLIENT_ID", "")
        self.client_secret = os.getenv("GOOGLE_ADS_CLIENT_SECRET", "")
        self.refresh_token = os.getenv("GOOGLE_ADS_REFRESH_TOKEN", "")
        
        if GOOGLE_ADS_AVAILABLE and all([
            self.customer_id,
            self.developer_token,
            self.client_id,
            self.client_secret
        ]):
            self._initialize_client()
    
    def _initialize_client(self):
        """Inicializa cliente de Google Ads"""
        if not GOOGLE_ADS_AVAILABLE:
            return
        
        try:
            # Configurar credenciales
            credentials = None
            if self.refresh_token:
                credentials = Credentials(
                    token=None,
                    refresh_token=self.refresh_token,
                    token_uri="https://oauth2.googleapis.com/token",
                    client_id=self.client_id,
                    client_secret=self.client_secret
                )
                credentials.refresh(Request())
            
            # Crear cliente
            yaml_config = {
                "developer_token": self.developer_token,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": self.refresh_token if self.refresh_token else "",
                "use_proto_plus": True
            }
            
            self.client = GoogleAdsClient.load_from_dict(yaml_config)
            
        except Exception as e:
            print(f"Error inicializando Google Ads client: {e}")
            self.client = None
    
    def create_campaign(
        self,
        name: str,
        budget: float,
        objective: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Crea una campaña en Google Ads"""
        if not self.client:
            return {
                "success": False,
                "error": "Google Ads client no inicializado",
                "note": "Configura GOOGLE_ADS_* variables de entorno"
            }
        
        if not GOOGLE_ADS_AVAILABLE:
            return {
                "success": False,
                "error": "Google Ads library no disponible",
                "note": "Instala con: pip install google-ads"
            }
        
        try:
            from google.ads.googleads.v16.resources.types.campaign import Campaign
            from google.ads.googleads.v16.enums.types.campaign_status import CampaignStatusEnum
            from google.ads.googleads.v16.enums.types.advertising_channel_type import AdvertisingChannelTypeEnum
            from google.ads.googleads.v16.enums.types.budget_delivery_method import BudgetDeliveryMethodEnum
            from google.ads.googleads.v16.services.types.campaign_service import MutateCampaignsRequest
            from google.ads.googleads.v16.services.types.campaign_budget_service import MutateCampaignBudgetsRequest
            
            # Crear budget primero
            budget_service = self.client.get_service("CampaignBudgetService")
            budget_operation = self.client.get_type("CampaignBudgetOperation")
            budget = budget_operation.create
            budget.name = f"{name} Budget"
            budget.delivery_method = BudgetDeliveryMethodEnum.BudgetDeliveryMethod.STANDARD
            budget.amount_micros = int(budget * 1_000_000)  # Convertir a micros
            
            budget_response = budget_service.mutate_campaign_budgets(
                customer_id=self.customer_id,
                operations=[budget_operation]
            )
            budget_resource_name = budget_response.results[0].resource_name
            
            # Crear campaña
            campaign_service = self.client.get_service("CampaignService")
            campaign_operation = self.client.get_type("CampaignOperation")
            campaign = campaign_operation.create
            campaign.name = name
            campaign.advertising_channel_type = AdvertisingChannelTypeEnum.AdvertisingChannelType.SEARCH
            campaign.status = CampaignStatusEnum.CampaignStatus.PAUSED  # Crear pausada
            campaign.campaign_budget = budget_resource_name
            campaign.start_date = start_date or datetime.now().strftime("%Y-%m-%d")
            if end_date:
                campaign.end_date = end_date
            
            campaign_response = campaign_service.mutate_campaigns(
                customer_id=self.customer_id,
                operations=[campaign_operation]
            )
            
            campaign_resource_name = campaign_response.results[0].resource_name
            campaign_id = campaign_resource_name.split("/")[-1]
            
            return {
                "success": True,
                "platform_id": campaign_id,
                "resource_name": campaign_resource_name,
                "message": "Campaign created on Google Ads (paused for review)"
            }
        
        except GoogleAdsException as e:
            error_messages = []
            for error in e.failure.errors:
                error_messages.append(f"{error.message}: {error.location}")
            
            return {
                "success": False,
                "error": "Google Ads API error",
                "details": error_messages
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_campaign_performance(
        self,
        campaign_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Obtiene métricas de performance de una campaña"""
        if not self.client:
            return {"error": "Client no inicializado"}
        
        try:
            ga_service = self.client.get_service("GoogleAdsService")
            
            query = f"""
                SELECT
                    campaign.id,
                    campaign.name,
                    metrics.impressions,
                    metrics.clicks,
                    metrics.conversions,
                    metrics.cost_micros,
                    metrics.ctr,
                    metrics.average_cpc,
                    metrics.conversion_rate
                FROM campaign
                WHERE campaign.id = {campaign_id}
            """
            
            if start_date:
                query += f" AND segments.date >= '{start_date}'"
            if end_date:
                query += f" AND segments.date <= '{end_date}'"
            
            response = ga_service.search(customer_id=self.customer_id, query=query)
            
            results = []
            for row in response:
                results.append({
                    "campaign_id": row.campaign.id,
                    "campaign_name": row.campaign.name,
                    "impressions": row.metrics.impressions,
                    "clicks": row.metrics.clicks,
                    "conversions": row.metrics.conversions,
                    "spend": row.metrics.cost_micros / 1_000_000,  # Convertir de micros
                    "ctr": row.metrics.ctr,
                    "cpc": row.metrics.average_cpc / 1_000_000,
                    "conversion_rate": row.metrics.conversion_rate
                })
            
            return {
                "success": True,
                "results": results
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def pause_campaign(self, campaign_id: str) -> Dict[str, Any]:
        """Pausa una campaña"""
        if not self.client:
            return {"error": "Client no inicializado"}
        
        try:
            from google.ads.googleads.v16.enums.types.campaign_status import CampaignStatusEnum
            
            campaign_service = self.client.get_service("CampaignService")
            campaign_operation = self.client.get_type("CampaignOperation")
            campaign = campaign_operation.update
            campaign.resource_name = f"customers/{self.customer_id}/campaigns/{campaign_id}"
            campaign.status = CampaignStatusEnum.CampaignStatus.PAUSED
            
            campaign_operation.update_mask.CopyFrom(
                self.client.get_type("FieldMask")(paths=["status"])
            )
            
            response = campaign_service.mutate_campaigns(
                customer_id=self.customer_id,
                operations=[campaign_operation]
            )
            
            return {
                "success": True,
                "message": f"Campaign {campaign_id} paused"
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

