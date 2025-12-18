"""
Google Ads Service
Integration with Google Ads API
Production-ready with retry logic and error handling
"""
from typing import Dict, Any, List, Optional
import os
from datetime import datetime, timedelta
import uuid
import logging

try:
    from google.ads.googleads.client import GoogleAdsClient
    from google.ads.googleads.errors import GoogleAdsException
    from google.ads.googleads.v16.enums.types import (
        AdvertisingChannelTypeEnum,
        CampaignStatusEnum,
        BudgetDeliveryMethodEnum,
        AdGroupStatusEnum,
        AdGroupAdStatusEnum
    )
    GOOGLE_ADS_AVAILABLE = True
except ImportError:
    GOOGLE_ADS_AVAILABLE = False

from ..utils.logging import setup_logger
from ..utils.retry import retry_with_backoff

logger = setup_logger("ads_worker.google_ads")

from ..models.schemas import CreativeGeneration, CampaignRequest


class GoogleAdsService:
    """Service for managing Google Ads campaigns"""
    
    def __init__(self, customer_id: str, config_path: Optional[str] = None):
        if not GOOGLE_ADS_AVAILABLE:
            raise ImportError("google-ads package is required")
        
        self.customer_id = customer_id
        
        # Initialize client
        try:
            if config_path and os.path.exists(config_path):
                self.client = GoogleAdsClient.load_from_storage(config_path)
                logger.info(f"✅ Google Ads Service inicializado desde: {config_path}")
            else:
                # Try default location
                try:
                    self.client = GoogleAdsClient.load_from_storage()
                    logger.info("✅ Google Ads Service inicializado desde ubicación por defecto")
                except Exception as e:
                    logger.error(f"Error cargando configuración de Google Ads: {e}")
                    raise ValueError("Google Ads configuration file not found. Create google-ads.yaml")
        except Exception as e:
            logger.error(f"Error inicializando Google Ads client: {e}")
            raise
    
    @retry_with_backoff(max_retries=3, exceptions=(GoogleAdsException,))
    def create_campaign(
        self,
        name: str,
        daily_budget: float,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Create a new campaign with budget
        
        Args:
            name: Campaign name
            daily_budget: Daily budget in USD
            start_date: Campaign start date
            end_date: Campaign end date
            
        Returns:
            Campaign data with resource name
        """
        logger.info(f"📢 Creando campaña Google Ads: {name} (${daily_budget}/día)")
        
        try:
            campaign_budget_service = self.client.get_service("CampaignBudgetService")
            campaign_service = self.client.get_service("CampaignService")
            
            # Create budget
            campaign_budget_operation = self.client.get_type("CampaignBudgetOperation")
            campaign_budget = campaign_budget_operation.create
            campaign_budget.name = f"Budget {uuid.uuid4()}"
            campaign_budget.delivery_method = BudgetDeliveryMethodEnum.BudgetDeliveryMethod.STANDARD
            campaign_budget.amount_micros = int(daily_budget * 1_000_000)  # Convert to micros
            
            # Create budget
            budget_response = campaign_budget_service.mutate_campaign_budgets(
                customer_id=self.customer_id,
                operations=[campaign_budget_operation]
            )
            budget_resource_name = budget_response.results[0].resource_name
            
            # Create campaign
            campaign_operation = self.client.get_type("CampaignOperation")
            campaign = campaign_operation.create
            campaign.name = name
            campaign.advertising_channel_type = AdvertisingChannelTypeEnum.AdvertisingChannelType.SEARCH
            campaign.status = CampaignStatusEnum.CampaignStatus.PAUSED
            campaign.manual_cpc = self.client.get_type("ManualCpc")
            campaign.campaign_budget = budget_resource_name
            
            # Network settings
            campaign.network_settings.target_google_search = True
            campaign.network_settings.target_search_network = True
            campaign.network_settings.target_partner_search_network = False
            campaign.network_settings.target_content_network = True
            
            # Dates
            if start_date:
                campaign.start_date = start_date.strftime("%Y%m%d")
            else:
                campaign.start_date = (datetime.now() + timedelta(days=1)).strftime("%Y%m%d")
            
            if end_date:
                campaign.end_date = end_date.strftime("%Y%m%d")
            else:
                campaign.end_date = (datetime.now() + timedelta(weeks=4)).strftime("%Y%m%d")
            
            # Create campaign
            campaign_response = campaign_service.mutate_campaigns(
                customer_id=self.customer_id,
                operations=[campaign_operation]
            )
            
            campaign_resource_name = campaign_response.results[0].resource_name
            campaign_id = campaign_resource_name.split('/')[-1]
            
            logger.info(f"✅ Campaña Google Ads creada: {campaign_id}")
            
            return {
                "campaign_resource_name": campaign_resource_name,
                "campaign_id": campaign_id,
                "name": name,
                "budget_resource_name": budget_resource_name
            }
            
        except GoogleAdsException as e:
            logger.error(f"Error creando campaña Google Ads: {e}")
            raise Exception(f"Error creating Google Ads campaign: {e}")
    
    def create_ad_group(
        self,
        campaign_resource_name: str,
        name: str,
        cpc_bid: float = 1.0
    ) -> Dict[str, Any]:
        """
        Create an ad group
        
        Args:
            campaign_resource_name: Parent campaign resource name
            name: Ad group name
            cpc_bid: CPC bid in USD
            
        Returns:
            Ad group data with resource name
        """
        try:
            ad_group_service = self.client.get_service("AdGroupService")
            
            ad_group_operation = self.client.get_type("AdGroupOperation")
            ad_group = ad_group_operation.create
            ad_group.name = name
            ad_group.campaign = campaign_resource_name
            ad_group.status = AdGroupStatusEnum.AdGroupStatus.ENABLED
            ad_group.type_ = self.client.enums.AdGroupTypeEnum.AdGroupType.SEARCH_STANDARD
            
            # Set CPC bid
            ad_group.cpc_bid_micros = int(cpc_bid * 1_000_000)
            
            # Create ad group
            ad_group_response = ad_group_service.mutate_ad_groups(
                customer_id=self.customer_id,
                operations=[ad_group_operation]
            )
            
            ad_group_resource_name = ad_group_response.results[0].resource_name
            
            return {
                "ad_group_resource_name": ad_group_resource_name,
                "ad_group_id": ad_group_resource_name.split('/')[-1],
                "name": name
            }
            
        except GoogleAdsException as e:
            raise Exception(f"Error creating Google Ads ad group: {e}")
    
    def upload_image(self, image_path: str) -> str:
        """
        Upload image to Google Ads
        
        Args:
            image_path: Local path to image file
            
        Returns:
            Image asset resource name
        """
        try:
            asset_service = self.client.get_service("AssetService")
            
            # Read image
            with open(image_path, "rb") as f:
                image_data = f.read()
            
            # Create image asset
            asset_operation = self.client.get_type("AssetOperation")
            asset = asset_operation.create
            asset.type_ = self.client.enums.AssetTypeEnum.AssetType.IMAGE
            asset.image_asset.data = image_data
            
            # Upload
            asset_response = asset_service.mutate_assets(
                customer_id=self.customer_id,
                operations=[asset_operation]
            )
            
            return asset_response.results[0].resource_name
            
        except GoogleAdsException as e:
            raise Exception(f"Error uploading image to Google Ads: {e}")
    
    def create_responsive_search_ad(
        self,
        ad_group_resource_name: str,
        creative: CreativeGeneration,
        final_url: str
    ) -> Dict[str, Any]:
        """
        Create a responsive search ad
        
        Args:
            ad_group_resource_name: Ad group resource name
            creative: CreativeGeneration object
            final_url: Landing page URL
            
        Returns:
            Ad data with resource name
        """
        try:
            ad_group_ad_service = self.client.get_service("AdGroupAdService")
            
            ad_group_ad_operation = self.client.get_type("AdGroupAdOperation")
            ad_group_ad = ad_group_ad_operation.create
            ad_group_ad.ad_group = ad_group_resource_name
            ad_group_ad.status = AdGroupAdStatusEnum.AdGroupAdStatus.PAUSED
            
            # Create responsive search ad
            ad = ad_group_ad.ad
            ad.type_ = self.client.enums.AdTypeEnum.AdType.RESPONSIVE_SEARCH_AD
            
            responsive_search_ad = ad.responsive_search_ad
            
            # Headlines (up to 15)
            headlines = [
                creative.headline or "Discover Amazing Products",
                creative.description[:30] if creative.description else "Shop Now",
                "Best Deals Available"
            ]
            for headline_text in headlines[:15]:
                headline = self.client.get_type("AdTextAsset")
                headline.text = headline_text
                responsive_search_ad.headlines.append(headline)
            
            # Descriptions (up to 4)
            descriptions = [
                creative.description or "Experience quality and innovation",
                "Join thousands of satisfied customers"
            ]
            for desc_text in descriptions[:4]:
                description = self.client.get_type("AdTextAsset")
                description.text = desc_text
                responsive_search_ad.descriptions.append(description)
            
            # Final URLs
            ad.final_urls.append(final_url)
            
            # Create ad
            ad_group_ad_response = ad_group_ad_service.mutate_ad_group_ads(
                customer_id=self.customer_id,
                operations=[ad_group_ad_operation]
            )
            
            ad_group_ad_resource_name = ad_group_ad_response.results[0].resource_name
            
            return {
                "ad_resource_name": ad_group_ad_resource_name,
                "ad_id": ad_group_ad_resource_name.split('/')[-1]
            }
            
        except GoogleAdsException as e:
            raise Exception(f"Error creating Google Ads ad: {e}")
    
    def get_campaign_metrics(
        self,
        campaign_resource_name: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get campaign performance metrics
        
        Args:
            campaign_resource_name: Campaign resource name
            start_date: Start date for metrics
            end_date: End date for metrics
            
        Returns:
            Metrics dictionary
        """
        try:
            ga_service = self.client.get_service("GoogleAdsService")
            
            query = f"""
                SELECT
                    campaign.id,
                    campaign.name,
                    metrics.impressions,
                    metrics.clicks,
                    metrics.cost_micros,
                    metrics.ctr,
                    metrics.average_cpc,
                    metrics.conversions,
                    metrics.cost_per_conversion
                FROM campaign
                WHERE campaign.resource_name = '{campaign_resource_name}'
            """
            
            if start_date and end_date:
                query += f" AND segments.date BETWEEN '{start_date.strftime('%Y-%m-%d')}' AND '{end_date.strftime('%Y-%m-%d')}'"
            
            response = ga_service.search(customer_id=self.customer_id, query=query)
            
            metrics = {}
            for row in response:
                metrics = {
                    "impressions": row.metrics.impressions,
                    "clicks": row.metrics.clicks,
                    "spend": row.metrics.cost_micros / 1_000_000,  # Convert from micros
                    "ctr": row.metrics.ctr,
                    "cpc": row.metrics.average_cpc / 1_000_000,  # Convert from micros
                    "conversions": row.metrics.conversions,
                    "cpa": row.metrics.cost_per_conversion / 1_000_000 if row.metrics.cost_per_conversion else 0
                }
                break
            
            return metrics
            
        except GoogleAdsException as e:
            print(f"⚠️ Error getting Google Ads metrics: {e}")
            return {}
    
    def pause_ad(self, ad_resource_name: str) -> bool:
        """Pause an ad"""
        try:
            ad_group_ad_service = self.client.get_service("AdGroupAdService")
            
            ad_group_ad_operation = self.client.get_type("AdGroupAdOperation")
            ad_group_ad = ad_group_ad_operation.update
            ad_group_ad.resource_name = ad_resource_name
            ad_group_ad.status = AdGroupAdStatusEnum.AdGroupAdStatus.PAUSED
            
            ad_group_ad_service.mutate_ad_group_ads(
                customer_id=self.customer_id,
                operations=[ad_group_ad_operation]
            )
            
            return True
        except GoogleAdsException as e:
            print(f"⚠️ Error pausing Google Ads ad: {e}")
            return False
    
    def activate_ad(self, ad_resource_name: str) -> bool:
        """Activate an ad"""
        try:
            ad_group_ad_service = self.client.get_service("AdGroupAdService")
            
            ad_group_ad_operation = self.client.get_type("AdGroupAdOperation")
            ad_group_ad = ad_group_ad_operation.update
            ad_group_ad.resource_name = ad_resource_name
            ad_group_ad.status = AdGroupAdStatusEnum.AdGroupAdStatus.ENABLED
            
            ad_group_ad_service.mutate_ad_group_ads(
                customer_id=self.customer_id,
                operations=[ad_group_ad_operation]
            )
            
            return True
        except GoogleAdsException as e:
            print(f"⚠️ Error activating Google Ads ad: {e}")
            return False

