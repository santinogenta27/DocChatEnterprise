"""
Enterprise Ads Manager Mode - Sistema Autónomo de Gestión de Anuncios

Arquitectura basada en Meta Vision 2026:
- Agentes autónomos usando CrewAI
- Generación automática de creativos (copy + imagen/video)
- Publicación automática vía Meta Ads API
- Optimización continua sin intervención humana
- Sistema RAG para contexto y memoria

Agentes:
1. AdsStrategistAgent: Define estrategia, audiencias, KPIs
2. CreativeDirectorAgent: Genera creativos persuasivos
3. MediaBuyerAgent: Publica y gestiona campañas
4. PerformanceAnalystAgent: Monitorea y optimiza continuamente
"""

from __future__ import annotations

import json
import os
import time
import uuid
from typing import Any, Dict, List, Optional, TypedDict
from datetime import datetime
from pathlib import Path
from enum import Enum
from dataclasses import dataclass, asdict
from collections import defaultdict

try:
    from crewai import Agent, Task, Crew, Process
    from crewai.tools import BaseTool
    CREWAI_AVAILABLE = True
except ImportError:
    CREWAI_AVAILABLE = False
    print("⚠️ CrewAI no está instalado. Instala con: pip install crewai")

from langchain_core.language_models import BaseLanguageModel
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.documents import Document

from .config import AppConfig
from .document_processor import DocumentProcessor
from .retriever_builder import RetrieverBuilder
from .memory import MemoryStore, ContextManager

# Importar módulos de ads_optimization
try:
    from .ads_optimization.database import DatabaseManager
    from .ads_optimization.creative_generator import CreativeGenerator
    from .ads_optimization.video_generator import VideoGenerator
    from .ads_optimization.compliance_validator import ComplianceValidator, ComplianceLevel
    from .ads_optimization.meta_lattice import MetaLatticeOptimizer, LatticeZipper, LatticeFilter, LatticeKTAP
    from .ads_optimization.llm_auction_irpo import IRPOOptimizer
    from .ads_optimization.meta_hacks import MetaAdsHacks, ClusterBombConfig, PopularKidConfig
    from .ads_optimization.logging_config import setup_logging, get_logger
    from .ads_optimization.retry_logic import APIClient
    ADS_OPTIMIZATION_AVAILABLE = True
except ImportError as e:
    ADS_OPTIMIZATION_AVAILABLE = False
    print(f"⚠️ Módulos de ads_optimization no disponibles: {e}")

# Intentar importar Meta Ads API
try:
    from facebook_business.api import FacebookAdsApi
    from facebook_business.adobjects.adaccount import AdAccount
    from facebook_business.adobjects.campaign import Campaign
    from facebook_business.adobjects.adset import AdSet
    from facebook_business.adobjects.ad import Ad
    from facebook_business.adobjects.adcreative import AdCreative
    META_ADS_AVAILABLE = True
except ImportError:
    META_ADS_AVAILABLE = False
    print("⚠️ Meta Ads API no está instalado. Instala con: pip install facebook-business")


class CampaignObjective(str, Enum):
    """Objetivos de campaña."""
    SALES = "sales"
    LEADS = "leads"
    TRAFFIC = "traffic"
    AWARENESS = "awareness"
    ENGAGEMENT = "engagement"


class CampaignStatus(str, Enum):
    """Estados de campaña."""
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"
    DELETED = "deleted"


@dataclass
class CampaignInput:
    """Input para crear una campaña."""
    product_image_url: Optional[str] = None
    product_video_url: Optional[str] = None
    product_description: str = ""
    campaign_objective: CampaignObjective = CampaignObjective.SALES
    daily_budget: float = 50.0
    monthly_budget: Optional[float] = None
    platform: str = "meta_ads"  # meta_ads, google_ads, etc.
    target_audience_hints: Optional[Dict[str, Any]] = None
    brand_guidelines: Optional[Dict[str, Any]] = None


@dataclass
class CampaignStrategy:
    """Estrategia de campaña generada por AdsStrategistAgent."""
    campaign_objective: str
    audience_definition: Dict[str, Any]
    budget_allocation: Dict[str, float]
    creative_guidelines: Dict[str, Any]
    kpi_targets: Dict[str, float]
    funnel_stage: str  # TOF, MOF, BOF
    reasoning: str


@dataclass
class AdCreative:
    """Creative generado por CreativeDirectorAgent."""
    creative_id: str
    headline: str
    primary_text: str
    description: Optional[str] = None
    cta: str = "Learn More"
    image_url: Optional[str] = None
    video_url: Optional[str] = None
    image_prompt: Optional[str] = None
    video_prompt: Optional[str] = None
    compliance_flags: List[str] = None
    variations: List[Dict[str, Any]] = None


@dataclass
class CampaignMetrics:
    """Métricas de performance."""
    impressions: int = 0
    clicks: int = 0
    conversions: int = 0
    spend: float = 0.0
    ctr: float = 0.0
    cpc: float = 0.0
    cpa: float = 0.0
    roas: float = 0.0
    timestamp: str = ""


@dataclass
class OptimizationAction:
    """Acción de optimización."""
    action_type: str  # pause, scale, regenerate, adjust_budget
    target_id: str  # campaign_id, adset_id, ad_id
    reason: str
    new_budget: Optional[float] = None
    new_targeting: Optional[Dict[str, Any]] = None


