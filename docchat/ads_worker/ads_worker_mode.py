"""
ADS WORKER Mode
Main integration mode for the ADS WORKER system
Production-ready with database integration and error handling
"""
from typing import Dict, Any, Optional, List
import os
from pathlib import Path
import logging

from .agents.ads_agent import AdsWorkerAgent
from .api.routes import router, agent_instance
from .database import DatabaseManager
from .models.schemas import (
    AssetUpload,
    CampaignRequest,
    CampaignResponse,
    OptimizationResult,
    AssetAnalysis
)
from .utils.logging import setup_logger
from .utils.queue import SimpleTaskQueue

logger = setup_logger("ads_worker.mode")


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
        
        # Meta credentials - Try credentials manager first, then environment
        from .credentials_manager import AdsCredentialsManager
        creds_manager = AdsCredentialsManager()
        meta_creds = creds_manager.load_meta_credentials()
        
        if meta_creds:
            meta_access_token = meta_creds.get("access_token")
            meta_app_id = meta_creds.get("app_id")
            meta_app_secret = meta_creds.get("app_secret")
            meta_ad_account_id = meta_creds.get("ad_account_id")
        else:
            meta_access_token = os.getenv("META_ACCESS_TOKEN")
            meta_app_id = os.getenv("META_APP_ID")
            meta_app_secret = os.getenv("META_APP_SECRET")
            meta_ad_account_id = os.getenv("META_AD_ACCOUNT_ID")
        
        # Google credentials - Try credentials manager first, then environment
        google_creds = creds_manager.load_google_credentials()
        if google_creds:
            google_customer_id = google_creds.get("customer_id")
        else:
            google_customer_id = os.getenv("GOOGLE_ADS_CUSTOMER_ID")
        google_config_path = os.getenv("GOOGLE_ADS_CONFIG_PATH", "google-ads.yaml")
        
        # Storage path
        storage_path = Path(getattr(config, "memory_dir", "./data")) / "ads_worker_assets"
        storage_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        memory_dir = getattr(config, "memory_dir", "./data")
        db_url = os.getenv("ADS_WORKER_DB_URL")  # Optional: PostgreSQL URL
        self.db = DatabaseManager(db_url=db_url, memory_dir=memory_dir)
        
        # Initialize task queue for async processing
        max_workers = int(os.getenv("ADS_WORKER_MAX_WORKERS", "4"))
        self.task_queue = SimpleTaskQueue(max_workers=max_workers)
        
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
            
            logger.info("✅ ADS WORKER Mode inicializado")
            logger.info(f"   - Meta Ads: {'✅' if self.agent.meta_service else '❌'}")
            logger.info(f"   - Google Ads: {'✅' if self.agent.google_service else '❌'}")
            logger.info(f"   - Asset Processor: ✅")
            logger.info(f"   - Copy Generator: ✅")
            logger.info(f"   - Visual Generator: ✅")
            logger.info(f"   - Optimizer: ✅")
            logger.info(f"   - Database: ✅")
            
        except Exception as e:
            logger.error(f"⚠️ Error inicializando ADS WORKER Mode: {e}")
            self.agent = None
    
    def process_assets(
        self,
        assets: List[AssetUpload],
        user_id: str = "default",
        max_assets: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Process user-uploaded assets
        
        Args:
            assets: List of assets to process
            user_id: User ID for tracking
            max_assets: Maximum number of assets to process (default: 50)
            
        Returns:
            List of analysis results
        """
        if not self.agent:
            raise ValueError("ADS WORKER agent not initialized")
        
        # Validación: límite de assets
        if len(assets) > max_assets:
            raise ValueError(f"Demasiados assets. Máximo permitido: {max_assets}. Recibidos: {len(assets)}")
        
        # Validación: tamaño de archivos (max 100MB por archivo)
        max_file_size = 100 * 1024 * 1024  # 100MB
        for asset in assets:
            if asset.file_path and os.path.exists(asset.file_path):
                file_size = os.path.getsize(asset.file_path)
                if file_size > max_file_size:
                    raise ValueError(f"Archivo demasiado grande: {asset.file_path} ({file_size / (1024*1024):.2f}MB). Máximo: 100MB")
        
        logger.info(f"📦 Procesando {len(assets)} assets para usuario: {user_id}")
        
        analyses = []
        for asset in assets:
            try:
                analysis = self.agent.asset_processor.process_asset(
                    asset.asset_type,
                    asset.file_path,
                    asset.file_url,
                    asset.text_content,
                    asset.metadata
                )
                
                # Save to database
                self.db.save_asset(
                    asset_id=analysis.asset_id,
                    user_id=user_id,
                    asset_type=analysis.asset_type.value,
                    file_path=asset.file_path,
                    file_url=asset.file_url,
                    text_content=asset.text_content,
                    analysis_result=analysis.model_dump(),
                    metadata=asset.metadata
                )
                
                analyses.append(analysis.model_dump())
                logger.info(f"✅ Asset procesado: {analysis.asset_id}")
                
            except Exception as e:
                logger.error(f"Error procesando asset: {e}")
                # Continue with next asset
                continue
        
        logger.info(f"✅ {len(analyses)} assets procesados exitosamente")
        return analyses
    
    def launch_campaign(
        self,
        campaign_request: CampaignRequest,
        user_id: str = "default"
    ) -> CampaignResponse:
        """
        Launch a new campaign
        
        Args:
            campaign_request: Campaign creation request
            user_id: User ID for tracking
            
        Returns:
            Campaign response with details
        """
        if not self.agent:
            raise ValueError("ADS WORKER agent not initialized")
        
        # Validaciones básicas
        if not campaign_request.name or not campaign_request.name.strip():
            raise ValueError("Nombre de campaña es requerido")
        
        if campaign_request.budget_daily <= 0:
            raise ValueError("Presupuesto diario debe ser mayor a 0")
        
        if campaign_request.budget_daily > 100000:
            raise ValueError("Presupuesto diario no puede exceder $100,000")
        
        if not campaign_request.asset_ids:
            raise ValueError("Se requiere al menos un asset_id")
        
        if len(campaign_request.asset_ids) > 100:
            raise ValueError("Demasiados assets. Máximo: 100")
        
        # Sanitizar nombre (básico)
        campaign_request.name = campaign_request.name.strip()[:200]  # Limitar longitud
        
        logger.info(f"🚀 Lanzando campaña: {campaign_request.name} para usuario: {user_id}")
        
        # Get assets from database using asset_ids
        assets = []
        for asset_id in campaign_request.asset_ids:
            asset_data = self.db.get_asset(asset_id)
            if asset_data:
                from .models.schemas import AssetType
                asset = AssetUpload(
                    asset_type=AssetType(asset_data["asset_type"]),
                    file_path=asset_data.get("file_path"),
                    file_url=asset_data.get("file_url"),
                    text_content=asset_data.get("text_content"),
                    metadata=asset_data.get("metadata", {})
                )
                assets.append(asset)
            else:
                logger.warning(f"Asset no encontrado: {asset_id}")
        
        if not assets:
            raise ValueError(f"No se encontraron assets para los IDs proporcionados: {campaign_request.asset_ids}")
        
        # Process and launch campaign
        campaign = self.agent.process_and_launch_campaign(assets, campaign_request)
        
        # Save campaign to database
        self.db.save_campaign(
            campaign_id=campaign.campaign_id,
            user_id=user_id,
            name=campaign.name,
            objective=campaign_request.objective.value,
            budget_daily=campaign_request.budget_daily,
            platforms=campaign_request.platforms.value,
            platform_campaign_ids=campaign.platform_campaign_ids,
            metadata=campaign_request.metadata
        )
        
        logger.info(f"✅ Campaña lanzada: {campaign.campaign_id}")
        
        return campaign
    
    def optimize_campaign(
        self,
        campaign_id: str
    ) -> OptimizationResult:
        """
        Optimize an existing campaign
        
        Args:
            campaign_id: Internal campaign ID
            
        Returns:
            Optimization result
        """
        if not self.agent:
            raise ValueError("ADS WORKER agent not initialized")
        
        logger.info(f"🔧 Optimizando campaña: {campaign_id}")
        
        # Get campaign from database
        campaign_data = self.db.get_campaign(campaign_id)
        if not campaign_data:
            raise ValueError(f"Campaña no encontrada: {campaign_id}")
        
        platform_campaign_ids = campaign_data.get("platform_campaign_ids", {})
        
        # Run optimization
        result = self.agent.optimize_existing_campaign(campaign_id, platform_campaign_ids)
        
        logger.info(f"✅ Optimización completada: {result.optimization_id}")
        logger.info(f"   - Ads pausados: {len(result.ads_paused)}")
        logger.info(f"   - Ads escalados: {len(result.ads_scaled)}")
        
        return result
    
    def get_campaign_metrics(
        self,
        campaign_id: str,
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Get campaign performance metrics
        
        Args:
            campaign_id: Campaign ID
            hours: Number of hours to look back
            
        Returns:
            List of metrics
        """
        return self.db.get_campaign_metrics(campaign_id, hours)
    
    def list_campaigns(
        self,
        user_id: str = "default",
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        List all campaigns for a user
        
        Args:
            user_id: User ID
            limit: Maximum number of campaigns to return
            
        Returns:
            List of campaign dictionaries
        """
        return self.db.list_campaigns(user_id=user_id, limit=limit)
    
    def list_assets(
        self,
        user_id: str = "default",
        asset_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        List all assets for a user
        
        Args:
            user_id: User ID
            asset_type: Optional filter by asset type (image, video, text)
            limit: Maximum number of assets to return
            
        Returns:
            List of asset dictionaries
        """
        return self.db.list_assets(user_id=user_id, asset_type=asset_type, limit=limit)
    
    def get_api_router(self):
        """Get FastAPI router for integration"""
        # Set global mode instance for API
        global mode_instance
        mode_instance = self
        return router



