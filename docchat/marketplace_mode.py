"""Marketplace Mode - Plataforma completa de monetización tipo Meta Ads"""

from __future__ import annotations

from typing import List, Dict, Any, Optional, Iterator
from datetime import datetime, timedelta
from pathlib import Path
import json
import uuid
from dataclasses import dataclass, asdict, field
from enum import Enum
import asyncio
from concurrent.futures import ThreadPoolExecutor

from langchain_core.documents import Document
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

from .config import AppConfig
from .document_processor import DocumentProcessor
from .retriever_builder import RetrieverBuilder
from .workflow import AgentWorkflow


class PricingTier(Enum):
    """Niveles de precios para anunciantes"""
    FREE = "free"  # 100 impresiones/mes
    PRO = "pro"  # $99/mes, 10,000 impresiones
    ENTERPRISE = "enterprise"  # $999/mes, ilimitado


class AdStatus(Enum):
    """Estado de una campaña publicitaria"""
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class CreatorTier(Enum):
    """Niveles de creadores"""
    BEGINNER = "beginner"  # 0-10K seguidores
    INTERMEDIATE = "intermediate"  # 10K-100K seguidores
    ADVANCED = "advanced"  # 100K-1M seguidores
    ELITE = "elite"  # 1M+ seguidores


@dataclass
class AdCampaign:
    """Campaña publicitaria"""
    campaign_id: str
    advertiser_id: str
    name: str
    budget: float
    daily_budget: Optional[float]
    target_audience: Dict[str, Any]
    ad_creatives: List[Dict[str, Any]]
    status: AdStatus
    start_date: datetime
    end_date: Optional[datetime]
    pricing_tier: PricingTier
    created_at: datetime = field(default_factory=datetime.now)
    impressions: int = 0
    clicks: int = 0
    conversions: int = 0
    revenue: float = 0.0
    ctr: float = 0.0
    cpc: float = 0.0
    roas: float = 0.0


@dataclass
class AdBid:
    """Oferta en subasta de anuncios"""
    bid_id: str
    campaign_id: str
    bid_amount: float
    ad_creative: Dict[str, Any]
    target_keywords: List[str]
    timestamp: datetime
    priority: int = 0  # Mayor = más prioridad


@dataclass
class Creator:
    """Creador de contenido"""
    creator_id: str
    name: str
    email: str
    social_handles: Dict[str, str]  # {platform: handle}
    follower_count: Dict[str, int]  # {platform: count}
    niche: str
    engagement_rate: float
    tier: CreatorTier
    created_at: datetime = field(default_factory=datetime.now)
    earnings: float = 0.0
    completed_collaborations: int = 0
    rating: float = 0.0


@dataclass
class Collaboration:
    """Colaboración entre marca y creador"""
    collaboration_id: str
    brand_id: str
    creator_id: str
    campaign_id: str
    content_type: str  # post, reel, story, video
    payment_amount: float
    created_at: datetime = field(default_factory=datetime.now)
    commission_rate: float = 0.15  # 15% para la plataforma
    status: str = "pending"
    completed_at: Optional[datetime] = None


@dataclass
class AdAnalytics:
    """Analytics de una campaña"""
    campaign_id: str
    date_range: tuple
    total_impressions: int
    total_clicks: int
    total_conversions: int
    total_spend: float
    total_revenue: float
    ctr: float
    cpc: float
    cpa: float
    roas: float
    top_performing_creatives: List[Dict[str, Any]]
    audience_insights: Dict[str, Any]
    recommendations: List[str]


