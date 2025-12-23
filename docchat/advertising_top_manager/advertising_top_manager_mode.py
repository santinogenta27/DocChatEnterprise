"""
ADVERTISING TOP MANAGER Mode
Main integration mode for the ADVERTISING TOP MANAGER system
Production-ready with database integration and error handling
"""
from typing import Dict, Any, Optional, List, Tuple
import os
from pathlib import Path
import logging
import numpy as np
from datetime import datetime

from .agents.ads_agent import AdsWorkerAgent as AdvertisingTopManagerAgent
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

# Advanced modules integration
try:
    from .advanced_modules.layout_generation import ContentAwareLayoutGenerator
    from .advanced_modules.influence_maximization import MultiProductInfluenceOptimizer
    from .advanced_modules.mindfuse import MindFuseStrategyCoCreator
    from .advanced_modules.ctr_generation import CTRDrivenImageGenerator
    from .advanced_modules.multi_attribution import MultiAttributionLearner
    from .advanced_modules.decision_support import MarketForecastingDSS
    ADVANCED_MODULES_AVAILABLE = True
except ImportError as e:
    ADVANCED_MODULES_AVAILABLE = False
    ContentAwareLayoutGenerator = None
    MultiProductInfluenceOptimizer = None
    MindFuseStrategyCoCreator = None
    CTRDrivenImageGenerator = None
    MultiAttributionLearner = None
    MarketForecastingDSS = None
    logger.warning(f"⚠️ Advanced modules not available: {e}")

logger = setup_logger("advertising_top_manager.mode")


