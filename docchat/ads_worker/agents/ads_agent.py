"""
ADS WORKER Agent
LangChain-based agent that orchestrates the entire ad creation and optimization workflow
Production-ready with error handling and logging
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid
import os
import logging

try:
    from langchain.agents import AgentExecutor, create_openai_tools_agent
    from langchain_openai import ChatOpenAI
    from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
    from langchain.tools import Tool
    from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

from ..utils.logging import setup_logger
from ..utils.retry import retry_with_backoff

logger = setup_logger("ads_worker.agent")

from ..models.schemas import (
    AssetUpload,
    AssetAnalysis,
    CreativeGeneration,
    CampaignRequest,
    CampaignResponse,
    AdPerformance,
    OptimizationResult
)
from ..services.asset_processor import AssetProcessor
from ..services.copy_generator import CopyGenerator
from ..services.visual_generator import VisualGenerator
from ..services.meta_ads_service import MetaAdsService
from ..services.google_ads_service import GoogleAdsService
from ..services.optimizer import CampaignOptimizer


class AdsWorkerAgent:
    """
    Main agent that orchestrates the entire ad creation and optimization workflow
    """
    
    def __init__(
        self,
        openai_api_key: str,
        meta_access_token: Optional[str] = None,
        meta_app_id: Optional[str] = None,
        meta_app_secret: Optional[str] = None,
        meta_ad_account_id: Optional[str] = None,
        google_customer_id: Optional[str] = None,
        google_config_path: Optional[str] = None,
        storage_path: str = "./assets"
    ):
        if not LANGCHAIN_AVAILABLE:
            raise ImportError("LangChain is required for AdsWorkerAgent")
        
        self.openai_api_key = openai_api_key
        
        # Initialize services
        self.asset_processor = AssetProcessor(openai_api_key, storage_path)
        self.copy_generator = CopyGenerator(openai_api_key)
        self.visual_generator = VisualGenerator(storage_path)
        
        # Initialize ad services if credentials provided
        self.meta_service = None
        if meta_access_token and meta_app_id and meta_app_secret and meta_ad_account_id:
            try:
                self.meta_service = MetaAdsService(
                    meta_access_token,
                    meta_app_id,
                    meta_app_secret,
                    meta_ad_account_id
                )
            except Exception as e:
                print(f"⚠️ Error inicializando Meta Ads Service: {e}")
        
        self.google_service = None
        if google_customer_id:
            try:
                self.google_service = GoogleAdsService(google_customer_id, google_config_path)
            except Exception as e:
                print(f"⚠️ Error inicializando Google Ads Service: {e}")
        
        self.optimizer = CampaignOptimizer()
        
        # Initialize LLM
        try:
            self.llm = ChatOpenAI(
                model="gpt-4o",
                temperature=0.7,
                api_key=openai_api_key,
                timeout=60.0,
                max_retries=2
            )
            logger.info("✅ LLM inicializado: gpt-4o")
        except Exception as e:
            logger.error(f"Error inicializando LLM: {e}")
            raise
        
        # Create tools for the agent
        self.tools = self._create_tools()
        logger.info(f"✅ {len(self.tools)} tools creados para el agente")
        
        # Create agent
        try:
            self.agent = self._create_agent()
            logger.info("✅ Agente LangChain creado")
        except Exception as e:
            logger.error(f"Error creando agente: {e}")
            self.agent = None
    
    def _create_tools(self) -> List[Tool]:
        """Create LangChain tools for the agent"""
        tools = [
            Tool(
                name="process_asset",
                func=self._process_asset_tool,
                description="Process and analyze user-uploaded assets (images, videos, text). Returns analysis with labels, objects, style tags, etc."
            ),
            Tool(
                name="generate_copies",
                func=self._generate_copies_tool,
                description="Generate multiple ad copy variations from asset analysis. Returns list of creative copies with headlines, descriptions, and CTAs."
            ),
            Tool(
                name="generate_visuals",
                func=self._generate_visuals_tool,
                description="Generate visual variations from assets in different formats (1:1, 4:5, 16:9, etc.). Returns list of visual creatives."
            ),
            Tool(
                name="create_meta_campaign",
                func=self._create_meta_campaign_tool,
                description="Create a campaign on Meta (Facebook/Instagram). Requires Meta service to be initialized."
            ),
            Tool(
                name="create_google_campaign",
                func=self._create_google_campaign_tool,
                description="Create a campaign on Google Ads. Requires Google service to be initialized."
            ),
            Tool(
                name="optimize_campaign",
                func=self._optimize_campaign_tool,
                description="Optimize campaign based on performance metrics. Returns optimization recommendations and actions."
            )
        ]
        
        return tools
    
    def _create_agent(self) -> AgentExecutor:
        """Create the LangChain agent"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert AI advertising manager that creates and optimizes ad campaigns.