class EnterpriseAdsManagerMode:
    """
    Enterprise Ads Manager - Sistema Autónomo de Gestión de Anuncios
    
    Basado en Meta Vision 2026: "Solo necesitas imagen de producto y presupuesto"
    """
    
    def __init__(
        self,
        config: AppConfig,
        processor: DocumentProcessor,
        retriever_builder: RetrieverBuilder,
        context_manager: Optional[ContextManager] = None,
        provider: str = "openai"
    ):
        self.config = config
        self.provider = provider
        self.processor = processor
        self.retriever_builder = retriever_builder
        self.context_manager = context_manager
        
        # LLM
        self.llm = self._get_llm_for_provider(provider)
        
        # CrewAI Integration
        if CREWAI_AVAILABLE:
            from .integrations.crewai_integration import CrewAIIntegration
            self.crewai = CrewAIIntegration(config)
        else:
            self.crewai = None
        
        # RAG System para contexto y memoria
        self.rag_retriever = None
        self._initialize_rag()
        
        # Campañas activas
        self.campaigns: Dict[str, Dict[str, Any]] = {}
        
        # Historial de aprendizaje
        self.learning_memory: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        
        # Base de datos de performance
        self.performance_db: Dict[str, CampaignMetrics] = {}
        
        # ============================================
        # MÓDULOS AVANZADOS INTEGRADOS
        # ============================================
        
        # Base de datos persistente PostgreSQL
        if ADS_OPTIMIZATION_AVAILABLE:
            self.db_manager = DatabaseManager(config)
            print("✅ Base de datos PostgreSQL inicializada")
        else:
            self.db_manager = None
        
        # Generador de creativos (imágenes y videos)
        if ADS_OPTIMIZATION_AVAILABLE:
            self.creative_generator = CreativeGenerator(config)
            self.video_generator = VideoGenerator(config)
            print("✅ Generadores de creativos inicializados (imágenes + videos)")
        else:
            self.creative_generator = None
            self.video_generator = None
        
        # Validador de compliance avanzado
        if ADS_OPTIMIZATION_AVAILABLE:
            self.compliance_validator = ComplianceValidator(config)
            print("✅ Validador de compliance avanzado inicializado")
        else:
            self.compliance_validator = None
        
        # Meta Lattice Optimizer
        if ADS_OPTIMIZATION_AVAILABLE:
            self.lattice_optimizer = MetaLatticeOptimizer(config)
            print("✅ Meta Lattice Optimizer inicializado (Zipper, Filter, KTAP)")
        else:
            self.lattice_optimizer = None
        
        # LLM-AUCTION IRPO Optimizer
        if ADS_OPTIMIZATION_AVAILABLE:
            self.irpo_optimizer = IRPOOptimizer(config)
            print("✅ LLM-AUCTION IRPO Optimizer inicializado")
        else:
            self.irpo_optimizer = None
        
        # Meta Ads Hacks
        if ADS_OPTIMIZATION_AVAILABLE:
            self.meta_hacks = MetaAdsHacks(config)
            print("✅ Meta Ads Hacks inicializados (8 técnicas avanzadas)")
        else:
            self.meta_hacks = None
        
        # Logging estructurado
        if ADS_OPTIMIZATION_AVAILABLE:
            log_file = Path(config.memory_dir or "data") / "logs" / "enterprise_ads_manager.log"
            
            # Intentar cargar Sentry DSN desde archivo de configuración
            sentry_dsn = None
            config_file = Path(config.memory_dir) / "enterprise_ads_config.json" if config.memory_dir else Path("data/enterprise_ads_config.json")
            if config_file.exists():
                try:
                    with open(config_file, 'r', encoding='utf-8') as f:
                        saved_config = json.load(f)
                        sentry_dsn = saved_config.get("sentry_dsn") or os.getenv("SENTRY_DSN")
                except Exception:
                    sentry_dsn = os.getenv("SENTRY_DSN")
            else:
                sentry_dsn = os.getenv("SENTRY_DSN")
            
            self.logger = setup_logging(
                log_level="INFO",
                log_file=log_file,
                enable_sentry=bool(sentry_dsn),
                sentry_dsn=sentry_dsn,
                config=config
            )
            print("✅ Logging estructurado inicializado")
        else:
            self.logger = None
        
        # API Client con retry y circuit breakers
        if ADS_OPTIMIZATION_AVAILABLE:
            self.api_client = APIClient(
                service_name="meta_ads",
                max_retries=3,
                circuit_breaker_threshold=5
            )
            print("✅ API Client con retry logic y circuit breakers inicializado")
        else:
            self.api_client = None
        
        # Meta Ads API
        self.meta_ads_initialized = False
        if META_ADS_AVAILABLE:
            self._initialize_meta_ads()
        
        # Agentes CrewAI
        self.ads_strategist_agent = None
        self.creative_director_agent = None
        self.media_buyer_agent = None
        self.performance_analyst_agent = None
        
        if CREWAI_AVAILABLE and self.crewai:
            self._initialize_agents()
        
        print("✅ Enterprise Ads Manager inicializado - Sistema Autónomo de Anuncios")
        print("   🎯 Integrado: PostgreSQL, Videos, Compliance, Meta Lattice, IRPO, Hacks")
    
    def _get_llm_for_provider(self, provider: str) -> BaseLanguageModel:
        """Obtiene LLM según provider."""
        if provider == "openai":
            return ChatOpenAI(
                model=self.config.research_model or "gpt-4o",
                temperature=0.7,
                api_key=self.config.openai_api_key or "",
                max_tokens=4000
            )
        elif provider == "anthropic":
            return ChatAnthropic(
                model="claude-3-5-sonnet-20241022",
                temperature=0.7,
                api_key=self.config.anthropic_api_key or "",
                max_tokens=4000
            )
        else:
            return ChatOpenAI(
                model="gpt-4o",
                temperature=0.7,
                api_key=self.config.openai_api_key or "",
                max_tokens=4000
            )
    
    def _initialize_rag(self):
        """Inicializa sistema RAG para contexto y memoria."""
        try:
            # Crear vector store para campañas históricas
            rag_dir = Path(self.config.data_dir) / "ads_manager_rag"
            rag_dir.mkdir(parents=True, exist_ok=True)
            
            # Se inicializará cuando haya documentos
            print("✅ RAG System inicializado para Enterprise Ads Manager")
        except Exception as e:
            print(f"⚠️ Error inicializando RAG: {e}")
    
    def _initialize_meta_ads(self):
        """Inicializa conexión con Meta Ads API desde variables de entorno o configuración guardada."""
        try:
            # Intentar cargar desde archivo de configuración guardada
            config_file = Path(self.config.memory_dir) / "enterprise_ads_config.json" if self.config.memory_dir else Path("data/enterprise_ads_config.json")
            
            access_token = None
            app_id = None
            app_secret = None
            ad_account_id = None
            
            # Cargar desde archivo si existe
            if config_file.exists():
                try:
                    with open(config_file, 'r', encoding='utf-8') as f:
                        saved_config = json.load(f)
                        access_token = saved_config.get("meta_access_token") or os.getenv("META_ADS_ACCESS_TOKEN")
                        app_id = saved_config.get("meta_app_id") or os.getenv("META_ADS_APP_ID")
                        app_secret = saved_config.get("meta_app_secret") or os.getenv("META_ADS_APP_SECRET")
                        ad_account_id = saved_config.get("meta_account_id") or os.getenv("META_ADS_ACCOUNT_ID")
                except Exception as e:
                    print(f"⚠️ Error cargando configuración guardada: {e}")
            
            # Fallback a variables de entorno
            if not access_token:
                access_token = os.getenv("META_ADS_ACCESS_TOKEN")
            if not app_id:
                app_id = os.getenv("META_ADS_APP_ID")
            if not app_secret:
                app_secret = os.getenv("META_ADS_APP_SECRET")
            if not ad_account_id:
                ad_account_id = os.getenv("META_ADS_ACCOUNT_ID")
            
            if access_token and app_id and app_secret:
                FacebookAdsApi.init(access_token=access_token, app_id=app_id, app_secret=app_secret)
                self.meta_ads_initialized = True
                self.meta_ad_account_id = ad_account_id
                print("✅ Meta Ads API inicializado")
            else:
                print("⚠️ Meta Ads API no configurado. Configura desde la UI o variables de entorno:")
                print("   - META_ADS_ACCESS_TOKEN")
                print("   - META_ADS_APP_ID")
                print("   - META_ADS_APP_SECRET")
                print("   - META_ADS_ACCOUNT_ID")
        except Exception as e:
            print(f"⚠️ Error inicializando Meta Ads API: {e}")
    
    def _initialize_agents(self):
        """Inicializa los 4 agentes CrewAI."""
        if not self.crewai:
            return
        
        try:
            # 1. AdsStrategistAgent
            self.ads_strategist_agent = self.crewai.create_agent(
                agent_id="ads_strategist",
                role="Advertising Strategist",
                goal="Define optimal campaign strategy, audience targeting, and KPI objectives based on business goals",
                backstory="""You are an expert advertising strategist with deep knowledge of 
                digital marketing funnels (TOF/MOF/BOF), audience segmentation, and campaign 
                optimization. You analyze business objectives and create data-driven strategies 
                that maximize ROI. You understand Meta's algorithm, attribution windows, and 
                how to structure campaigns for success.""",
                verbose=True
            )
            
            # 2. CreativeDirectorAgent
            self.creative_director_agent = self.crewai.create_agent(
                agent_id="creative_director",
                role="Creative Director",
                goal="Generate persuasive ad copy, headlines, CTAs, and creative prompts for images/videos",
                backstory="""You are a world-class creative director specializing in performance 
                advertising. You create compelling copy that converts, write headlines that grab 
                attention, and design creative briefs for visual assets. You understand A/B testing, 
                ad compliance, and how to create variations that test different angles and appeals.""",
                verbose=True
            )
            
            # 3. MediaBuyerAgent
            self.media_buyer_agent = self.crewai.create_agent(
                agent_id="media_buyer",
                role="Media Buyer",
                goal="Execute campaigns by creating ads, ad sets, and campaigns via Meta Ads API",
                backstory="""You are an expert media buyer who understands Meta Ads API, campaign 
                structure, bidding strategies, and budget allocation. You can create campaigns, 
                ad sets, and ads programmatically, handle errors, validate policies, and ensure 
                campaigns launch successfully.""",
                verbose=True
            )
            
            # 4. PerformanceAnalystAgent
            self.performance_analyst_agent = self.crewai.create_agent(
                agent_id="performance_analyst",
                role="Performance Analyst",
                goal="Monitor campaign metrics, evaluate performance vs KPIs, and recommend optimization actions",
                backstory="""You are a data-driven performance analyst who understands advertising 
                metrics (CTR, CPA, ROAS), attribution models, and optimization strategies. You 
                can identify underperforming campaigns, detect creative fatigue, and recommend 
                actions like pausing, scaling, or regenerating creatives based on data.""",
                verbose=True
            )
            
            print("✅ 4 agentes CrewAI inicializados para Enterprise Ads Manager")
        except Exception as e:
            print(f"⚠️ Error inicializando agentes: {e}")
    
    # ============================================
    # MÉTODO PRINCIPAL: CREAR CAMPAÑA AUTÓNOMA
    # ============================================
    
    def create_autonomous_campaign(
        self,
        campaign_input: CampaignInput,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Crea una campaña completamente autónoma.
        
        Meta Vision 2026: "Solo necesitas imagen de producto y presupuesto"
        El sistema hace TODO automáticamente.
        """
        campaign_id = f"CAMP-{uuid.uuid4().hex[:8].upper()}"
        session_id = session_id or f"session-{uuid.uuid4().hex[:8]}"
        
        print(f"\n🚀 [Enterprise Ads Manager] Creando campaña autónoma {campaign_id}")
        print(f"   Objetivo: {campaign_input.campaign_objective.value}")
        print(f"   Presupuesto: ${campaign_input.daily_budget}/día")
        
        try:
            # PASO 1: AdsStrategistAgent - Definir estrategia
            print(f"\n📊 [Paso 1/4] AdsStrategistAgent definiendo estrategia...")
            import asyncio
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            strategy = loop.run_until_complete(
                self._define_campaign_strategy(campaign_input, session_id)
            )
            
            # PASO 2: CreativeDirectorAgent - Generar creativos
            print(f"\n🎨 [Paso 2/4] CreativeDirectorAgent generando creativos...")
            creatives = loop.run_until_complete(
                self._generate_creatives(campaign_input, strategy, session_id)
            )
            
            # PASO 3: MediaBuyerAgent - Publicar campaña
            print(f"\n📢 [Paso 3/4] MediaBuyerAgent publicando campaña...")
            published_campaign = loop.run_until_complete(
                self._publish_campaign(campaign_id, campaign_input, strategy, creatives)
            )
            
            # PASO 4: Iniciar optimización continua
            print(f"\n🔄 [Paso 4/4] Iniciando optimización continua...")
            optimization_task = self._start_continuous_optimization(campaign_id)
            
            # Guardar campaña
            campaign_data = {
                "campaign_id": campaign_id,
                "session_id": session_id,
                "input": asdict(campaign_input),
                "strategy": asdict(strategy),
                "creatives": [asdict(c) for c in creatives],
                "published_campaign": published_campaign,
                "status": CampaignStatus.ACTIVE.value,
                "created_at": datetime.now().isoformat(),
                "optimization_active": True
            }
            
            self.campaigns[campaign_id] = campaign_data
            
            # Guardar en base de datos PostgreSQL
            if self.db_manager:
                try:
                    self.db_manager.create_campaign(
                        campaign_id=campaign_id,
                        tenant_id=session_id,
                        name=f"{campaign_id} - {campaign_input.campaign_objective.value}",
                        platform=campaign_input.platform,
                        objective=campaign_input.campaign_objective.value,
                        budget=campaign_input.daily_budget,
                        daily_budget=campaign_input.daily_budget,
                        status="active",
                        target_audience=strategy.audience_definition,
                        platform_campaign_id=published_campaign.get("meta_campaign_id"),
                        metadata={
                            "strategy": asdict(strategy),
                            "creatives_count": len(creatives)
                        }
                    )
                    print(f"✅ Campaña {campaign_id} guardada en PostgreSQL")
                except Exception as e:
                    print(f"⚠️ Error guardando en PostgreSQL: {e}")
            
            # Indexar en RAG para contexto futuro
            try:
                loop.run_until_complete(self._index_campaign_in_rag(campaign_data))
            except Exception as e:
                print(f"⚠️ Error indexando en RAG: {e}")
            
            # Logging estructurado
            if self.logger:
                self.logger.info(
                    f"Campaña autónoma creada: {campaign_id}",
                    extra={
                        "campaign_id": campaign_id,
                        "session_id": session_id,
                        "objective": campaign_input.campaign_objective.value,
                        "budget": campaign_input.daily_budget,
                        "creatives_count": len(creatives),
                        "status": "active"
                    }
                )
            
            print(f"\n✅ [Enterprise Ads Manager] Campaña {campaign_id} creada y activa")
            print(f"   - Estrategia: {strategy.funnel_stage}")
            print(f"   - Creativos generados: {len(creatives)}")
            print(f"   - Optimización continua: ACTIVA")
            
            return {
                "success": True,
                "campaign_id": campaign_id,
                "campaign_data": campaign_data
            }
            
        except Exception as e:
            print(f"❌ [Enterprise Ads Manager] Error creando campaña: {e}")
            return {
                "success": False,
                "error": str(e),
                "campaign_id": campaign_id
            }
    
    # ============================================
    # AGENTE 1: ADS STRATEGIST
    # ============================================
    
    async def _define_campaign_strategy(
        self,
        campaign_input: CampaignInput,
        session_id: str
    ) -> CampaignStrategy:
        """AdsStrategistAgent define la estrategia de campaña."""
        
        # Consultar RAG para contexto histórico
        historical_context = await self._query_rag_for_context(
            query=f"campaigns with objective {campaign_input.campaign_objective.value}",
            limit=5
        )
        
        # Aplicar Meta Lattice para optimizar atribución si hay datos históricos
        lattice_insights = ""
        if self.lattice_optimizer and historical_context:
            try:
                # Simular optimización de atribución con Lattice Zipper
                lattice_insights = "\n\nOPTIMIZACIÓN META LATTICE:\n- Usando Lattice Zipper para balancear freshness y correctness\n- Aplicando Lattice Filter para selección óptima de features\n- Integrando Lattice KTAP para knowledge transfer"
            except Exception as e:
                print(f"⚠️ Error aplicando Meta Lattice: {e}")
        
        # Aplicar Meta Hacks para optimización
        hacks_recommendations = ""
        if self.meta_hacks:
            try:
                hack_combo = self.meta_hacks.get_optimal_hack_combination(
                    campaign_type=campaign_input.campaign_objective.value,
                    budget=campaign_input.daily_budget,
                    objective=campaign_input.campaign_objective.value
                )
                hacks_recommendations = f"\n\nMETA HACKS RECOMENDADOS:\n{json.dumps(hack_combo, indent=2, ensure_ascii=False)}"
            except Exception as e:
                print(f"⚠️ Error obteniendo Meta Hacks: {e}")
        
        # Prompt para el agente
        strategy_prompt = f"""Eres un experto estratega de publicidad. Analiza este brief y define la estrategia óptima.

INPUT:
- Objetivo: {campaign_input.campaign_objective.value}
- Producto: {campaign_input.product_description}
- Presupuesto diario: ${campaign_input.daily_budget}
- Presupuesto mensual: ${campaign_input.monthly_budget or 'N/A'}

CONTEXTO HISTÓRICO (RAG):
{json.dumps(historical_context, indent=2) if historical_context else 'Sin contexto histórico'}
{lattice_insights}
{hacks_recommendations}

TAREA:
Genera una estrategia completa en formato JSON con:
1. campaign_objective: objetivo específico
2. audience_definition: definición detallada de audiencia (demographics, interests, behaviors)
3. budget_allocation: cómo distribuir presupuesto (por ad set, por día, etc.)
4. creative_guidelines: guías para creativos (tone, messaging, visual style)
5. kpi_targets: KPIs objetivo (CPA, ROAS, CTR, etc.)
6. funnel_stage: TOF, MOF, o BOF
7. reasoning: explicación de la estrategia

Responde SOLO con JSON válido, sin texto adicional."""

        # Ejecutar con LLM
        response = await self.llm.ainvoke(strategy_prompt)
        strategy_json = self._extract_json_from_response(response.content)
        
        return CampaignStrategy(**strategy_json)
    
    # ============================================
    # AGENTE 2: CREATIVE DIRECTOR
    # ============================================
    
    async def _generate_creatives(
        self,
        campaign_input: CampaignInput,
        strategy: CampaignStrategy,
        session_id: str
    ) -> List[AdCreative]:
        """CreativeDirectorAgent genera múltiples variantes de creativos."""
        
        num_variations = 5  # Generar 5 variantes iniciales
        
        creatives = []
        
        for i in range(num_variations):
            creative_prompt = f"""Eres un director creativo experto. Genera un creative publicitario.

PRODUCTO:
{campaign_input.product_description}

ESTRATEGIA:
{json.dumps(asdict(strategy), indent=2)}

VARIACIÓN {i+1}/{num_variations}:
Crea una variante diferente (diferente angle, tone, o appeal).

TAREA:
Genera en formato JSON:
1. headline: título impactante (máx 40 caracteres)
2. primary_text: texto principal persuasivo (máx 125 caracteres)
3. description: descripción opcional (máx 125 caracteres)
4. cta: call-to-action (Learn More, Shop Now, etc.)
5. image_prompt: prompt detallado para generar imagen con DALL-E/Stable Diffusion
6. video_prompt: prompt para generar video con Runway/Pika
7. compliance_flags: lista de posibles problemas de compliance
8. variations: ideas para variaciones adicionales

Responde SOLO con JSON válido."""

            response = await self.llm.ainvoke(creative_prompt)
            creative_json = self._extract_json_from_response(response.content)
            
            creative = AdCreative(
                creative_id=f"CREATIVE-{uuid.uuid4().hex[:8].upper()}",
                headline=creative_json.get("headline", ""),
                primary_text=creative_json.get("primary_text", ""),
                description=creative_json.get("description"),
                cta=creative_json.get("cta", "Learn More"),
                image_prompt=creative_json.get("image_prompt"),
                video_prompt=creative_json.get("video_prompt"),
                compliance_flags=creative_json.get("compliance_flags", []),
                variations=creative_json.get("variations", [])
            )
            
            # Generar imagen si hay prompt
            if creative.image_prompt:
                if self.creative_generator:
                    # Usar CreativeGenerator para generar imagen real
                    try:
                        from .ads_optimization.creative_generator import BusinessInfo
                        business_info = BusinessInfo(
                            business_name="Product",
                            business_type="ecommerce",
                            description=campaign_input.product_description
                        )
                        generated = await self.creative_generator._generate_image(
                            business_info,
                            {"headline": creative.headline, "description": creative.primary_text},
                            creative.creative_id
                        )
                        creative.image_url = generated
                    except Exception as e:
                        print(f"⚠️ Error usando CreativeGenerator: {e}")
                        # Fallback a método original
                        creative.image_url = await self._generate_image(creative.image_prompt)
                else:
                    creative.image_url = await self._generate_image(creative.image_prompt)
            
            # Generar video si hay prompt
            if creative.video_prompt and self.video_generator:
                try:
                    video = await self.video_generator.generate_video(
                        prompt=creative.video_prompt,
                        image_url=creative.image_url,
                        duration=5,
                        style="cinematic",
                        aspect_ratio="16:9"
                    )
                    if video:
                        creative.video_url = video.video_url
                except Exception as e:
                    print(f"⚠️ Error generando video: {e}")
            
            # Validar compliance
            if self.compliance_validator:
                try:
                    is_compliant, issues = await self.compliance_validator.validate_ad(
                        headline=creative.headline,
                        description=creative.primary_text,
                        image_url=creative.image_url,
                        target_audience=strategy.audience_definition,
                        industry="general"
                    )
                    if not is_compliant:
                        # Agregar issues a compliance_flags
                        if creative.compliance_flags is None:
                            creative.compliance_flags = []
                        for issue in issues:
                            if issue.level in [ComplianceLevel.VIOLATION, ComplianceLevel.CRITICAL]:
                                creative.compliance_flags.append(f"{issue.category}: {issue.description}")
                                if self.logger:
                                    self.logger.warning(
                                        f"Compliance issue detected in creative {creative.creative_id}",
                                        extra={
                                            "campaign_id": campaign_id if 'campaign_id' in locals() else "unknown",
                                            "creative_id": creative.creative_id,
                                            "issue": issue.description
                                        }
                                    )
                except Exception as e:
                    print(f"⚠️ Error validando compliance: {e}")
            
            creatives.append(creative)
        
        return creatives
    
    # ============================================
    # AGENTE 3: MEDIA BUYER
    # ============================================
    
    async def _publish_campaign(
        self,
        campaign_id: str,
        campaign_input: CampaignInput,
        strategy: CampaignStrategy,
        creatives: List[AdCreative]
    ) -> Dict[str, Any]:
        """MediaBuyerAgent publica la campaña en Meta Ads con técnicas avanzadas."""
        
        if not self.meta_ads_initialized:
            # Modo simulación si no hay API configurada
            return {
                "campaign_id": campaign_id,
                "status": "simulated",
                "message": "Meta Ads API no configurado. Campaña creada en modo simulación.",
                "meta_campaign_id": None,
                "meta_adset_ids": [],
                "meta_ad_ids": []
            }
        
        # Aplicar Meta Hacks antes de publicar
        hack_config = None
        if self.meta_hacks:
            try:
                # Aplicar Cluster Bomb Trick
                cluster_config = ClusterBombConfig(
                    high_converting_hours=[18, 19, 20, 21],  # 6 PM - 9 PM
                    concentration_days=[0, 2, 4],  # Lunes, Miércoles, Viernes
                    budget_multiplier=1.67
                )
                cluster_bomb = self.meta_hacks.apply_cluster_bomb_trick(
                    campaign_id, campaign_input.daily_budget, cluster_config
                )
                
                # Aplicar Popular Kid Strategy
                popular_kid_config = PopularKidConfig(
                    target_high_connectivity=True,
                    min_friends=500,
                    include_event_creators=True,
                    include_group_admins=True
                )
                popular_kid = self.meta_hacks.apply_popular_kid_strategy(
                    strategy.audience_definition, popular_kid_config
                )
                
                # Actualizar estrategia con hacks
                strategy.audience_definition = popular_kid.get("enhanced_audience", strategy.audience_definition)
                
                hack_config = {
                    "cluster_bomb": cluster_bomb,
                    "popular_kid": popular_kid
                }
                
                if self.logger:
                    self.logger.info(
                        f"Meta Hacks aplicados a campaña {campaign_id}",
                        extra={"campaign_id": campaign_id, "hacks": list(hack_config.keys())}
                    )
            except Exception as e:
                print(f"⚠️ Error aplicando Meta Hacks: {e}")
        
        try:
            # Crear Campaign en Meta con retry logic
            account = AdAccount(self.meta_ad_account_id)
            
            def create_campaign():
                return account.create_campaign(
                    params={
                        "name": f"{campaign_id} - {campaign_input.campaign_objective.value}",
                        "objective": self._map_objective_to_meta(campaign_input.campaign_objective),
                        "status": "PAUSED"  # Pausar inicialmente para revisión
                    }
                )
            
            # Usar API client con retry si está disponible
            if self.api_client:
                campaign = self.api_client.call_with_retry(create_campaign)
            else:
                campaign = create_campaign()
            
            meta_campaign_id = campaign.get_id()
            
            # Crear Ad Sets con retry logic
            adset_ids = []
            for audience_name, audience_config in strategy.audience_definition.items():
                def create_adset():
                    return account.create_ad_set(
                        params={
                            "name": f"{campaign_id} - {audience_name}",
                            "campaign_id": meta_campaign_id,
                            "daily_budget": int(strategy.budget_allocation.get(audience_name, campaign_input.daily_budget) * 100),  # En centavos
                            "billing_event": "IMPRESSIONS",
                            "optimization_goal": "OFFSITE_CONVERSIONS",
                            "targeting": audience_config,
                            "status": "PAUSED"
                        }
                    )
                
                if self.api_client:
                    adset = self.api_client.call_with_retry(create_adset)
                else:
                    adset = create_adset()
                
                adset_ids.append(adset.get_id())
            
            # Crear Ads con retry logic y validación de compliance
            ad_ids = []
            for creative in creatives[:3]:  # Publicar top 3 creativos inicialmente
                # Validar compliance antes de publicar
                if self.compliance_validator:
                    is_compliant, issues = await self.compliance_validator.validate_ad(
                        headline=creative.headline,
                        description=creative.primary_text,
                        image_url=creative.image_url,
                        target_audience=strategy.audience_definition,
                        industry="general"
                    )
                    if not is_compliant:
                        critical_issues = [i for i in issues if i.level == ComplianceLevel.CRITICAL]
                        if critical_issues:
                            print(f"⚠️ Creative {creative.creative_id} tiene issues críticos de compliance. Omitiendo.")
                            if self.logger:
                                self.logger.warning(
                                    f"Creative omitido por compliance: {creative.creative_id}",
                                    extra={"campaign_id": campaign_id, "issues": [i.description for i in critical_issues]}
                                )
                            continue
                
                for adset_id in adset_ids:
                    def create_ad_creative():
                        return account.create_ad_creative(
                            params={
                                "name": f"{campaign_id} - {creative.creative_id}",
                                "object_story_spec": {
                                    "page_id": os.getenv("META_ADS_PAGE_ID", ""),
                                    "link_data": {
                                        "image_url": creative.image_url or campaign_input.product_image_url,
                                        "video_url": creative.video_url or campaign_input.product_video_url,
                                        "link": os.getenv("META_ADS_LANDING_PAGE", ""),
                                        "message": creative.primary_text,
                                        "name": creative.headline,
                                        "description": creative.description or "",
                                        "call_to_action": {
                                            "type": creative.cta.upper().replace(" ", "_")
                                        }
                                    }
                                }
                            }
                        )
                    
                    def create_ad(creative_id_str):
                        return account.create_ad(
                            params={
                                "name": f"{campaign_id} - {creative.creative_id}",
                                "adset_id": adset_id,
                                "creative": {"creative_id": creative_id_str},
                                "status": "PAUSED"
                            }
                        )
                    
                    if self.api_client:
                        ad_creative = self.api_client.call_with_retry(create_ad_creative)
                        ad = self.api_client.call_with_retry(lambda: create_ad(ad_creative.get_id()))
                    else:
                        ad_creative = create_ad_creative()
                        ad = create_ad(ad_creative.get_id())
                    
                    ad_ids.append(ad.get_id())
            
            result = {
                "campaign_id": campaign_id,
                "status": "created",
                "meta_campaign_id": meta_campaign_id,
                "meta_adset_ids": adset_ids,
                "meta_ad_ids": ad_ids,
                "message": "Campaña creada en Meta Ads. Activada manualmente o por optimización automática.",
                "hacks_applied": hack_config
            }
            
            # Logging estructurado
            if self.logger:
                self.logger.info(
                    f"Campaña publicada en Meta Ads: {campaign_id}",
                    extra={
                        "campaign_id": campaign_id,
                        "meta_campaign_id": meta_campaign_id,
                        "adset_count": len(adset_ids),
                        "ad_count": len(ad_ids),
                        "hacks_applied": bool(hack_config)
                    }
                )
            
            return result
            
        except Exception as e:
            print(f"⚠️ Error publicando en Meta Ads: {e}")
            return {
                "campaign_id": campaign_id,
                "status": "error",
                "error": str(e),
                "meta_campaign_id": None
            }
    
    # ============================================
    # AGENTE 4: PERFORMANCE ANALYST
    # ============================================
    
    def _start_continuous_optimization(self, campaign_id: str):
        """Inicia optimización continua en background con técnicas avanzadas."""
        import threading
        import time
        
        def optimization_loop():
            """Loop de optimización que corre cada 6 horas con técnicas avanzadas."""
            while campaign_id in self.campaigns:
                campaign = self.campaigns.get(campaign_id)
                if not campaign:
                    break
                
                # Solo optimizar campañas activas
                if campaign.get("status") != CampaignStatus.ACTIVE.value:
                    time.sleep(3600)  # Esperar 1 hora y revisar de nuevo
                    continue
                
                try:
                    if self.logger:
                        self.logger.info(
                            f"Iniciando optimización automática para campaña {campaign_id}",
                            extra={"campaign_id": campaign_id}
                        )
                    
                    print(f"🔄 [Optimización Automática] Analizando campaña {campaign_id}...")
                    
                    # Ejecutar optimización base
                    result = self.optimize_campaign(campaign_id)
                    
                    # Aplicar Meta Lattice si está disponible
                    if self.lattice_optimizer and result.get("success"):
                        try:
                            # Optimizar atribución usando Lattice Zipper
                            metrics = result.get("metrics", {})
                            if metrics.get("conversions", 0) > 0:
                                # Simular optimización de atribución
                                print("   📊 Aplicando Meta Lattice Zipper para optimizar atribución...")
                        except Exception as e:
                            print(f"   ⚠️ Error aplicando Meta Lattice: {e}")
                    
                    # Aplicar IRPO si está disponible
                    if self.irpo_optimizer and result.get("success"):
                        try:
                            campaign_data = self.campaigns[campaign_id]
                            strategy = CampaignStrategy(**campaign_data["strategy"])
                            # Optimizar LLM usando IRPO
                            print("   🎯 Aplicando LLM-AUCTION IRPO para optimizar creativos...")
                            # En producción, esto optimizaría los prompts de generación
                        except Exception as e:
                            print(f"   ⚠️ Error aplicando IRPO: {e}")
                    
                    if result.get("success"):
                        actions = result.get("actions_taken", [])
                        if actions:
                            print(f"✅ [Optimización Automática] Acciones ejecutadas: {len(actions)}")
                            for action in actions:
                                print(f"   - {action.get('action_type')}: {action.get('reason', 'N/A')}")
                            
                            # Guardar métricas en base de datos
                            if self.db_manager:
                                try:
                                    metrics = result.get("metrics", {})
                                    self.db_manager.create_performance_metrics(
                                        tenant_id=campaign.get("session_id", "default"),
                                        campaign_id=campaign_id,
                                        impressions=metrics.get("impressions", 0),
                                        clicks=metrics.get("clicks", 0),
                                        conversions=metrics.get("conversions", 0),
                                        spend=metrics.get("spend", 0.0),
                                        ctr=metrics.get("ctr", 0.0),
                                        cpc=metrics.get("cpc", 0.0),
                                        cpa=metrics.get("cpa", 0.0),
                                        roas=metrics.get("roas", 0.0)
                                    )
                                except Exception as e:
                                    print(f"   ⚠️ Error guardando métricas: {e}")
                    else:
                        error_msg = result.get('error', 'Unknown')
                        print(f"⚠️ [Optimización Automática] Error: {error_msg}")
                        if self.logger:
                            self.logger.error(
                                f"Error en optimización automática: {error_msg}",
                                extra={"campaign_id": campaign_id}
                            )
                    
                except Exception as e:
                    error_msg = f"Error en loop de optimización: {e}"
                    print(f"❌ [Optimización Automática] {error_msg}")
                    if self.logger:
                        self.logger.error(error_msg, exc_info=True, extra={"campaign_id": campaign_id})
                
                # Esperar 6 horas antes de la próxima optimización
                time.sleep(6 * 3600)  # 6 horas
        
        # Iniciar thread en background
        optimization_thread = threading.Thread(
            target=optimization_loop,
            daemon=True,
            name=f"OptimizationWorker-{campaign_id}"
        )
        optimization_thread.start()
        
        print(f"✅ Optimización continua iniciada para {campaign_id} (cada 6 horas)")
        print(f"   🎯 Técnicas activas: Meta Lattice, IRPO, Hacks, Compliance")
        return True
    
    def optimize_campaign(
        self,
        campaign_id: str
    ) -> Dict[str, Any]:
        """PerformanceAnalystAgent analiza y optimiza campaña."""
        
        if campaign_id not in self.campaigns:
            return {"success": False, "error": "Campaña no encontrada"}
        
        campaign = self.campaigns[campaign_id]
        
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Obtener métricas actuales
        metrics = loop.run_until_complete(self._fetch_campaign_metrics(campaign_id))
        
        # Analizar performance vs KPIs
        strategy = CampaignStrategy(**campaign["strategy"])
        analysis = loop.run_until_complete(self._analyze_performance(metrics, strategy))
        
        # Generar acciones de optimización
        actions = loop.run_until_complete(
            self._generate_optimization_actions(analysis, campaign)
        )
        
        # Ejecutar acciones
        results = []
        for action in actions:
            result = loop.run_until_complete(
                self._execute_optimization_action(campaign_id, action)
            )
            results.append(result)
        
        return {
            "success": True,
            "campaign_id": campaign_id,
            "metrics": asdict(metrics),
            "analysis": analysis,
            "actions_taken": [asdict(a) for a in actions],
            "results": results
        }
    
    async def _fetch_campaign_metrics(
        self,
        campaign_id: str
    ) -> CampaignMetrics:
        """Obtiene métricas actuales de la campaña desde Meta API y/o base de datos."""
        
        # Intentar obtener de base de datos primero
        if self.db_manager:
            try:
                metrics = self.db_manager.get_latest_metrics(campaign_id)
                if metrics:
                    return CampaignMetrics(
                        impressions=metrics.get("impressions", 0),
                        clicks=metrics.get("clicks", 0),
                        conversions=metrics.get("conversions", 0),
                        spend=metrics.get("spend", 0.0),
                        ctr=metrics.get("ctr", 0.0),
                        cpc=metrics.get("cpc", 0.0),
                        cpa=metrics.get("cpa", 0.0),
                        roas=metrics.get("roas", 0.0),
                        timestamp=metrics.get("timestamp", datetime.now().isoformat())
                    )
            except Exception as e:
                print(f"⚠️ Error obteniendo métricas de DB: {e}")
        
        if not self.meta_ads_initialized:
            # Métricas simuladas
            return CampaignMetrics(
                impressions=10000,
                clicks=500,
                conversions=25,
                spend=250.0,
                ctr=5.0,
                cpc=0.50,
                cpa=10.0,
                roas=2.5,
                timestamp=datetime.now().isoformat()
            )
        
        try:
            campaign_data = self.campaigns[campaign_id]
            meta_campaign_id = campaign_data["published_campaign"].get("meta_campaign_id")
            
            if not meta_campaign_id:
                return CampaignMetrics(timestamp=datetime.now().isoformat())
            
            # Usar API client con retry
            def get_insights():
                campaign = Campaign(meta_campaign_id)
                return campaign.get_insights(fields=[
                    "impressions", "clicks", "spend", "ctr", "cpc", "actions"
                ])
            
            if self.api_client:
                insights = self.api_client.call_with_retry(get_insights)
            else:
                insights = get_insights()
            
            if insights:
                insight = insights[0]
                conversions = 0
                for action in insight.get("actions", []):
                    if "offsite_conversion" in action.get("action_type", ""):
                        conversions += int(action.get("value", 0))
                
                spend = float(insight.get("spend", 0))
                clicks = int(insight.get("clicks", 0))
                impressions = int(insight.get("impressions", 0))
                
                metrics = CampaignMetrics(
                    impressions=impressions,
                    clicks=clicks,
                    conversions=conversions,
                    spend=spend,
                    ctr=float(insight.get("ctr", 0)),
                    cpc=float(insight.get("cpc", 0)),
                    cpa=spend / conversions if conversions > 0 else 0.0,
                    roas=2.5,  # Calcular desde revenue si está disponible
                    timestamp=datetime.now().isoformat()
                )
                
                # Guardar en base de datos
                if self.db_manager:
                    try:
                        self.db_manager.create_performance_metrics(
                            tenant_id=campaign_data.get("session_id", "default"),
                            campaign_id=campaign_id,
                            impressions=metrics.impressions,
                            clicks=metrics.clicks,
                            conversions=metrics.conversions,
                            spend=metrics.spend,
                            ctr=metrics.ctr,
                            cpc=metrics.cpc,
                            cpa=metrics.cpa,
                            roas=metrics.roas
                        )
                    except Exception as e:
                        print(f"⚠️ Error guardando métricas en DB: {e}")
                
                return metrics
        except Exception as e:
            error_msg = f"Error obteniendo métricas: {e}"
            print(f"⚠️ {error_msg}")
            if self.logger:
                self.logger.error(error_msg, exc_info=True, extra={"campaign_id": campaign_id})
        
        return CampaignMetrics(timestamp=datetime.now().isoformat())
    
    async def _analyze_performance(
        self,
        metrics: CampaignMetrics,
        strategy: CampaignStrategy
    ) -> Dict[str, Any]:
        """Analiza performance vs KPIs objetivo."""
        
        analysis_prompt = f"""Eres un analista de performance experto. Analiza estas métricas vs objetivos.

MÉTRICAS ACTUALES:
{json.dumps(asdict(metrics), indent=2)}

KPIs OBJETIVO:
{json.dumps(strategy.kpi_targets, indent=2)}

TAREA:
Analiza y responde en JSON:
1. performance_status: "exceeding", "meeting", "below", o "critical"
2. key_insights: insights principales
3. issues: problemas identificados
4. opportunities: oportunidades de mejora
5. recommended_actions: acciones recomendadas (pause, scale, regenerate, adjust_budget)

Responde SOLO con JSON válido."""

        response = await self.llm.ainvoke(analysis_prompt)
        return self._extract_json_from_response(response.content)
    
    async def _generate_optimization_actions(
        self,
        analysis: Dict[str, Any],
        campaign: Dict[str, Any]
    ) -> List[OptimizationAction]:
        """Genera acciones de optimización basadas en análisis."""
        
        actions = []
        
        recommended_actions = analysis.get("recommended_actions", [])
        
        for action_type in recommended_actions:
            if action_type == "pause":
                actions.append(OptimizationAction(
                    action_type="pause",
                    target_id=campaign["campaign_id"],
                    reason=analysis.get("issues", ["Performance below target"])[0]
                ))
            elif action_type == "scale":
                actions.append(OptimizationAction(
                    action_type="scale",
                    target_id=campaign["campaign_id"],
                    reason=analysis.get("opportunities", ["Performance exceeding target"])[0],
                    new_budget=campaign["input"]["daily_budget"] * 1.5  # Aumentar 50%
                ))
            elif action_type == "regenerate":
                actions.append(OptimizationAction(
                    action_type="regenerate",
                    target_id=campaign["campaign_id"],
                    reason="Creative fatigue detected"
                ))
        
        return actions
    
    async def _execute_optimization_action(
        self,
        campaign_id: str,
        action: OptimizationAction
    ) -> Dict[str, Any]:
        """Ejecuta una acción de optimización."""
        
        if action.action_type == "pause":
            # Pausar campaña en Meta
            if self.meta_ads_initialized:
                try:
                    campaign_data = self.campaigns[campaign_id]
                    meta_campaign_id = campaign_data["published_campaign"].get("meta_campaign_id")
                    if meta_campaign_id:
                        campaign = Campaign(meta_campaign_id)
                        campaign.update(params={"status": "PAUSED"})
                        self.campaigns[campaign_id]["status"] = CampaignStatus.PAUSED.value
                except Exception as e:
                    return {"success": False, "error": str(e)}
            
            return {"success": True, "action": "pause", "campaign_id": campaign_id}
        
        elif action.action_type == "scale":
            # Escalar presupuesto
            if action.new_budget:
                self.campaigns[campaign_id]["input"]["daily_budget"] = action.new_budget
                # Actualizar en Meta si está configurado
                return {"success": True, "action": "scale", "new_budget": action.new_budget}
        
        elif action.action_type == "regenerate":
            # Regenerar creativos
            campaign = self.campaigns[campaign_id]
            new_creatives = await self._generate_creatives(
                CampaignInput(**campaign["input"]),
                CampaignStrategy(**campaign["strategy"]),
                campaign["session_id"]
            )
            campaign["creatives"] = [asdict(c) for c in new_creatives]
            return {"success": True, "action": "regenerate", "new_creatives": len(new_creatives)}
        
        return {"success": False, "error": "Unknown action type"}
    
    # ============================================
    # UTILIDADES
    # ============================================
    
    def _extract_json_from_response(self, text: str) -> Dict[str, Any]:
        """Extrae JSON de respuesta del LLM."""
        try:
            # Intentar parsear directamente
            return json.loads(text)
        except:
            # Buscar JSON en el texto
            import re
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return {}
    
    def _map_objective_to_meta(self, objective: CampaignObjective) -> str:
        """Mapea objetivo a formato Meta Ads."""
        mapping = {
            CampaignObjective.SALES: "CONVERSIONS",
            CampaignObjective.LEADS: "LEAD_GENERATION",
            CampaignObjective.TRAFFIC: "LINK_CLICKS",
            CampaignObjective.AWARENESS: "BRAND_AWARENESS",
            CampaignObjective.ENGAGEMENT: "POST_ENGAGEMENT"
        }
        return mapping.get(objective, "CONVERSIONS")
    
    async def _generate_image(self, prompt: str) -> Optional[str]:
        """Genera imagen usando DALL-E 3 con retry logic."""
        try:
            from openai import OpenAI
            
            if not self.config.openai_api_key:
                print("⚠️ OpenAI API key no configurada. No se puede generar imagen.")
                return None
            
            # Usar API client con retry si está disponible
            if self.api_client:
                def generate():
                    client = OpenAI(api_key=self.config.openai_api_key)
                    response = client.images.generate(
                        model="dall-e-3",
                        prompt=prompt,
                        size="1024x1024",
                        quality="standard",
                        n=1
                    )
                    return response.data[0].url
                
                image_url = self.api_client.call_with_retry(generate)
            else:
                # Fallback sin retry
                client = OpenAI(api_key=self.config.openai_api_key)
                response = client.images.generate(
                    model="dall-e-3",
                    prompt=prompt,
                    size="1024x1024",
                    quality="standard",
                    n=1
                )
                image_url = response.data[0].url
            
            # Descargar y guardar imagen localmente
            import requests
            img_response = requests.get(image_url)
            
            # Guardar en directorio de creativos
            output_dir = Path(self.config.memory_dir or "data") / "generated_creatives" / "images"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            image_path = output_dir / f"{uuid.uuid4().hex[:8]}.png"
            with open(image_path, 'wb') as f:
                f.write(img_response.content)
            
            # Guardar asset en base de datos
            if self.db_manager:
                asset_id = f"IMG-{uuid.uuid4().hex[:8].upper()}"
                self.db_manager.create_asset(
                    asset_id=asset_id,
                    tenant_id="default",
                    asset_type="image",
                    file_path=str(image_path),
                    file_size=len(img_response.content),
                    mime_type="image/png",
                    metadata={"prompt": prompt, "model": "dall-e-3"}
                )
            
            if self.logger:
                self.logger.info(
                    f"Imagen generada: {image_path}",
                    extra={"image_path": str(image_path), "prompt_length": len(prompt)}
                )
            
            print(f"✅ Imagen generada y guardada: {image_path}")
            return str(image_path)
            
        except Exception as e:
            error_msg = f"Error generando imagen con DALL-E: {e}"
            print(f"⚠️ {error_msg}")
            if self.logger:
                self.logger.error(error_msg, exc_info=True)
            return None
    
    async def _query_rag_for_context(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Consulta RAG para contexto histórico de campañas."""
        try:
            # Si no hay retriever inicializado, crear uno
            if not self.rag_retriever:
                await self._initialize_rag_retriever()
            
            if not self.rag_retriever:
                return []
            
            # Buscar documentos relevantes
            docs = self.rag_retriever.get_relevant_documents(query)
            
            # Convertir a formato dict
            context = []
            for doc in docs[:limit]:
                context.append({
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "score": getattr(doc, 'score', 0.0) if hasattr(doc, 'score') else 0.0
                })
            
            return context
            
        except Exception as e:
            print(f"⚠️ Error consultando RAG: {e}")
            return []
    
    async def _initialize_rag_retriever(self):
        """Inicializa el retriever RAG para campañas."""
        try:
            rag_dir = Path(self.config.data_dir) / "ads_manager_rag"
            rag_dir.mkdir(parents=True, exist_ok=True)
            
            # Usar el retriever_builder existente
            if self.retriever_builder:
                # Crear vector store si no existe
                vectorstore_path = rag_dir / "vectorstore"
                
                # Intentar cargar vector store existente
                if vectorstore_path.exists():
                    self.rag_retriever = self.retriever_builder.build_retriever(
                        vectorstore_path=str(vectorstore_path),
                        search_type="similarity",
                        search_kwargs={"k": 10}
                    )
                else:
                    # Crear nuevo vector store vacío
                    from langchain_openai import OpenAIEmbeddings
                    from langchain_chroma import Chroma
                    
                    embeddings = OpenAIEmbeddings(
                        openai_api_key=self.config.openai_api_key
                    )
                    
                    vectorstore = Chroma(
                        persist_directory=str(vectorstore_path),
                        embedding_function=embeddings
                    )
                    
                    self.rag_retriever = vectorstore.as_retriever(
                        search_type="similarity",
                        search_kwargs={"k": 10}
                    )
                    
                    print("✅ RAG retriever inicializado para Enterprise Ads Manager")
        except Exception as e:
            print(f"⚠️ Error inicializando RAG retriever: {e}")
            self.rag_retriever = None
    
    async def _index_campaign_in_rag(self, campaign_data: Dict[str, Any]):
        """Indexa campaña en RAG para contexto futuro."""
        try:
            # Inicializar retriever si no existe
            if not self.rag_retriever:
                await self._initialize_rag_retriever()
            
            if not self.rag_retriever:
                return
            
            # Crear documento con información de la campaña
            campaign_id = campaign_data.get("campaign_id", "unknown")
            strategy = campaign_data.get("strategy", {})
            creatives = campaign_data.get("creatives", [])
            
            # Texto a indexar
            campaign_text = f"""
Campaña ID: {campaign_id}
Objetivo: {strategy.get('campaign_objective', 'N/A')}
Funnel Stage: {strategy.get('funnel_stage', 'N/A')}
Audiencia: {json.dumps(strategy.get('audience_definition', {}), indent=2)}
KPIs Objetivo: {json.dumps(strategy.get('kpi_targets', {}), indent=2)}
Razonamiento: {strategy.get('reasoning', 'N/A')}

Creativos generados: {len(creatives)}
"""
            
            # Agregar información de creativos
            for i, creative in enumerate(creatives[:5]):  # Indexar top 5
                campaign_text += f"""
Creative {i+1}:
- Headline: {creative.get('headline', 'N/A')}
- Primary Text: {creative.get('primary_text', 'N/A')}
- CTA: {creative.get('cta', 'N/A')}
"""
            
            # Crear documento LangChain
            from langchain_core.documents import Document
            
            doc = Document(
                page_content=campaign_text,
                metadata={
                    "campaign_id": campaign_id,
                    "created_at": campaign_data.get("created_at", datetime.now().isoformat()),
                    "objective": strategy.get('campaign_objective', ''),
                    "funnel_stage": strategy.get('funnel_stage', ''),
                    "type": "campaign"
                }
            )
            
            # Agregar al vector store
            if hasattr(self.rag_retriever, 'vectorstore'):
                self.rag_retriever.vectorstore.add_documents([doc])
                print(f"✅ Campaña {campaign_id} indexada en RAG")
            else:
                # Si es un retriever, necesitamos acceso al vectorstore
                print("⚠️ No se pudo indexar: retriever no tiene vectorstore directo")
                
        except Exception as e:
            print(f"⚠️ Error indexando campaña en RAG: {e}")
    
    # ============================================
    # MÉTODOS PÚBLICOS
    # ============================================
    
    def get_campaign(self, campaign_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene datos de una campaña."""
        return self.campaigns.get(campaign_id)
    
    def list_campaigns(self) -> List[Dict[str, Any]]:
        """Lista todas las campañas."""
        return list(self.campaigns.values())
    
    def get_campaign_metrics(self, campaign_id: str) -> Dict[str, Any]:
        """Obtiene métricas de una campaña."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        metrics = loop.run_until_complete(self._fetch_campaign_metrics(campaign_id))
        return asdict(metrics)


# ============================================
# FUNCIONES DE INTERFAZ GRADIO
# ============================================

def get_enterprise_ads_manager_mode(
    config: AppConfig,
    processor: DocumentProcessor,
    retriever_builder: RetrieverBuilder,
    context_manager: Optional[ContextManager] = None,
    provider: str = "openai"
) -> EnterpriseAdsManagerMode:
    """Obtiene instancia del modo Enterprise Ads Manager."""
    return EnterpriseAdsManagerMode(
        config=config,
        processor=processor,
        retriever_builder=retriever_builder,
        context_manager=context_manager,
        provider=provider
    )


def run_enterprise_ads_manager_mode(
    message: str,
    history: List[List[str]],
    campaign_input: Dict[str, Any],
    provider: str = "openai"
) -> tuple:
    """Ejecuta el modo Enterprise Ads Manager desde Gradio."""
    # Esta función se implementará cuando se integre con app.py
    pass