class AdvertisingTopManagerMode:
    """
    ADVERTISING TOP MANAGER Mode - AI-Powered Autonomous Advertising Manager
    
    Sistema completo que:
    - Recibe imágenes/videos/textos de usuarios
    - Analiza assets con visión y audio
    - Genera creativos de anuncios con IA
    - Publica campañas automáticamente en Meta y Google Ads
    - Optimiza en tiempo real basado en métricas
    """
    
    def __init__(self, config: Any, provider: str = "openai"):
        """
        Initialize ADVERTISING TOP MANAGER Mode
        
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
        storage_path = Path(getattr(config, "memory_dir", "./data")) / "advertising_top_manager_assets"
        storage_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        memory_dir = getattr(config, "memory_dir", "./data")
        db_url = os.getenv("ADVERTISING_TOP_MANAGER_DB_URL")  # Optional: PostgreSQL URL
        self.db = DatabaseManager(db_url=db_url, memory_dir=memory_dir)
        
        # Initialize task queue for async processing
        max_workers = int(os.getenv("ADVERTISING_TOP_MANAGER_MAX_WORKERS", "4"))
        self.task_queue = SimpleTaskQueue(max_workers=max_workers)
        
        # Initialize agent
        try:
            self.agent = AdvertisingTopManagerAgent(
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
            
            logger.info("✅ ADVERTISING TOP MANAGER Mode inicializado")
            logger.info(f"   - Meta Ads: {'✅' if self.agent.meta_service else '❌'}")
            logger.info(f"   - Google Ads: {'✅' if self.agent.google_service else '❌'}")
            logger.info(f"   - Asset Processor: ✅")
            logger.info(f"   - Copy Generator: ✅")
            logger.info(f"   - Visual Generator: ✅")
            logger.info(f"   - Optimizer: ✅")
            logger.info(f"   - Database: ✅")
            
        except Exception as e:
            logger.error(f"⚠️ Error inicializando ADVERTISING TOP MANAGER Mode: {e}")
            self.agent = None
        
        # Initialize Advanced Modules
        try:
            if ADVANCED_MODULES_AVAILABLE:
                # Content-Aware Layout Generation
                self.layout_generator = ContentAwareLayoutGenerator(config=config) if ContentAwareLayoutGenerator else None
                
                # Multi-Product Influence Maximization
                self.influence_optimizer = MultiProductInfluenceOptimizer(config=config) if MultiProductInfluenceOptimizer else None
                
                # MindFuse Strategy Co-Creation
                self.mindfuse = MindFuseStrategyCoCreator(config=config) if MindFuseStrategyCoCreator else None
                
                # CTR-Driven Image Generation
                self.ctr_generator = CTRDrivenImageGenerator(config=config) if CTRDrivenImageGenerator else None
                
                # Multi-Attribution Learning
                self.multi_attribution = MultiAttributionLearner(config=config) if MultiAttributionLearner else None
                
                # Market Forecasting DSS
                self.market_forecaster = MarketForecastingDSS(config=config) if MarketForecastingDSS else None
                
                logger.info("✅ Advanced Modules inicializados:")
                logger.info(f"   - Content-Aware Layout Generator: {'✅' if self.layout_generator else '❌'}")
                logger.info(f"   - Multi-Product Influence Optimizer: {'✅' if self.influence_optimizer else '❌'}")
                logger.info(f"   - MindFuse Strategy Co-Creator: {'✅' if self.mindfuse else '❌'}")
                logger.info(f"   - CTR-Driven Image Generator: {'✅' if self.ctr_generator else '❌'}")
                logger.info(f"   - Multi-Attribution Learner: {'✅' if self.multi_attribution else '❌'}")
                logger.info(f"   - Market Forecasting DSS: {'✅' if self.market_forecaster else '❌'}")
            else:
                self.layout_generator = None
                self.influence_optimizer = None
                self.mindfuse = None
                self.ctr_generator = None
                self.multi_attribution = None
                self.market_forecaster = None
        except Exception as e:
            logger.error(f"⚠️ Error inicializando Advanced Modules: {e}")
            self.layout_generator = None
            self.influence_optimizer = None
            self.mindfuse = None
            self.ctr_generator = None
            self.multi_attribution = None
            self.market_forecaster = None
    
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
            raise ValueError("ADVERTISING TOP MANAGER agent not initialized")
        
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
            raise ValueError("ADVERTISING TOP MANAGER agent not initialized")
        
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
        
        # Guardar métricas iniciales (0) para la campaña - CRÍTICO para dashboard
        try:
            # Guardar métrica inicial agregada para la campaña completa
            # Esto permite que el dashboard muestre datos aunque no haya métricas por ad individual
            initial_ad_id = f"campaign_{campaign.campaign_id}_initial"
            self.db.save_metrics(
                ad_id=initial_ad_id,
                campaign_id=campaign.campaign_id,
                platform=campaign_request.platforms.value if isinstance(campaign_request.platforms.value, str) else "meta",
                metrics={
                    "impressions": 0,
                    "clicks": 0,
                    "conversions": 0,
                    "spend": 0.0,
                    "ctr": 0.0,
                    "cpc": 0.0,
                    "cpa": 0.0,
                    "roas": 0.0,
                    "metadata": {
                        "initial": True,
                        "created_at": datetime.utcnow().isoformat(),
                        "note": "Métricas iniciales de campaña - Se actualizarán con datos reales cuando estén disponibles"
                    }
                }
            )
            logger.info(f"✅ Métricas iniciales guardadas para campaña {campaign.campaign_id}")
        except Exception as e:
            logger.warning(f"⚠️ No se pudieron guardar métricas iniciales: {e}")
            # No fallar la creación de campaña por esto
        
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
            raise ValueError("ADVERTISING TOP MANAGER agent not initialized")
        
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
    
    # ========== Advanced Module Methods ==========
    
    def generate_content_aware_layout(
        self,
        background_image_path: str,
        element_types: List[str],
        canvas_size: Tuple[int, int] = (1024, 1500)
    ) -> Dict[str, Any]:
        """
        Generate content-aware ad banner layout using VLM with Chain-of-Thought
        
        Args:
            background_image_path: Path to background image
            element_types: List of element types (e.g., ["text", "logo", "underlay"])
            canvas_size: Canvas dimensions (width, height)
        
        Returns:
            Dictionary with placement_plan and html_layout
        """
        if not self.layout_generator:
            raise ValueError("Content-Aware Layout Generator not available")
        
        return self.layout_generator.generate_layout(
            background_image_path=background_image_path,
            element_types=element_types,
            canvas_size=canvas_size
        )
    
    def optimize_multi_product_influence(
        self,
        products: List[Dict[str, Any]],
        slots: List[Dict[str, Any]],
        strategy: str = "balanced",
        budgets: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        Optimize billboard slot selection for multiple products
        
        Args:
            products: List of product dictionaries with influence_demand, budget, etc.
            slots: List of billboard slot dictionaries
            strategy: Optimization strategy ("common_slots", "disjoint_slots", "balanced")
            budgets: Optional budget constraints per product
        
        Returns:
            Optimization result with selected slots and influence metrics
        """
        if not self.influence_optimizer:
            raise ValueError("Multi-Product Influence Optimizer not available")
        
        # Add products and slots to optimizer
        from .advanced_modules.influence_maximization.multi_product_optimizer import Product, BillboardSlot
        
        for product_data in products:
            product = Product(
                product_id=product_data["product_id"],
                influence_demand=product_data.get("influence_demand", 1000.0),
                budget=product_data.get("budget", 1000.0),
                target_users=product_data.get("target_users", [])
            )
            self.influence_optimizer.add_product(product)
        
        for slot_data in slots:
            slot = BillboardSlot(
                slot_id=slot_data["slot_id"],
                billboard_id=slot_data["billboard_id"],
                location=tuple(slot_data["location"]),
                time_interval=tuple(slot_data["time_interval"]),
                cost=slot_data.get("cost", 100.0),
                influence_probability=slot_data.get("influence_probability", {})
            )
            self.influence_optimizer.add_slot(slot)
        
        # Run optimization
        if strategy == "common_slots":
            total_budget = sum(budgets.values()) if budgets else 5000.0
            min_influences = {p["product_id"]: p.get("min_influence", 0) for p in products}
            result = self.influence_optimizer.optimize_common_slots(total_budget, min_influences)
        elif strategy == "disjoint_slots":
            product_budgets = budgets or {p["product_id"]: p.get("budget", 1000.0) for p in products}
            min_influences = {p["product_id"]: p.get("min_influence", 0) for p in products}
            result = self.influence_optimizer.optimize_disjoint_slots(product_budgets, min_influences)
        else:  # balanced
            product_budgets = budgets or {p["product_id"]: p.get("budget", 1000.0) for p in products}
            result = self.influence_optimizer.optimize_balanced(product_budgets)
        
        return {
            "selected_slots": {pid: slots for pid, slots in result.selected_slots.items()},
            "total_influence": result.total_influence,
            "total_cost": result.total_cost,
            "product_influences": result.product_influences,
            "balance_score": result.balance_score
        }
    
    def co_create_marketing_strategy(
        self,
        ad_corpus: List[Dict[str, Any]],
        product_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Co-create marketing strategy using MindFuse
        
        Args:
            ad_corpus: List of ad data for analysis
            product_info: Product/service information
        
        Returns:
            Dictionary with personas, themes, and campaign narratives
        """
        if not self.mindfuse:
            raise ValueError("MindFuse Strategy Co-Creator not available")
        
        # Extract content pillars
        pillars = self.mindfuse.extract_content_pillars(ad_corpus)
        
        # Mine personas
        personas = self.mindfuse.mine_personas(ad_corpus)
        
        # Mine themes
        themes = self.mindfuse.mine_themes(ad_corpus)
        
        # Generate campaign narratives
        narratives = []
        if personas and themes:
            # Generate narrative for first persona-theme combination
            narrative = self.mindfuse.generate_campaign_narrative(
                persona=personas[0],
                theme=themes[0],
                product_info=product_info
            )
            narratives.append({
                "narrative_id": narrative.narrative_id,
                "story": narrative.story,
                "campaign_insight": narrative.campaign_insight,
                "content_brief": narrative.content_brief,
                "suggested_offerings": narrative.suggested_offerings
            })
        
        return {
            "content_pillars": [{"name": p.name, "description": p.description} for p in pillars],
            "personas": [{"name": p.name, "description": p.description} for p in personas],
            "themes": [{"name": t.name, "description": t.description} for t in themes],
            "campaign_narratives": narratives
        }
    
    def generate_ctr_optimized_image(
        self,
        product_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate CTR-optimized advertising image
        
        Args:
            product_info: Product information dictionary
        
        Returns:
            Dictionary with generated image info and CTR prediction
        """
        if not self.ctr_generator:
            raise ValueError("CTR-Driven Image Generator not available")
        
        from .advanced_modules.ctr_generation.ctr_driven_generator import ProductInfo
        
        product = ProductInfo(
            product_id=product_info.get("product_id", "unknown"),
            title=product_info.get("title", ""),
            category=product_info.get("category", ""),
            attributes=product_info.get("attributes", {}),
            image_path=product_info.get("image_path"),
            caption=product_info.get("caption")
        )
        
        result = self.ctr_generator.generate_ctr_optimized_image(product)
        
        return {
            "image_path": result.image_path,
            "background_description": result.background_description,
            "predicted_ctr": result.predicted_ctr,
            "product_alignment_score": result.product_alignment_score
        }
    
    def predict_cvr_multi_attribution(
        self,
        features: List[float],
        touchpoints: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """
        Predict CVR using multi-attribution learning
        
        Args:
            features: Input feature vector
            touchpoints: List of ad interaction touchpoints
        
        Returns:
            Dictionary with CVR predictions under different attribution mechanisms
        """
        if not self.multi_attribution:
            raise ValueError("Multi-Attribution Learner not available")
        
        import torch
        from .advanced_modules.multi_attribution.multi_attribution_learner import AttributionMechanism
        
        # Calculate attribution labels
        attribution_labels = {}
        for mechanism in AttributionMechanism:
            weights = self.multi_attribution.calculate_attribution_weights(touchpoints, mechanism)
            total_weight = sum(weights.values())
            attribution_labels[mechanism] = {
                "weights": weights,
                "is_positive": total_weight > 0
            }
        
        # Predict CVR (simplified - would use actual model in production)
        feature_tensor = torch.tensor([features], dtype=torch.float32)
        cvr_prediction = self.multi_attribution.predict_cvr(feature_tensor)
        
        return {
            "predicted_cvr": cvr_prediction,
            "attribution_weights": {k.value: v["weights"] for k, v in attribution_labels.items()}
        }
    
    def forecast_market_growth(
        self,
        nodes: List[Dict[str, Any]],
        interactions: List[Tuple[str, str, float]],
        metrics_history: List[Dict[str, Any]],
        forecast_horizon: int = 7
    ) -> Dict[str, Any]:
        """
        Forecast market growth and content diffusion
        
        Args:
            nodes: List of diffusion graph nodes
            interactions: List of graph edges (node1_id, node2_id, weight)
            metrics_history: Historical market metrics
            forecast_horizon: Number of days to forecast
        
        Returns:
            Forecasting result with predictions and recommendations
        """
        if not self.market_forecaster:
            raise ValueError("Market Forecasting DSS not available")
        
        from .advanced_modules.decision_support.market_forecaster import ContentDiffusionNode, MarketMetrics
        
        # Convert nodes
        diffusion_nodes = []
        for node_data in nodes:
            node = ContentDiffusionNode(
                node_id=node_data["node_id"],
                node_type=node_data.get("node_type", "user"),
                features=np.array(node_data.get("features", [0.0] * 64)),
                timestamp=datetime.fromisoformat(node_data.get("timestamp", datetime.now().isoformat()))
            )
            diffusion_nodes.append(node)
        
        # Convert metrics
        market_metrics = []
        for metric_data in metrics_history:
            metric = MarketMetrics(
                timestamp=datetime.fromisoformat(metric_data.get("timestamp", datetime.now().isoformat())),
                reach=metric_data.get("reach", 0),
                frequency=metric_data.get("frequency", 0.0),
                results=metric_data.get("results", 0),
                cpr=metric_data.get("cpr", 0.0),
                spend=metric_data.get("spend", 0.0),
                cpm=metric_data.get("cpm", 0.0),
                ctr=metric_data.get("ctr", 0.0),
                cr=metric_data.get("cr", 0.0)
            )
            market_metrics.append(metric)
        
        # Forecast
        result = self.market_forecaster.forecast_market_growth(
            nodes=diffusion_nodes,
            interactions=interactions,
            metrics_history=market_metrics,
            forecast_horizon=forecast_horizon
        )
        
        return {
            "forecasted_metrics": result.forecasted_metrics,
            "confidence_intervals": {
                k: {"lower": v[0], "upper": v[1]}
                for k, v in result.confidence_intervals.items()
            },
            "recommendations": result.recommendations,
            "causal_effects": result.causal_effects
        }
















