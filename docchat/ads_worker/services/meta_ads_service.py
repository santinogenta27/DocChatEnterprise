"""
Meta Ads Service
Integration with Meta Marketing API (Facebook/Instagram)
Production-ready with retry logic and error handling
"""
from typing import Dict, Any, List, Optional
import os
import logging
from datetime import datetime

try:
    from facebook_business.api import FacebookAdsApi
    from facebook_business.adobjects.adaccount import AdAccount
    from facebook_business.adobjects.campaign import Campaign
    from facebook_business.adobjects.adset import AdSet
    from facebook_business.adobjects.adcreative import AdCreative
    from facebook_business.adobjects.ad import Ad
    from facebook_business.adobjects.adimage import AdImage
    from facebook_business.adobjects.advideo import AdVideo
    from facebook_business.exceptions import FacebookRequestError
    META_AVAILABLE = True
except ImportError:
    META_AVAILABLE = False
    # Definir clase dummy para evitar NameError en decoradores
    class FacebookRequestError(Exception):
        """Dummy exception class when facebook_business is not installed"""
        pass

from ..utils.logging import setup_logger
from ..utils.retry import retry_with_backoff

logger = setup_logger("ads_worker.meta_ads")

from ..models.schemas import CreativeGeneration, CampaignRequest


class MetaAdsService:
    """Service for managing Meta (Facebook/Instagram) ads"""
    
    def __init__(
        self,
        access_token: str,
        app_id: str,
        app_secret: str,
        ad_account_id: str
    ):
        if not META_AVAILABLE:
            raise ImportError("facebook-business package is required")
        
        self.access_token = access_token
        self.app_id = app_id
        self.app_secret = app_secret
        self.ad_account_id = ad_account_id
        
        # Initialize API
        try:
            FacebookAdsApi.init(access_token=access_token, app_id=app_id, app_secret=app_secret)
            self.account = AdAccount(f'act_{ad_account_id}')
            logger.info(f"✅ Meta Ads Service inicializado para cuenta: {ad_account_id}")
        except Exception as e:
            logger.error(f"Error inicializando Meta Ads API: {e}")
            raise
    
    @retry_with_backoff(max_retries=3, exceptions=(FacebookRequestError,))
    def create_campaign(
        self,
        name: str,
        objective: str,
        status: str = "PAUSED"
    ) -> Dict[str, Any]:
        """
        Create a new campaign
        
        Args:
            name: Campaign name
            objective: Campaign objective (CONVERSIONS, TRAFFIC, etc.)
            status: Campaign status (PAUSED, ACTIVE)
            
        Returns:
            Campaign data with ID
        """
        logger.info(f"📢 Creando campaña Meta: {name} ({objective})")
        
        try:
            campaign = self.account.create_campaign(
                params={
                    'name': name,
                    'objective': objective,
                    'status': status,
                    'special_ad_categories': []
                }
            )
            
            campaign_id = campaign.get_id()
            logger.info(f"✅ Campaña Meta creada: {campaign_id}")
            
            return {
                "campaign_id": campaign_id,
                "name": name,
                "objective": objective,
                "status": status
            }
        except FacebookRequestError as e:
            logger.error(f"Error creando campaña Meta: {e}")
            raise Exception(f"Error creating Meta campaign: {e}")
    
    def create_ad_set(
        self,
        campaign_id: str,
        name: str,
        daily_budget: float,
        targeting: Optional[Dict[str, Any]] = None,
        optimization_goal: str = "OFFSITE_CONVERSIONS"
    ) -> Dict[str, Any]:
        """
        Create an ad set
        
        Args:
            campaign_id: Parent campaign ID
            name: Ad set name
            daily_budget: Daily budget in cents
            targeting: Targeting parameters
            optimization_goal: Optimization goal
            
        Returns:
            Ad set data with ID
        """
        if targeting is None:
            targeting = {
                "age_min": 18,
                "age_max": 65,
                "genders": [1, 2],  # All genders
                "geo_locations": {"countries": ["US"]}  # Default to US
            }
        
        try:
            ad_set = self.account.create_ad_set(
                params={
                    'name': name,
                    'campaign_id': campaign_id,
                    'daily_budget': int(daily_budget * 100),  # Convert to cents
                    'billing_event': 'IMPRESSIONS',
                    'optimization_goal': optimization_goal,
                    'bid_amount': 100,  # $1.00 default bid
                    'targeting': targeting,
                    'status': 'PAUSED'
                }
            )
            
            return {
                "ad_set_id": ad_set.get_id(),
                "name": name,
                "daily_budget": daily_budget,
                "campaign_id": campaign_id
            }
        except FacebookRequestError as e:
            raise Exception(f"Error creating Meta ad set: {e}")
    
    @retry_with_backoff(max_retries=3, exceptions=(FacebookRequestError,))
    def upload_image(self, image_path: str) -> str:
        """
        Upload image to Meta
        
        Args:
            image_path: Local path to image file
            
        Returns:
            Image hash (used to reference in creatives)
        """
        logger.info(f"📤 Subiendo imagen a Meta: {image_path}")
        
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image file not found: {image_path}")
        
        try:
            image = AdImage(parent_id=self.ad_account_id)
            image[AdImage.Field.filename] = image_path
            image.remote_create()
            
            image_hash = image[AdImage.Field.hash]
            logger.info(f"✅ Imagen subida a Meta, hash: {image_hash}")
            
            return image_hash
        except FacebookRequestError as e:
            logger.error(f"Error subiendo imagen a Meta: {e}")
            raise Exception(f"Error uploading image to Meta: {e}")
    
    def upload_video(self, video_path: str) -> str:
        """
        Upload video to Meta
        
        Args:
            video_path: Local path to video file
            
        Returns:
            Video ID
        """
        try:
            video = AdVideo(parent_id=self.ad_account_id)
            video[AdVideo.Field.filepath] = video_path
            video.remote_create()
            
            return video.get_id()
        except FacebookRequestError as e:
            raise Exception(f"Error uploading video to Meta: {e}")
    
    def create_ad_creative(
        self,
        name: str,
        creative: CreativeGeneration,
        image_hash: Optional[str] = None,
        video_id: Optional[str] = None,
        page_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create ad creative
        
        Args:
            name: Creative name
            creative: CreativeGeneration object
            image_hash: Image hash from upload_image
            video_id: Video ID from upload_video
            page_id: Facebook Page ID (required)
            
        Returns:
            Creative data with ID
        """
        if not page_id:
            raise ValueError("page_id is required for Meta creatives")
        
        creative_params = {
            'name': name,
            'object_story_spec': {
                'page_id': page_id
            }
        }
        
        # Add image or video
        if image_hash:
            creative_params['object_story_spec']['link_data'] = {
                'image_hash': image_hash,
                'link': creative.generation_params.get('link_url', ''),
                'message': creative.description or '',
                'name': creative.headline or '',
                'call_to_action': {
                    'type': creative.cta or 'LEARN_MORE'
                }
            }
        elif video_id:
            creative_params['object_story_spec']['video_id'] = video_id
            creative_params['object_story_spec']['link_data'] = {
                'link': creative.generation_params.get('link_url', ''),
                'message': creative.description or '',
                'name': creative.headline or '',
                'call_to_action': {
                    'type': creative.cta or 'LEARN_MORE'
                }
            }
        else:
            raise ValueError("Either image_hash or video_id must be provided")
        
        try:
            ad_creative = AdCreative(parent_id=self.ad_account_id)
            for key, value in creative_params.items():
                ad_creative[key] = value
            ad_creative.remote_create()
            
            return {
                "creative_id": ad_creative.get_id(),
                "name": name
            }
        except FacebookRequestError as e:
            raise Exception(f"Error creating Meta creative: {e}")
    
    def create_ad(
        self,
        ad_set_id: str,
        creative_id: str,
        name: str,
        status: str = "PAUSED"
    ) -> Dict[str, Any]:
        """
        Create an ad
        
        Args:
            ad_set_id: Ad set ID
            creative_id: Creative ID
            name: Ad name
            status: Ad status
            
        Returns:
            Ad data with ID
        """
        try:
            ad = Ad(parent_id=self.ad_account_id)
            ad[Ad.Field.name] = name
            ad[Ad.Field.adset_id] = ad_set_id
            ad[Ad.Field.creative] = {'creative_id': creative_id}
            ad[Ad.Field.status] = status
            ad.remote_create()
            
            return {
                "ad_id": ad.get_id(),
                "name": name,
                "ad_set_id": ad_set_id,
                "status": status
            }
        except FacebookRequestError as e:
            raise Exception(f"Error creating Meta ad: {e}")
    
    def get_campaign_metrics(
        self,
        campaign_id: str,
        date_preset: str = "last_7d"
    ) -> Dict[str, Any]:
        """
        Get campaign performance metrics
        
        Args:
            campaign_id: Campaign ID
            date_preset: Date range preset
            
        Returns:
            Metrics dictionary
        """
        try:
            campaign = Campaign(campaign_id)
            insights = campaign.get_insights(
                params={
                    'date_preset': date_preset,
                    'fields': [
                        'impressions',
                        'clicks',
                        'spend',
                        'ctr',
                        'cpc',
                        'cpm',
                        'actions'
                    ]
                }
            )
            
            if insights:
                insight = insights[0]
                return {
                    "impressions": int(insight.get('impressions', 0)),
                    "clicks": int(insight.get('clicks', 0)),
                    "spend": float(insight.get('spend', 0)),
                    "ctr": float(insight.get('ctr', 0)),
                    "cpc": float(insight.get('cpc', 0)),
                    "cpm": float(insight.get('cpm', 0)),
                    "conversions": self._extract_conversions(insight.get('actions', []))
                }
            
            return {}
        except FacebookRequestError as e:
            print(f"⚠️ Error getting Meta metrics: {e}")
            return {}
    
    def _extract_conversions(self, actions: List[Dict]) -> int:
        """Extract conversion count from actions"""
        conversions = 0
        for action in actions:
            if action.get('action_type') in ['offsite_conversion', 'purchase', 'lead']:
                conversions += int(action.get('value', 0))
        return conversions
    
    def pause_ad(self, ad_id: str) -> bool:
        """Pause an ad"""
        try:
            ad = Ad(ad_id)
            ad.update({'status': 'PAUSED'})
            return True
        except FacebookRequestError as e:
            print(f"⚠️ Error pausing Meta ad: {e}")
            return False
    
    def activate_ad(self, ad_id: str) -> bool:
        """Activate an ad"""
        try:
            ad = Ad(ad_id)
            ad.update({'status': 'ACTIVE'})
            return True
        except FacebookRequestError as e:
            print(f"⚠️ Error activating Meta ad: {e}")
            return False
    
    @retry_with_backoff(max_retries=3, exceptions=(FacebookRequestError,))
    def estimate_audience_size(
        self,
        targeting: Dict[str, Any],
        optimization_goal: str = "OFFSITE_CONVERSIONS",
        daily_budget: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Estimate audience size using Meta Ads API delivery_estimate
        
        Args:
            targeting: Targeting parameters (age_min, age_max, genders, geo_locations, interests)
            optimization_goal: Optimization goal (OFFSITE_CONVERSIONS, LINK_CLICKS, etc.)
            daily_budget: Optional daily budget in USD for more accurate estimates
            
        Returns:
            Dictionary with audience_size, daily_reach, and recommendations
        """
        logger.info(f"📊 Estimando tamaño de audiencia con targeting: {targeting}")
        
        try:
            # Prepare targeting spec
            targeting_spec = {
                "age_min": targeting.get("age_min", 18),
                "age_max": targeting.get("age_max", 65),
                "genders": targeting.get("genders", [1, 2]),
                "geo_locations": targeting.get("geo_locations", {"countries": ["US"]})
            }
            
            # Add interests if provided
            if "interests" in targeting and targeting["interests"]:
                interests_list = targeting["interests"]
                if isinstance(interests_list, list) and len(interests_list) > 0:
                    # Use flexible_spec for interests
                    targeting_spec["flexible_spec"] = [
                        {"interests": [{"name": interest} for interest in interests_list[:5]]}
                    ]
            
            # Prepare delivery estimate params
            estimate_params = {
                "optimization_goal": optimization_goal,
                "targeting_spec": targeting_spec
            }
            
            # Add budget if provided (in cents)
            if daily_budget:
                estimate_params["daily_budget"] = int(daily_budget * 100)
            
            # Get delivery estimate
            delivery_estimate = self.account.get_delivery_estimate(params=estimate_params)
            
            # Parse response
            estimate_data = delivery_estimate.get('data', [{}])[0] if delivery_estimate.get('data') else {}
            
            # Extract audience size
            estimate_dau = estimate_data.get('estimate_dau', {})
            audience_size_min = estimate_dau.get('lower_bound', 0)
            audience_size_max = estimate_dau.get('upper_bound', 0)
            audience_size_avg = (audience_size_min + audience_size_max) // 2 if (audience_size_min + audience_size_max) > 0 else 0
            
            # Extract daily reach estimate
            estimate_ready = estimate_data.get('estimate_ready', {})
            daily_reach_min = estimate_ready.get('lower_bound', 0)
            daily_reach_max = estimate_ready.get('upper_bound', 0)
            daily_reach_avg = (daily_reach_min + daily_reach_max) // 2 if (daily_reach_min + daily_reach_max) > 0 else 0
            
            # Generate recommendations
            recommendations = []
            
            if audience_size_avg < 1000:
                recommendations.append("⚠️ Audiencia muy pequeña (<1K). Considera expandir países o intereses.")
            elif audience_size_avg < 10000:
                recommendations.append("💡 Audiencia pequeña (1K-10K). Podrías considerar expandir targeting.")
            elif audience_size_avg > 50000000:
                recommendations.append("💡 Audiencia muy grande (>50M). Considera refinar targeting para mejor ROI.")
            
            if daily_budget and daily_reach_avg > 0:
                cpm_estimate = (daily_budget * 1000) / daily_reach_avg if daily_reach_avg > 0 else 0
                if cpm_estimate > 10:
                    recommendations.append(f"💰 CPM estimado: ${cpm_estimate:.2f}. Considera aumentar presupuesto para mejor alcance.")
            
            result = {
                "audience_size": audience_size_avg,
                "audience_size_min": audience_size_min,
                "audience_size_max": audience_size_max,
                "daily_reach": daily_reach_avg,
                "daily_reach_min": daily_reach_min,
                "daily_reach_max": daily_reach_max,
                "recommendations": recommendations,
                "status": "success"
            }
            
            logger.info(f"✅ Estimación de audiencia: ~{audience_size_avg:,} personas")
            return result
            
        except FacebookRequestError as e:
            logger.error(f"Error estimando audiencia: {e}")
            return {
                "audience_size": 0,
                "audience_size_min": 0,
                "audience_size_max": 0,
                "daily_reach": 0,
                "daily_reach_min": 0,
                "daily_reach_max": 0,
                "recommendations": [f"⚠️ No se pudo obtener estimación de Meta API: {str(e)}"],
                "status": "error",
                "error": str(e)
            }
        except Exception as e:
            logger.error(f"Error inesperado estimando audiencia: {e}")
            return {
                "audience_size": 0,
                "audience_size_min": 0,
                "audience_size_max": 0,
                "daily_reach": 0,
                "daily_reach_min": 0,
                "daily_reach_max": 0,
                "recommendations": [f"⚠️ Error: {str(e)}"],
                "status": "error",
                "error": str(e)
            }