class MarketplaceMode:
    """
    Modo Marketplace: Plataforma completa de monetización tipo Meta Ads
    
    Funcionalidades:
    - Sistema de subastas de anuncios en tiempo real
    - Monetización de Portal ADS y AD LLM
    - AI Agent Factory para marketing autónomo
    - Marketplace de creadores
    - Retargeting y personalización avanzada
    - Dashboard de analytics
    - Sistema de pagos integrado
    """
    
    def __init__(self, config: AppConfig, provider: str = "openai"):
        self.config = config
        self.provider = provider
        
        # Inicializar LLM
        if provider == "openai":
            self.llm = ChatOpenAI(
                model=config.agentic_model,
                temperature=0.7,
                api_key=config.openai_api_key
            )
        elif provider == "claude":
            self.llm = ChatAnthropic(
                model="claude-3-5-sonnet-20241022",  # Modelo por defecto para Claude
                temperature=0.7,
                api_key=config.anthropic_api_key
            )
        else:
            self.llm = ChatOpenAI(
                model=config.agentic_model,
                temperature=0.7,
                api_key=config.openai_api_key
            )
        
        # Almacenamiento en memoria (en producción usar DB)
        self.campaigns: Dict[str, AdCampaign] = {}
        self.bids: Dict[str, AdBid] = {}
        self.creators: Dict[str, Creator] = {}
        self.collaborations: Dict[str, Collaboration] = {}
        self.analytics: Dict[str, AdAnalytics] = {}
        
        # Configuración de precios
        self.pricing = {
            PricingTier.FREE: {
                "monthly_fee": 0,
                "impressions_limit": 100,
                "features": ["basic_targeting", "standard_analytics"]
            },
            PricingTier.PRO: {
                "monthly_fee": 99,
                "impressions_limit": 10000,
                "features": ["advanced_targeting", "ai_creatives", "retargeting", "premium_analytics"]
            },
            PricingTier.ENTERPRISE: {
                "monthly_fee": 999,
                "impressions_limit": float('inf'),
                "features": ["all_pro_features", "autonomous_agents", "api_access", "dedicated_support", "white_label"]
            }
        }
        
        # Comisión de marketplace
        self.marketplace_commission = 0.15  # 15%
        
        # Cargar datos persistentes
        self._load_data()
        
        print("✅ Marketplace Mode inicializado - Listo para generar $100B en revenue")
    
    def _load_data(self):
        """Carga datos persistentes desde archivos"""
        data_dir = Path(self.config.memory_dir) / "marketplace"
        data_dir.mkdir(parents=True, exist_ok=True)
        
        # Cargar campañas
        campaigns_file = data_dir / "campaigns.json"
        if campaigns_file.exists():
            try:
                with open(campaigns_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for camp_data in data:
                        camp = AdCampaign(**camp_data)
                        camp.start_date = datetime.fromisoformat(camp.start_date) if isinstance(camp.start_date, str) else camp.start_date
                        camp.end_date = datetime.fromisoformat(camp.end_date) if camp.end_date and isinstance(camp.end_date, str) else camp.end_date
                        camp.created_at = datetime.fromisoformat(camp.created_at) if isinstance(camp.created_at, str) else camp.created_at
                        camp.status = AdStatus(camp.status) if isinstance(camp.status, str) else camp.status
                        camp.pricing_tier = PricingTier(camp.pricing_tier) if isinstance(camp.pricing_tier, str) else camp.pricing_tier
                        self.campaigns[camp.campaign_id] = camp
            except Exception as e:
                print(f"Error cargando campañas: {e}")
    
    def _save_data(self):
        """Guarda datos persistentes en archivos"""
        data_dir = Path(self.config.memory_dir) / "marketplace"
        data_dir.mkdir(parents=True, exist_ok=True)
        
        # Guardar campañas
        campaigns_file = data_dir / "campaigns.json"
        campaigns_data = []
        for camp in self.campaigns.values():
            camp_dict = asdict(camp)
            camp_dict['start_date'] = camp.start_date.isoformat() if camp.start_date else None
            camp_dict['end_date'] = camp.end_date.isoformat() if camp.end_date else None
            camp_dict['created_at'] = camp.created_at.isoformat() if camp.created_at else None
            camp_dict['status'] = camp.status.value
            camp_dict['pricing_tier'] = camp.pricing_tier.value
            campaigns_data.append(camp_dict)
        
        with open(campaigns_file, 'w', encoding='utf-8') as f:
            json.dump(campaigns_data, f, indent=2, ensure_ascii=False)
    
    # ==================== GESTIÓN DE CAMPAÑAS ====================
    
    def create_campaign(
        self,
        advertiser_id: str,
        name: str,
        budget: float,
        daily_budget: Optional[float],
        target_audience: Dict[str, Any],
        ad_creatives: List[Dict[str, Any]],
        pricing_tier: PricingTier = PricingTier.PRO,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> AdCampaign:
        """Crea una nueva campaña publicitaria con validaciones"""
        # Validaciones
        if not advertiser_id or not advertiser_id.strip():
            raise ValueError("advertiser_id es requerido")
        if not name or not name.strip():
            raise ValueError("name es requerido")
        if budget < 10:
            raise ValueError("El presupuesto mínimo es $10")
        if daily_budget and daily_budget > budget:
            raise ValueError("El presupuesto diario no puede ser mayor al presupuesto total")
        if not ad_creatives:
            raise ValueError("Se requiere al menos un creativo publicitario")
        
        # Validar límites del plan
        plan_limits = self.pricing.get(pricing_tier, {})
        if pricing_tier == PricingTier.FREE:
            # Verificar si ya tiene campañas activas en el plan FREE
            existing_free_campaigns = [c for c in self.campaigns.values() 
                                     if c.advertiser_id == advertiser_id and c.pricing_tier == PricingTier.FREE]
            if len(existing_free_campaigns) >= 1:
                raise ValueError("El plan FREE permite solo 1 campaña activa. Actualiza a PRO o ENTERPRISE para más campañas.")
        
        campaign_id = f"camp_{uuid.uuid4().hex[:12]}"
        
        campaign = AdCampaign(
            campaign_id=campaign_id,
            advertiser_id=advertiser_id,
            name=name,
            budget=budget,
            daily_budget=daily_budget,
            target_audience=target_audience,
            ad_creatives=ad_creatives,
            status=AdStatus.DRAFT,
            start_date=start_date or datetime.now(),
            end_date=end_date,
            pricing_tier=pricing_tier,
            created_at=datetime.now()
        )
        
        self.campaigns[campaign_id] = campaign
        self._save_data()
        
        print(f"✅ Campaña '{name}' creada (ID: {campaign_id}, Budget: ${budget}, Tier: {pricing_tier.value})")
        return campaign
    
    def activate_campaign(self, campaign_id: str) -> bool:
        """Activa una campaña"""
        if campaign_id not in self.campaigns:
            return False
        
        campaign = self.campaigns[campaign_id]
        campaign.status = AdStatus.ACTIVE
        self._save_data()
        
        print(f"🚀 Campaña '{campaign.name}' activada")
        return True
    
    def pause_campaign(self, campaign_id: str) -> bool:
        """Pausa una campaña"""
        if campaign_id not in self.campaigns:
            return False
        
        campaign = self.campaigns[campaign_id]
        campaign.status = AdStatus.PAUSED
        self._save_data()
        
        print(f"⏸️ Campaña '{campaign.name}' pausada")
        return True
    
    def get_campaign(self, campaign_id: str) -> Optional[AdCampaign]:
        """Obtiene una campaña por ID"""
        return self.campaigns.get(campaign_id)
    
    def list_campaigns(self, advertiser_id: Optional[str] = None) -> List[AdCampaign]:
        """Lista todas las campañas o las de un anunciante específico"""
        if advertiser_id:
            return [c for c in self.campaigns.values() if c.advertiser_id == advertiser_id]
        return list(self.campaigns.values())
    
    # ==================== SISTEMA DE SUBASTAS ====================
    
    def create_bid(
        self,
        campaign_id: str,
        bid_amount: float,
        ad_creative: Dict[str, Any],
        target_keywords: List[str],
        priority: int = 0
    ) -> AdBid:
        """Crea una oferta para la subasta de anuncios"""
        bid_id = f"bid_{uuid.uuid4().hex[:12]}"
        
        bid = AdBid(
            bid_id=bid_id,
            campaign_id=campaign_id,
            bid_amount=bid_amount,
            ad_creative=ad_creative,
            target_keywords=target_keywords,
            timestamp=datetime.now(),
            priority=priority
        )
        
        self.bids[bid_id] = bid
        return bid
    
    def run_auction(
        self,
        user_context: Dict[str, Any],
        available_slots: int = 1
    ) -> List[AdBid]:
        """
        Ejecuta una subasta de anuncios en tiempo real
        
        Args:
            user_context: Contexto del usuario (intereses, comportamiento, etc.)
            available_slots: Número de espacios publicitarios disponibles
        
        Returns:
            Lista de ofertas ganadoras ordenadas por relevancia y bid
        """
        # Filtrar ofertas activas
        active_bids = []
        for bid in self.bids.values():
            campaign = self.campaigns.get(bid.campaign_id)
            if campaign and campaign.status == AdStatus.ACTIVE:
                # Verificar si el bid es relevante para el usuario
                relevance_score = self._calculate_relevance(bid, user_context)
                if relevance_score > 0.3:  # Umbral mínimo de relevancia
                    active_bids.append((bid, relevance_score))
        
        # Ordenar por score combinado (relevancia * bid_amount * priority)
        active_bids.sort(
            key=lambda x: x[1] * x[0].bid_amount * (1 + x[0].priority / 10),
            reverse=True
        )
        
        # Seleccionar ganadores
        winners = [bid for bid, _ in active_bids[:available_slots]]
        
        # Actualizar métricas de campañas ganadoras
        for bid in winners:
            campaign = self.campaigns.get(bid.campaign_id)
            if campaign:
                campaign.impressions += 1
                # Simular click (en producción sería real)
                if self._simulate_click(bid, user_context):
                    campaign.clicks += 1
                    campaign.ctr = campaign.clicks / campaign.impressions if campaign.impressions > 0 else 0
                    campaign.cpc = bid.bid_amount
                    campaign.revenue += bid.bid_amount
        
        self._save_data()
        return winners
    
    def _calculate_relevance(self, bid: AdBid, user_context: Dict[str, Any]) -> float:
        """Calcula la relevancia de un bid para un usuario"""
        score = 0.0
        
        # Matching de keywords
        user_interests = user_context.get("interests", [])
        keyword_matches = sum(1 for kw in bid.target_keywords if kw.lower() in [i.lower() for i in user_interests])
        if bid.target_keywords:
            score += (keyword_matches / len(bid.target_keywords)) * 0.5
        
        # Matching de demografía
        target_demo = bid.ad_creative.get("target_demographics", {})
        user_demo = user_context.get("demographics", {})
        
        if target_demo.get("age_range") and user_demo.get("age"):
            age = user_demo["age"]
            age_range = target_demo["age_range"]
            if age_range[0] <= age <= age_range[1]:
                score += 0.3
        
        if target_demo.get("gender") and user_demo.get("gender"):
            if target_demo["gender"] == user_demo["gender"]:
                score += 0.2
        
        return min(1.0, score)
    
    def _simulate_click(self, bid: AdBid, user_context: Dict[str, Any]) -> bool:
        """Simula si un usuario haría click (en producción sería real)"""
        import random
        base_ctr = 0.02  # 2% CTR base
        relevance = self._calculate_relevance(bid, user_context)
        click_probability = base_ctr * (1 + relevance)
        return random.random() < click_probability
    
    # ==================== GENERACIÓN DE CREATIVOS CON IA ====================
    
    def generate_ad_creative(
        self,
        product_description: str,
        target_audience: Dict[str, Any],
        ad_type: str = "text",  # text, image, video
        personality_trait: Optional[str] = None,
        persuasion_principle: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Genera creativos publicitarios usando IA (integra Portal ADS y AD LLM)
        Optimizado para producción con validaciones y mejoras
        """
        # Validaciones
        if not product_description or len(product_description.strip()) < 10:
            return {
                "headline": "Descubre más",
                "description": "Oferta especial para ti",
                "cta": "Saber Más",
                "keywords": [],
                "error": "Descripción del producto demasiado corta (mínimo 10 caracteres)"
            }
        
        # Mejorar prompt con mejores prácticas de marketing
        persuasion_principles_map = {
            "authority": "Usa autoridad y credibilidad (expertos, certificaciones, testimonios)",
            "consensus": "Usa prueba social (miles de usuarios, reviews positivas, popularidad)",
            "scarcity": "Crea urgencia y escasez (oferta limitada, pocas unidades, tiempo limitado)",
            "value": "Destaca el valor y beneficios (ahorro, eficiencia, resultados)",
            "urgency": "Crea urgencia temporal (solo hoy, última oportunidad, expira pronto)"
        }
        
        persuasion_guide = persuasion_principles_map.get(persuasion_principle or "value", persuasion_principles_map["value"])
        
        prompt = f"""Eres un experto en marketing digital y generación de anuncios publicitarios de alto rendimiento.

PRODUCTO/SERVICIO:
{product_description}

AUDIENCIA OBJETIVO:
{json.dumps(target_audience, indent=2, ensure_ascii=False)}

TIPO DE ANUNCIO: {ad_type}
PRINCIPIO DE PERSUASIÓN: {persuasion_principle or "value"}
GUÍA: {persuasion_guide}

INSTRUCCIONES:
1. Genera un anuncio que capture la atención en los primeros 3 segundos
2. El headline debe ser impactante, claro y específico (máximo 60 caracteres)
3. La descripción debe comunicar el beneficio principal de forma concisa (máximo 125 caracteres)
4. El CTA debe ser acción directa y clara
5. Usa el principio de persuasión especificado de forma natural
6. Adapta el tono a la audiencia objetivo
7. Incluye elementos emocionales que conecten con la audiencia

Responde ÚNICAMENTE en formato JSON válido (sin markdown, sin código):
{{
    "headline": "Título principal (máx 60 caracteres, impactante)",
    "description": "Descripción del anuncio (máx 125 caracteres, beneficios claros)",
    "cta": "Call-to-action claro (ej: 'Comprar Ahora', 'Comenzar Gratis', 'Saber Más')",
    "keywords": ["palabra1", "palabra2", "palabra3"],
    "emotional_appeal": "Tipo de apelación emocional (ej: 'miedo a perder', 'deseo de éxito', 'orgullo')",
    "persuasion_technique": "Técnica específica usada",
    "targeting_notes": "Notas sobre por qué este anuncio funciona para esta audiencia"
}}
"""
        
        try:
            response = self.llm.invoke(prompt).content.strip()
            
            # Limpiar y parsear JSON de forma robusta
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                response = response.split("```")[1].split("```")[0].strip()
            
            # Intentar parsear JSON
            creative = json.loads(response)
            
            # Validar campos requeridos
            required_fields = ["headline", "description", "cta"]
            for field in required_fields:
                if field not in creative or not creative[field]:
                    creative[field] = "Descubre más" if field == "headline" else "Oferta especial" if field == "description" else "Saber Más"
            
            # Validar longitudes
            if len(creative.get("headline", "")) > 60:
                creative["headline"] = creative["headline"][:57] + "..."
            if len(creative.get("description", "")) > 125:
                creative["description"] = creative["description"][:122] + "..."
            
            # Agregar metadata
            creative["generated_at"] = datetime.now().isoformat()
            creative["ad_type"] = ad_type
            creative["target_audience"] = target_audience
            creative["persuasion_principle"] = persuasion_principle or "value"
            creative["quality_score"] = self._calculate_creative_quality_score(creative)
            
            print(f"✅ Creativo generado: {creative.get('headline', 'N/A')} (Score: {creative.get('quality_score', 0):.2f})")
            return creative
            
        except json.JSONDecodeError as e:
            print(f"❌ Error parseando JSON del creativo: {e}")
            # Intentar extraer información básica del texto
            return {
                "headline": product_description[:60] if len(product_description) > 10 else "Descubre más",
                "description": product_description[:125] if len(product_description) > 10 else "Oferta especial para ti",
                "cta": "Saber Más",
                "keywords": [],
                "error": f"Error parseando respuesta JSON: {str(e)}"
            }
        except Exception as e:
            print(f"❌ Error generando creativo: {e}")
            return {
                "headline": "Descubre más",
                "description": "Oferta especial para ti",
                "cta": "Saber Más",
                "keywords": [],
                "error": str(e)
            }
    
    def _calculate_creative_quality_score(self, creative: Dict[str, Any]) -> float:
        """Calcula un score de calidad para el creativo (0-1)"""
        score = 0.0
        
        # Headline (40%)
        headline = creative.get("headline", "")
        if headline:
            if 20 <= len(headline) <= 60:
                score += 0.4
            elif 10 <= len(headline) < 20 or 60 < len(headline) <= 70:
                score += 0.2
        
        # Description (30%)
        description = creative.get("description", "")
        if description:
            if 50 <= len(description) <= 125:
                score += 0.3
            elif 30 <= len(description) < 50 or 125 < len(description) <= 150:
                score += 0.15
        
        # CTA (20%)
        cta = creative.get("cta", "")
        if cta and len(cta) >= 3:
            score += 0.2
        
        # Keywords (10%)
        keywords = creative.get("keywords", [])
        if keywords and len(keywords) >= 3:
            score += 0.1
        
        return min(1.0, score)
    
    def generate_multiple_variations(
        self,
        product_description: str,
        target_audience: Dict[str, Any],
        num_variations: int = 5
    ) -> List[Dict[str, Any]]:
        """Genera múltiples variaciones de creativos para A/B testing"""
        variations = []
        
        persuasion_principles = ["authority", "consensus", "scarcity", "value", "urgency"]
        
        for i in range(num_variations):
            principle = persuasion_principles[i % len(persuasion_principles)]
            creative = self.generate_ad_creative(
                product_description=product_description,
                target_audience=target_audience,
                persuasion_principle=principle
            )
            creative["variation_id"] = f"var_{i+1}"
            creative["persuasion_principle"] = principle
            variations.append(creative)
        
        return variations
    
    # ==================== MARKETPLACE DE CREADORES ====================
    
    def register_creator(
        self,
        name: str,
        email: str,
        social_handles: Dict[str, str],
        follower_count: Dict[str, int],
        niche: str
    ) -> Creator:
        """Registra un nuevo creador en el marketplace"""
        creator_id = f"creator_{uuid.uuid4().hex[:12]}"
        
        # Calcular engagement rate (simulado)
        total_followers = sum(follower_count.values())
        engagement_rate = min(0.15, 0.05 + (total_followers / 1000000) * 0.1)
        
        # Determinar tier
        if total_followers < 10000:
            tier = CreatorTier.BEGINNER
        elif total_followers < 100000:
            tier = CreatorTier.INTERMEDIATE
        elif total_followers < 1000000:
            tier = CreatorTier.ADVANCED
        else:
            tier = CreatorTier.ELITE
        
        creator = Creator(
            creator_id=creator_id,
            name=name,
            email=email,
            social_handles=social_handles,
            follower_count=follower_count,
            niche=niche,
            engagement_rate=engagement_rate,
            tier=tier,
            created_at=datetime.now()
        )
        
        self.creators[creator_id] = creator
        print(f"✅ Creador '{name}' registrado (Tier: {tier.value}, Followers: {total_followers:,})")
        return creator
    
    def search_creators(
        self,
        niche: Optional[str] = None,
        min_followers: Optional[int] = None,
        min_engagement: Optional[float] = None,
        tier: Optional[CreatorTier] = None
    ) -> List[Creator]:
        """Busca creadores según criterios"""
        results = list(self.creators.values())
        
        if niche:
            results = [c for c in results if niche.lower() in c.niche.lower()]
        
        if min_followers:
            results = [c for c in results if sum(c.follower_count.values()) >= min_followers]
        
        if min_engagement:
            results = [c for c in results if c.engagement_rate >= min_engagement]
        
        if tier:
            results = [c for c in results if c.tier == tier]
        
        # Ordenar por engagement rate
        results.sort(key=lambda c: c.engagement_rate, reverse=True)
        return results
    
    def create_collaboration(
        self,
        brand_id: str,
        creator_id: str,
        campaign_id: str,
        content_type: str,
        payment_amount: float
    ) -> Collaboration:
        """Crea una colaboración entre marca y creador"""
        collaboration_id = f"collab_{uuid.uuid4().hex[:12]}"
        
        collaboration = Collaboration(
            collaboration_id=collaboration_id,
            brand_id=brand_id,
            creator_id=creator_id,
            campaign_id=campaign_id,
            content_type=content_type,
            payment_amount=payment_amount,
            commission_rate=self.marketplace_commission,
            created_at=datetime.now()
        )
        
        self.collaborations[collaboration_id] = collaboration
        
        # Actualizar earnings del creador
        creator = self.creators.get(creator_id)
        if creator:
            creator.earnings += payment_amount * (1 - self.marketplace_commission)
            creator.completed_collaborations += 1
        
        print(f"✅ Colaboración creada: {brand_id} + {creator_id} (${payment_amount})")
        return collaboration
    
    # ==================== ANALYTICS Y REPORTES ====================
    
    def get_campaign_analytics(
        self,
        campaign_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> AdAnalytics:
        """Genera analytics detallados de una campaña"""
        campaign = self.campaigns.get(campaign_id)
        if not campaign:
            raise ValueError(f"Campaña {campaign_id} no encontrada")
        
        start_date = start_date or campaign.start_date
        end_date = end_date or datetime.now()
        
        # Calcular métricas
        total_impressions = campaign.impressions
        total_clicks = campaign.clicks
        total_conversions = campaign.conversions
        total_spend = campaign.revenue
        total_revenue = campaign.revenue * 8  # Simular revenue (ROAS 8x)
        
        ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
        cpc = (total_spend / total_clicks) if total_clicks > 0 else 0
        cpa = (total_spend / total_conversions) if total_conversions > 0 else 0
        roas = (total_revenue / total_spend) if total_spend > 0 else 0
        
        # Top creativos (simulado)
        top_creatives = [
            {
                "creative_id": f"creative_{i}",
                "impressions": total_impressions // len(campaign.ad_creatives),
                "clicks": total_clicks // len(campaign.ad_creatives),
                "ctr": ctr,
                "performance_score": 0.8 + (i * 0.05)
            }
            for i in range(min(3, len(campaign.ad_creatives)))
        ]
        
        # Insights de audiencia (generados con IA)
        audience_insights = self._generate_audience_insights(campaign)
        
        # Recomendaciones (generadas con IA)
        recommendations = self._generate_recommendations(campaign, ctr, roas)
        
        analytics = AdAnalytics(
            campaign_id=campaign_id,
            date_range=(start_date, end_date),
            total_impressions=total_impressions,
            total_clicks=total_clicks,
            total_conversions=total_conversions,
            total_spend=total_spend,
            total_revenue=total_revenue,
            ctr=ctr,
            cpc=cpc,
            cpa=cpa,
            roas=roas,
            top_performing_creatives=top_creatives,
            audience_insights=audience_insights,
            recommendations=recommendations
        )
        
        self.analytics[campaign_id] = analytics
        return analytics
    
    def _generate_audience_insights(self, campaign: AdCampaign) -> Dict[str, Any]:
        """Genera insights de audiencia usando IA"""
        prompt = f"""Analiza la audiencia objetivo de esta campaña y genera insights:
        
        AUDIENCIA OBJETIVO:
        {json.dumps(campaign.target_audience, indent=2)}
        
        MÉTRICAS:
        - Impresiones: {campaign.impressions}
        - Clicks: {campaign.clicks}
        - CTR: {campaign.ctr:.2%}
        
        Genera insights en formato JSON:
        - primary_demographic: Demografía principal
        - peak_engagement_times: Horarios de mayor engagement
        - content_preferences: Preferencias de contenido
        - optimization_suggestions: Sugerencias de optimización
        """
        
        try:
            response = self.llm.invoke(prompt).content.strip()
            if response.startswith("```json"):
                response = response.replace("```json", "").replace("```", "").strip()
            elif response.startswith("```"):
                response = response.replace("```", "").strip()
            return json.loads(response)
        except:
            return {
                "primary_demographic": "25-45 años",
                "peak_engagement_times": ["19:00-21:00"],
                "content_preferences": ["Video", "Imágenes"],
                "optimization_suggestions": ["Mejorar targeting", "Optimizar creativos"]
            }
    
    def _generate_recommendations(self, campaign: AdCampaign, ctr: float, roas: float) -> List[str]:
        """Genera recomendaciones de optimización usando IA"""
        recommendations = []
        
        if ctr < 0.02:
            recommendations.append("CTR bajo: Considera mejorar los creativos o ajustar el targeting")
        
        if roas < 3.0:
            recommendations.append("ROAS bajo: Optimiza el targeting o aumenta el presupuesto en audiencias de alto rendimiento")
        
        if campaign.impressions < 1000:
            recommendations.append("Pocas impresiones: Aumenta el presupuesto o expande la audiencia")
        
        recommendations.append("Prueba variaciones de creativos con A/B testing")
        recommendations.append("Considera retargeting para usuarios que visitaron pero no compraron")
        
        return recommendations
    
    # ==================== AI AGENTS AUTÓNOMOS ====================
    
    def create_autonomous_marketing_agent(
        self,
        campaign_id: str,
        agent_name: str,
        capabilities: List[str]  # ["budget_optimization", "creative_generation", "lead_response"]
    ) -> Dict[str, Any]:
        """
        Crea un agente de marketing autónomo que gestiona campañas 24/7
        """
        agent_id = f"agent_{uuid.uuid4().hex[:12]}"
        
        agent_config = {
            "agent_id": agent_id,
            "campaign_id": campaign_id,
            "name": agent_name,
            "capabilities": capabilities,
            "status": "active",
            "created_at": datetime.now().isoformat(),
            "actions_taken": [],
            "performance_metrics": {
                "budget_optimized": 0,
                "creatives_generated": 0,
                "leads_responded": 0,
                "revenue_generated": 0.0
            }
        }
        
        print(f"🤖 Agente autónomo '{agent_name}' creado para campaña {campaign_id}")
        return agent_config
    
    def autonomous_agent_optimize_budget(self, agent_id: str, campaign_id: str) -> Dict[str, Any]:
        """El agente optimiza el presupuesto automáticamente"""
        campaign = self.campaigns.get(campaign_id)
        if not campaign:
            return {"success": False, "error": "Campaña no encontrada"}
        
        # Lógica de optimización (simulada)
        if campaign.ctr > 0.05 and campaign.roas > 5.0:
            # Aumentar presupuesto diario si está funcionando bien
            if campaign.daily_budget:
                campaign.daily_budget *= 1.2
                return {
                    "success": True,
                    "action": "budget_increased",
                    "new_daily_budget": campaign.daily_budget,
                    "reason": "Alto CTR y ROAS, aumentando presupuesto"
                }
        elif campaign.ctr < 0.01:
            # Reducir presupuesto si está funcionando mal
            if campaign.daily_budget:
                campaign.daily_budget *= 0.8
                return {
                    "success": True,
                    "action": "budget_decreased",
                    "new_daily_budget": campaign.daily_budget,
                    "reason": "Bajo CTR, reduciendo presupuesto"
                }
        
        return {"success": True, "action": "no_change", "reason": "Métricas dentro del rango óptimo"}
    
    # ==================== RETARGETING Y PERSONALIZACIÓN ====================
    
    def create_retargeting_campaign(
        self,
        advertiser_id: str,
        base_campaign_id: str,
        retargeting_rules: Dict[str, Any]
    ) -> AdCampaign:
        """
        Crea una campaña de retargeting basada en comportamiento de usuarios
        """
        base_campaign = self.campaigns.get(base_campaign_id)
        if not base_campaign:
            raise ValueError(f"Campaña base {base_campaign_id} no encontrada")
        
        # Crear audiencia de retargeting
        retargeting_audience = {
            **base_campaign.target_audience,
            "retargeting": True,
            "rules": retargeting_rules,
            "user_segments": retargeting_rules.get("segments", ["cart_abandoners", "website_visitors"])
        }
        
        # Generar creativos específicos para retargeting
        retargeting_creatives = [
            self.generate_ad_creative(
                product_description=base_campaign.name,
                target_audience=retargeting_audience,
                persuasion_principle="urgency"
            )
        ]
        
        retargeting_campaign = self.create_campaign(
            advertiser_id=advertiser_id,
            name=f"Retargeting: {base_campaign.name}",
            budget=base_campaign.budget * 0.3,  # 30% del presupuesto base
            daily_budget=base_campaign.daily_budget * 0.3 if base_campaign.daily_budget else None,
            target_audience=retargeting_audience,
            ad_creatives=retargeting_creatives,
            pricing_tier=base_campaign.pricing_tier
        )
        
        print(f"🎯 Campaña de retargeting creada: {retargeting_campaign.campaign_id}")
        return retargeting_campaign
    
    # ==================== REPORTES Y ESTADÍSTICAS ====================
    
    def get_platform_statistics(self) -> Dict[str, Any]:
        """Obtiene estadísticas generales de la plataforma"""
        total_campaigns = len(self.campaigns)
        active_campaigns = len([c for c in self.campaigns.values() if c.status == AdStatus.ACTIVE])
        total_creators = len(self.creators)
        total_collaborations = len(self.collaborations)
        
        total_revenue = sum(c.revenue for c in self.campaigns.values())
        total_impressions = sum(c.impressions for c in self.campaigns.values())
        total_clicks = sum(c.clicks for c in self.campaigns.values())
        
        avg_ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
        
        return {
            "total_campaigns": total_campaigns,
            "active_campaigns": active_campaigns,
            "total_creators": total_creators,
            "total_collaborations": total_collaborations,
            "total_revenue": total_revenue,
            "total_impressions": total_impressions,
            "total_clicks": total_clicks,
            "average_ctr": avg_ctr,
            "platform_commission_earned": total_revenue * self.marketplace_commission,
            "estimated_annual_revenue": total_revenue * 12  # Proyección anual
        }


# Instancia global
_marketplace_mode_instance: Optional[MarketplaceMode] = None


def get_marketplace_mode(
    config: AppConfig,
    provider: str = "openai"
) -> MarketplaceMode:
    """Obtiene o crea la instancia global de Marketplace Mode"""
    global _marketplace_mode_instance
    
    if _marketplace_mode_instance is None:
        _marketplace_mode_instance = MarketplaceMode(
            config=config,
            provider=provider
        )
    
    return _marketplace_mode_instance


def run_marketplace_mode(
    action: str,
    params: Dict[str, Any],
    config: Optional[AppConfig] = None,
    provider: str = "openai"
) -> Any:
    """Ejecuta acciones del Marketplace Mode"""
    if config is None:
        from .config import load_config
        config = load_config()
    
    marketplace = get_marketplace_mode(config=config, provider=provider)
    
    if action == "create_campaign":
        return marketplace.create_campaign(**params)
    elif action == "list_campaigns":
        return marketplace.list_campaigns(**params)
    elif action == "get_analytics":
        return marketplace.get_campaign_analytics(**params)
    elif action == "register_creator":
        return marketplace.register_creator(**params)
    elif action == "search_creators":
        return marketplace.search_creators(**params)
    elif action == "generate_creative":
        return marketplace.generate_ad_creative(**params)
    elif action == "get_statistics":
        return marketplace.get_platform_statistics()
    else:
        raise ValueError(f"Acción '{action}' no reconocida")

