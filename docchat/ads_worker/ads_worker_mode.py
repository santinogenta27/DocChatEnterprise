"""
ADS WORKER Mode
Main integration mode for the ADS WORKER system
"""
from typing import Dict, Any, Optional, List
import os
from pathlib import Path

from .agents.ads_agent import AdsWorkerAgent
from .api.routes import router, agent_instance
from .models.schemas import (
    AssetUpload,
    CampaignRequest,
    CampaignResponse,
    OptimizationResult
)


class AdsWorkerMode:
    """
    ADS WORKER Mode - AI-Powered Autonomous Advertising Manager
    
    Sistema completo que:
    - Recibe imágenes/videos/textos de usuarios
    - Analiza assets con visión y audio
    - Genera creativos de anuncios con IA
    - Publica campañas automáticamente en Meta y Google Ads
    - Optimiza en tiempo real basado en métricas
    """
    
    def __init__(self, config: Any, provider: str = "openai"):
        """
        Initialize ADS WORKER Mode
        
        Args:
            config: AppConfig object
            provider: LLM provider (openai, anthropic, etc.)
        """
        self.config = config
        self.provider = provider
        
        # Get API keys from config or environment
        openai_api_key = os.getenv("OPENAI_API_KEY") or getattr(config, "openai_api_key", None)
        
        # Meta credentials
        meta_access_token = os.getenv("META_ACCESS_TOKEN")
        meta_app_id = os.getenv("META_APP_ID")
        meta_app_secret = os.getenv("META_APP_SECRET")
        meta_ad_account_id = os.getenv("META_AD_ACCOUNT_ID")
        
        # Google credentials
        google_customer_id = os.getenv("GOOGLE_ADS_CUSTOMER_ID")
        google_config_path = os.getenv("GOOGLE_ADS_CONFIG_PATH", "google-ads.yaml")
        
        # Storage path
        storage_path = Path(getattr(config, "memory_dir", "./data")) / "ads_worker_assets"
        storage_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize agent
        try:
            self.agent = AdsWorkerAgent(
                openai_api_key=openai_api_key,
                meta_access_token=meta_access_token,
                meta_app_id=meta_app_id,
                meta_app_secret=meta_app_secret,
                meta_ad_account_id=meta_ad_account_id,
                google_customer_id=google_customer_id,
                google_config_path=google_config_path if os.path.exists(google_config_path) else None,
                storage_path=str(storage_path)
            )
            
            # Set global agent instance for API
            global agent_instance
            agent_instance = self.agent
            
            print("✅ ADS WORKER Mode inicializado")
            print(f"   - Meta Ads: {'✅' if self.agent.meta_service else '❌'}")
            print(f"   - Google Ads: {'✅' if self.agent.google_service else '❌'}")
            print(f"   - Asset Processor: ✅")
            print(f"   - Copy Generator: ✅")
            print(f"   - Visual Generator: ✅")
            print(f"   - Optimizer: ✅")
            
        except Exception as e:
            print(f"⚠️ Error inicializando ADS WORKER Mode: {e}")
            self.agent = None
    
    def process_assets(
        self,
        assets: List[AssetUpload]
    ) -> List[Dict[str, Any]]:
        """
        Process user-uploaded assets
        
        Args:
            assets: List of assets to process
            
        Returns:
            List of analysis results
        """
        if not self.agent:
            raise ValueError("ADS WORKER agent not initialized")
        
        analyses = []
        for asset in assets:
            analysis = self.agent.asset_processor.process_asset(
                asset.asset_type,
                asset.file_path,
                asset.file_url,
                asset.text_content,
                asset.metadata
            )
            analyses.append(analysis.model_dump())
        
        return analyses
    
    def launch_campaign(
        self,
        campaign_request: CampaignRequest
    ) -> CampaignResponse:
        """
        Launch a new campaign
        
        Args:
            campaign_request: Campaign creation request
            
        Returns:
            Campaign response with details
        """
        if not self.agent:
            raise ValueError("ADS WORKER agent not initialized")
        
        # Get assets from database using asset_ids
        # For now, create empty list (in production fetch from DB)
        assets = []
        
        campaign = self.agent.process_and_launch_campaign(assets, campaign_request)
        
        return campaign
    
    def optimize_campaign(
        self,
        campaign_id: str,
        platform_campaign_ids: Dict[str, str]
    ) -> OptimizationResult:
        """
        Optimize an existing campaign
        
        Args:
            campaign_id: Internal campaign ID
            platform_campaign_ids: Platform campaign IDs
            
        Returns:
            Optimization result
        """
        if not self.agent:
            raise ValueError("ADS WORKER agent not initialized")
        
        return self.agent.optimize_existing_campaign(campaign_id, platform_campaign_ids)
    
    def get_api_router(self):
        """Get FastAPI router for integration"""
        return router