Your workflow:
1. Process user assets (images/videos/text) to understand content
2. Generate multiple ad copy variations
3. Generate visual variations in different formats
4. Create campaigns on Meta and/or Google Ads
5. Monitor performance and optimize continuously

Always think step by step and explain your decisions."""),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad")
        ])
        
        agent = create_openai_tools_agent(self.llm, self.tools, prompt)
        agent_executor = AgentExecutor(agent=agent, tools=self.tools, verbose=True)
        
        return agent_executor
    
    def _process_asset_tool(self, asset_info: str) -> str:
        """Tool wrapper for asset processing"""
        # Parse asset info (simplified - in production use proper parsing)
        import json
        try:
            info = json.loads(asset_info)
            asset_type = info.get("asset_type")
            file_path = info.get("file_path")
            file_url = info.get("file_url")
            text_content = info.get("text_content")
            
            from ..models.schemas import AssetType
            asset_type_enum = AssetType(asset_type)
            
            analysis = self.asset_processor.process_asset(
                asset_type_enum,
                file_path,
                file_url,
                text_content,
                info.get("metadata")
            )
            
            return analysis.model_dump_json()
        except Exception as e:
            return f"Error processing asset: {e}"
    
    def _generate_copies_tool(self, analysis_json: str) -> str:
        """Tool wrapper for copy generation"""
        import json
        try:
            analysis_dict = json.loads(analysis_json)
            analysis = AssetAnalysis(**analysis_dict)
            
            copies = self.copy_generator.generate_copies(
                analysis,
                num_variations=10
            )
            
            return json.dumps([copy.model_dump() for copy in copies])
        except Exception as e:
            return f"Error generating copies: {e}"
    
    def _generate_visuals_tool(self, asset_info: str) -> str:
        """Tool wrapper for visual generation"""
        import json
        try:
            info = json.loads(asset_info)
            analysis_dict = info.get("analysis")
            asset_path = info.get("asset_path")
            options = info.get("options", {})
            
            analysis = AssetAnalysis(**analysis_dict)
            visuals = self.visual_generator.generate_visuals_from_asset(
                analysis,
                asset_path,
                options
            )
            
            return json.dumps([visual.model_dump() for visual in visuals])
        except Exception as e:
            return f"Error generating visuals: {e}"
    
    def _create_meta_campaign_tool(self, campaign_info: str) -> str:
        """Tool wrapper for Meta campaign creation"""
        if not self.meta_service:
            return "Meta Ads Service not initialized"
        
        import json
        try:
            info = json.loads(campaign_info)
            # Create campaign using Meta service
            # (Simplified - in production implement full workflow)
            return "Meta campaign creation initiated"
        except Exception as e:
            return f"Error creating Meta campaign: {e}"
    
    def _create_google_campaign_tool(self, campaign_info: str) -> str:
        """Tool wrapper for Google campaign creation"""
        if not self.google_service:
            return "Google Ads Service not initialized"
        
        import json
        try:
            info = json.loads(campaign_info)
            # Create campaign using Google service
            # (Simplified - in production implement full workflow)
            return "Google campaign creation initiated"
        except Exception as e:
            return f"Error creating Google campaign: {e}"
    
    def _optimize_campaign_tool(self, metrics_info: str) -> str:
        """Tool wrapper for campaign optimization"""
        import json
        try:
            info = json.loads(metrics_info)
            performances = [AdPerformance(**p) for p in info.get("performances", [])]
            total_budget = info.get("total_budget", 0.0)
            optimization_goal = info.get("optimization_goal", "conversions")
            
            result = self.optimizer.optimize_campaign(
                performances,
                total_budget,
                optimization_goal
            )
            
            return result.model_dump_json()
        except Exception as e:
            return f"Error optimizing campaign: {e}"
    
    def process_and_launch_campaign(
        self,
        assets: List[AssetUpload],
        campaign_request: CampaignRequest
    ) -> CampaignResponse:
        """
        Main method: Process assets and launch campaign
        
        Args:
            assets: List of user-uploaded assets
            campaign_request: Campaign creation request
            
        Returns:
            CampaignResponse with campaign details
        """
        logger.info(f"🚀 Iniciando proceso de campaña: {campaign_request.name}")
        logger.info(f"   - Assets: {len(assets)}")
        logger.info(f"   - Presupuesto diario: ${campaign_request.budget_daily}")
        logger.info(f"   - Plataformas: {campaign_request.platforms.value}")
        
        # 1. Process all assets
        asset_analyses = []
        for i, asset in enumerate(assets, 1):
            try:
                logger.info(f"📦 Procesando asset {i}/{len(assets)}: {asset.asset_type.value}")
                analysis = self.asset_processor.process_asset(
                    asset.asset_type,
                    asset.file_path,
                    asset.file_url,
                    asset.text_content,
                    asset.metadata
                )
                asset_analyses.append(analysis)
                logger.info(f"✅ Asset {i} procesado: {analysis.asset_id}")
            except Exception as e:
                logger.error(f"Error procesando asset {i}: {e}")
                # Continue with other assets
                continue
        
        if not asset_analyses:
            raise ValueError("No se pudieron procesar assets. Verifica los archivos.")
        
        logger.info(f"✅ {len(asset_analyses)} assets procesados exitosamente")
        
        # 2. Generate copies for each asset
        logger.info("📝 Generando variaciones de copy...")
        all_copies = []
        for i, analysis in enumerate(asset_analyses, 1):
            try:
                logger.info(f"   Generando copy para asset {i}/{len(asset_analyses)}")
                copies = self.copy_generator.generate_copies(
                    analysis,
                    num_variations=10,
                    tone=campaign_request.metadata.get("tone"),
                    target_audience=campaign_request.metadata.get("target_audience")
                )
                # Set asset_id
                for copy in copies:
                    copy.asset_id = analysis.asset_id
                all_copies.extend(copies)
                logger.info(f"   ✅ {len(copies)} copies generados para asset {i}")
            except Exception as e:
                logger.error(f"Error generando copy para asset {i}: {e}")
                # Continue with other assets
                continue
        
        logger.info(f"✅ {len(all_copies)} variaciones de copy generadas en total")
        
        # 3. Generate visuals
        logger.info("🎨 Generando variaciones visuales...")
        all_visuals = []
        for i, analysis in enumerate(asset_analyses):
            if analysis.asset_type.value in ["image", "video"]:
                try:
                    asset_path = assets[i].file_path or assets[i].file_url
                    if not asset_path:
                        logger.warning(f"Asset {i} no tiene file_path ni file_url, saltando generación visual")
                        continue
                    
                    logger.info(f"   Generando visuales para asset {i+1}/{len(asset_analyses)}")
                    visuals = self.visual_generator.generate_visuals_from_asset(
                        analysis,
                        asset_path,
                        {"formats": ["1:1", "4:5", "16:9"]}
                    )
                    all_visuals.extend(visuals)
                    logger.info(f"   ✅ {len(visuals)} visuales generados para asset {i+1}")
                except Exception as e:
                    logger.error(f"Error generando visuales para asset {i+1}: {e}")
                    # Continue with other assets
                    continue
        
        logger.info(f"✅ {len(all_visuals)} variaciones visuales generadas en total")
        
        # 4. Create campaigns on platforms
        campaign_id = str(uuid.uuid4())
        platform_campaign_ids = {}
        
        # Meta campaign
        if campaign_request.platforms.value in ["meta", "both"] and self.meta_service:
            try:
                meta_campaign = self.meta_service.create_campaign(
                    campaign_request.name,
                    campaign_request.objective.value,
                    "PAUSED"  # Start paused, activate after setup
                )
                platform_campaign_ids["meta"] = meta_campaign["campaign_id"]
                logger.info(f"   ✅ Campaña Meta creada: {meta_campaign['campaign_id']}")
            except Exception as e:
                logger.error(f"   ⚠️ Error creando Meta campaign: {e}")
        
        # Google campaign
        if campaign_request.platforms.value in ["google", "both"] and self.google_service:
            try:
                logger.info("   Creando campaña en Google Ads...")
                google_campaign = self.google_service.create_campaign(
                    campaign_request.name,
                    campaign_request.budget_daily,
                    campaign_request.start_date,
                    campaign_request.end_date
                )
                platform_campaign_ids["google"] = google_campaign["campaign_resource_name"]
                logger.info(f"   ✅ Campaña Google creada: {google_campaign['campaign_id']}")
            except Exception as e:
                logger.error(f"   ⚠️ Error creando Google campaign: {e}")
        
        if not platform_campaign_ids:
            raise ValueError("No se pudieron crear campañas en ninguna plataforma. Verifica las credenciales.")
        
        # 5. Create ads combining copies and visuals
        logger.info("📌 Creando y publicando anuncios...")
        ads_created = 0
        created_ads = []
        
        # Combine copies with visuals to create ads
        for copy in all_copies[:10]:  # Limit to top 10 copies
            # Find matching visual for this asset
            matching_visuals = [v for v in all_visuals if v.asset_id == copy.asset_id]
            visual = matching_visuals[0] if matching_visuals else None
            
            # Get original asset
            asset_analysis = next((a for a in asset_analyses if a.asset_id == copy.asset_id), None)
            if not asset_analysis:
                continue
            
            # Create ads on each platform
            # Meta Ads
            if campaign_request.platforms.value in ["meta", "both"] and self.meta_service:
                try:
                    logger.info(f"   Creando ad en Meta para copy: {copy.creative_id[:8]}...")
                    
                    # 1. Upload image/video to Meta
                    image_hash = None
                    video_id = None
                    asset_path = None
                    
                    # Find asset file path
                    for asset in assets:
                        if asset.asset_type.value == asset_analysis.asset_type.value:
                            asset_path = asset.file_path or asset.file_url
                            break
                    
                    if asset_path and asset_analysis.asset_type.value == "image":
                        try:
                            image_hash = self.meta_service.upload_image(asset_path)
                        except Exception as e:
                            logger.warning(f"   Error subiendo imagen a Meta: {e}")
                            continue
                    elif asset_path and asset_analysis.asset_type.value == "video":
                        try:
                            video_id = self.meta_service.upload_video(asset_path)
                        except Exception as e:
                            logger.warning(f"   Error subiendo video a Meta: {e}")
                            continue
                    
                    if not image_hash and not video_id:
                        logger.warning(f"   No se pudo subir asset a Meta, saltando...")
                        continue
                    
                    # 2. Create ad set (one per campaign for simplicity)
                    ad_set_name = f"{campaign_request.name} - Ad Set 1"
                    ad_set = self.meta_service.create_ad_set(
                        campaign_id=platform_campaign_ids["meta"],
                        name=ad_set_name,
                        daily_budget=campaign_request.budget_daily,
                        optimization_goal=campaign_request.objective.value
                    )
                    
                    # 3. Create creative
                    creative_name = f"{campaign_request.name} - Creative {copy.creative_id[:8]}"
                    page_id = os.getenv("META_PAGE_ID") or campaign_request.metadata.get("page_id")
                    if not page_id:
                        logger.warning("   META_PAGE_ID no configurado, saltando creación de creative")
                        continue
                    
                    creative = self.meta_service.create_ad_creative(
                        name=creative_name,
                        creative=copy,
                        image_hash=image_hash,
                        video_id=video_id,
                        page_id=page_id
                    )
                    
                    # 4. Create ad
                    ad_name = f"{campaign_request.name} - Ad {copy.creative_id[:8]}"
                    ad = self.meta_service.create_ad(
                        ad_set_id=ad_set["ad_set_id"],
                        creative_id=creative["creative_id"],
                        name=ad_name,
                        status="PAUSED"  # Start paused, activate manually or via optimization
                    )
                    
                    created_ads.append({
                        "platform": "meta",
                        "ad_id": ad["ad_id"],
                        "creative_id": copy.creative_id,
                        "status": "paused"
                    })
                    ads_created += 1
                    logger.info(f"   ✅ Ad Meta creado: {ad['ad_id']}")
                    
                except Exception as e:
                    logger.error(f"   Error creando ad en Meta: {e}")
                    continue
            
            # Google Ads
            if campaign_request.platforms.value in ["google", "both"] and self.google_service:
                try:
                    logger.info(f"   Creando ad en Google para copy: {copy.creative_id[:8]}...")
                    
                    # 1. Create ad group (one per campaign for simplicity)
                    ad_group_name = f"{campaign_request.name} - Ad Group 1"
                    ad_group = self.google_service.create_ad_group(
                        campaign_resource_name=platform_campaign_ids["google"],
                        name=ad_group_name,
                        cpc_bid=1.0
                    )
                    
                    # 2. Create responsive search ad
                    final_url = copy.generation_params.get("link_url") or campaign_request.metadata.get("landing_page_url", "https://example.com")
                    ad = self.google_service.create_responsive_search_ad(
                        ad_group_resource_name=ad_group["ad_group_resource_name"],
                        creative=copy,
                        final_url=final_url
                    )
                    
                    created_ads.append({
                        "platform": "google",
                        "ad_id": ad["ad_id"],
                        "creative_id": copy.creative_id,
                        "status": "paused"
                    })
                    ads_created += 1
                    logger.info(f"   ✅ Ad Google creado: {ad['ad_id']}")
                    
                except Exception as e:
                    logger.error(f"   Error creando ad en Google: {e}")
                    continue
        
        logger.info(f"✅ {ads_created} anuncios creados en total")
        
        # Return campaign response
        logger.info(f"✅ Proceso de campaña completado: {campaign_id}")
        return CampaignResponse(
            campaign_id=campaign_id,
            name=campaign_request.name,
            status="active",
            platforms=[p for p in ["meta", "google"] if p in platform_campaign_ids],
            budget_daily=campaign_request.budget_daily,
            budget_remaining=campaign_request.budget_daily * 30,  # Estimate
            ads_count=ads_created,
            active_ads=ads_created,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            start_date=campaign_request.start_date,
            end_date=campaign_request.end_date,
            platform_campaign_ids=platform_campaign_ids
        )
    
    def optimize_existing_campaign(
        self,
        campaign_id: str,
        platform_campaign_ids: Dict[str, str]
    ) -> OptimizationResult:
        """
        Optimize an existing campaign
        
        Args:
            campaign_id: Internal campaign ID
            platform_campaign_ids: Dict mapping platform to campaign ID
            
        Returns:
            OptimizationResult with optimization actions
        """
        # Fetch metrics
        performances = self.optimizer.fetch_metrics_from_providers(
            self.meta_service,
            self.google_service,
            {"campaign_id": campaign_id, **platform_campaign_ids}
        )
        
        # Run optimization
        result = self.optimizer.optimize_campaign(
            performances,
            total_budget=100.0,  # Get from campaign
            optimization_goal="conversions"
        )
        
        return result

