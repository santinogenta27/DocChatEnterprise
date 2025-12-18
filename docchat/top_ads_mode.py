"""
Top Ads Mode - Autonomous AI Agent for Advertising
Un sistema completo comparable a Meta Ads Manager + AI Agent

🎯 OBJETIVO PRINCIPAL
Construir un AI Agent autónomo que:
- Reciba inputs del usuario (imágenes, videos, textos, objetivos, presupuesto)
- Cree, publique, optimice y escale campañas publicitarias automáticamente
- Opere en Meta Ads (Facebook, Instagram, WhatsApp) y TikTok Ads
- Gestione todo el ciclo de vida publicitario con autonomía configurable

🧩 ARQUITECTURA
1. Core Agent Layer (Brain) - LLM como motor de razonamiento
2. Input & Creative Processing Layer - Procesamiento multimodal
3. Campaign Strategy Engine - Decisión automática de estrategia
4. Ads Platform Integration Layer - Meta Ads + TikTok Ads APIs
5. Optimization & Learning Loop - Optimización continua
6. Autonomy Control System - Full Autonomous / Human-in-the-loop / Recommendation Only
7. Logging, Safety & Compliance - Logs estructurados, validación de políticas
"""

from __future__ import annotations

import json
import time
import asyncio
from typing import List, Dict, Optional, Any, Tuple
from pathlib import Path
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, asdict

from langchain_core.language_models import BaseLanguageModel
from langchain_openai import ChatOpenAI

from .config import AppConfig

# Importar tipos compartidos (evita importaciones circulares)
from .top_ads.types import (
    AutonomyMode,
    CampaignObjective,
    UserInput,
    CampaignResult,
    CampaignMetrics
)

# Importar módulos del sistema Top Ads
from .top_ads.agent.core_agent import TopAdsCoreAgent
from .top_ads.agent.planner import CampaignPlanner
from .top_ads.agent.decision_engine import DecisionEngine
from .top_ads.creatives.copy_generator import CopyGenerator
from .top_ads.creatives.asset_processor import AssetProcessor
from .top_ads.creatives.dynamic_creative_optimizer import DynamicCreativeOptimizer, UserProfile
from .top_ads.platforms.meta_ads import MetaAdsPlatform
from .top_ads.platforms.tiktok_ads import TikTokAdsPlatform
from .top_ads.optimization.metrics_collector import MetricsCollector
from .top_ads.optimization.optimizer import CampaignOptimizer
from .top_ads.utils.logger import TopAdsLogger
from .top_ads.utils.validators import AdsPolicyValidator


class TopAdsMode:
    """
    Top Ads Mode - Autonomous AI Agent for Advertising
    
    Sistema completo comparable a Meta Ads Manager + AI Agent.
    Production-ready, multi-tenant, escalable.
    """
    
    def __init__(
        self,
        config: AppConfig,
        llm: Optional[BaseLanguageModel] = None
    ):
        """
        Inicializa Top Ads Mode.
        
        Args:
            config: Configuración de la aplicación
            llm: Modelo de lenguaje (opcional, se crea automáticamente si no se proporciona)
        """
        self.config = config
        
        # Inicializar LLM
        if llm:
            self.llm = llm
        else:
            if not config.openai_api_key:
                raise ValueError("OPENAI_API_KEY requerida para Top Ads Mode")
            self.llm = ChatOpenAI(
                model=config.agentic_model or "gpt-4o",
                temperature=0.2,
                api_key=config.openai_api_key,
                max_tokens=4000
            )
        
        # Logger estructurado
        self.logger = TopAdsLogger(config=config)
        
        # Validator de políticas de ads
        self.policy_validator = AdsPolicyValidator(llm=self.llm, logger=self.logger)
        
        # Core Agent (Brain)
        self.core_agent = TopAdsCoreAgent(
            config=config,
            llm=self.llm,
            logger=self.logger
        )
        
        # Planner y Decision Engine
        self.planner = CampaignPlanner(
            config=config,
            llm=self.llm,
            logger=self.logger
        )
        
        self.decision_engine = DecisionEngine(
            config=config,
            llm=self.llm,
            logger=self.logger
        )
        
        # Creative Processing
        self.asset_processor = AssetProcessor(
            config=config,
            llm=self.llm,
            logger=self.logger
        )
        
        self.copy_generator = CopyGenerator(
            config=config,
            llm=self.llm,
            logger=self.logger
        )
        
        # Dynamic Creative Optimizer (DCO)
        self.dco = DynamicCreativeOptimizer(
            config=config,
            llm=self.llm,
            logger=self.logger
        )
        
        # Ads Platforms
        self.meta_ads = MetaAdsPlatform(
            config=config,
            logger=self.logger
        )
        
        self.tiktok_ads = TikTokAdsPlatform(
            config=config,
            logger=self.logger
        )
        
        # Optimization
        self.metrics_collector = MetricsCollector(
            config=config,
            meta_ads=self.meta_ads,
            tiktok_ads=self.tiktok_ads,
            logger=self.logger
        )
        
        self.optimizer = CampaignOptimizer(
            config=config,
            llm=self.llm,
            logger=self.logger
        )
        
        # Estado del sistema
        self.active_campaigns: Dict[str, Dict[str, Any]] = {}
        self.campaign_history: List[Dict[str, Any]] = []
        
        self.logger.info("Top Ads Mode inicializado correctamente")
    
    def create_campaign(
        self,
        user_input: UserInput,
        platforms: List[str] = None
    ) -> List[CampaignResult]:
        """
        Crea una campaña publicitaria completa de forma autónoma.
        
        Flujo:
        1. Procesar assets (imágenes, videos, textos)
        2. Generar creativos (copys, variantes)
        3. Planear estrategia de campaña
        4. Validar políticas de ads
        5. Publicar en plataformas
        6. Iniciar optimización
        
        Args:
            user_input: Input del usuario con assets y configuración
            platforms: Lista de plataformas ["meta", "tiktok"] (por defecto todas)
        
        Returns:
            Lista de resultados de campaña por plataforma
        """
        if platforms is None:
            platforms = ["meta", "tiktok"]
        
        self.logger.info(f"Iniciando creación de campaña: {user_input.campaign_name}")
        
        results = []
        
        try:
            # 1. Procesar assets
            self.logger.info("Procesando assets del usuario...")
            processed_assets = self.asset_processor.process_assets(
                images=user_input.images or [],
                videos=user_input.videos or [],
                texts=user_input.texts or []
            )
            
            # 1.5. Image Expansion (si hay imágenes y es modo autónomo)
            if user_input.images and user_input.autonomy_mode == AutonomyMode.FULL_AUTONOMOUS:
                self.logger.info("Aplicando Image Expansion a imágenes...")
                expanded_images = {}
                for img_path in user_input.images:
                    try:
                        expanded = self.asset_processor.expand_image_for_formats(
                            image_path=img_path,
                            formats=["1:1", "16:9", "9:16", "4:5"]
                        )
                        expanded_images[img_path] = expanded
                        # Agregar imágenes expandidas a processed_assets
                        for format_ratio, expanded_path in expanded.items():
                            processed_assets["images"].append({
                                "path": expanded_path,
                                "type": "image",
                                "format": format_ratio,
                                "original_path": img_path,
                                "is_expanded": True
                            })
                    except Exception as e:
                        self.logger.warning(f"Error en Image Expansion para {img_path}: {e}")
            
            # 2. Generar creativos
            self.logger.info("Generando creativos publicitarios...")
            creatives = self.copy_generator.generate_creatives(
                processed_assets=processed_assets,
                business_objective=user_input.business_objective.value,
                num_variants=10  # Generar 10 variantes por defecto
            )
            
            # 3. Validar políticas de ads
            self.logger.info("Validando políticas de ads...")
            validated_creatives = []
            for creative in creatives:
                is_valid, reason = self.policy_validator.validate_creative(creative)
                if is_valid:
                    validated_creatives.append(creative)
                else:
                    self.logger.warning(f"Creative rechazado por política: {reason}")
            
            if not validated_creatives:
                raise ValueError("Todos los creativos fueron rechazados por políticas de ads")
            
            # 4. Planear estrategia de campaña
            self.logger.info("Planificando estrategia de campaña...")
            force_broad = user_input.autonomy_mode == AutonomyMode.FULL_AUTONOMOUS
            campaign_plan = self.planner.plan_campaign(
                business_objective=user_input.business_objective.value,
                budget=user_input.budget,
                creatives=validated_creatives,
                target_audience=user_input.target_audience,
                force_broad_targeting=force_broad
            )
            
            # 5. Tomar decisión sobre estructura de campaña
            # (Esto fuerza broad targeting si es FULL_AUTONOMOUS)
            campaign_structure = self.decision_engine.decide_campaign_structure(
                plan=campaign_plan,
                autonomy_mode=user_input.autonomy_mode
            )
            
            # 5.5. Preparar componentes para DCO (si se requiere personalización dinámica)
            # Nota: DCO se aplicará en tiempo real cuando se sirva el ad al usuario
            # Aquí preparamos los componentes disponibles
            if validated_creatives:
                image_paths = [img.get("path") for img in processed_assets.get("images", []) if img.get("path")]
                headlines = [c.get("headline", "") for c in validated_creatives]
                primary_texts = [c.get("primary_text", "") for c in validated_creatives]
                descriptions = [c.get("description", "") for c in validated_creatives if c.get("description")]
                ctas = [c.get("cta", "Learn More") for c in validated_creatives]
                
                self.dco.load_components(
                    images=image_paths,
                    headlines=headlines,
                    primary_texts=primary_texts,
                    descriptions=descriptions if descriptions else None,
                    ctas=list(set(ctas)) if ctas else None  # CTAs únicos
                )
                self.logger.info("Componentes cargados en DCO para personalización dinámica")
            
            # 6. Publicar en cada plataforma
            for platform in platforms:
                try:
                    if platform == "meta":
                        result = self._publish_meta_campaign(
                            campaign_structure=campaign_structure,
                            creatives=validated_creatives,
                            user_input=user_input
                        )
                    elif platform == "tiktok":
                        result = self._publish_tiktok_campaign(
                            campaign_structure=campaign_structure,
                            creatives=validated_creatives,
                            user_input=user_input
                        )
                    else:
                        self.logger.warning(f"Plataforma no soportada: {platform}")
                        continue
                    
                    results.append(result)
                    
                    # Guardar campaña activa
                    self.active_campaigns[result.campaign_id] = {
                        "platform": platform,
                        "created_at": result.created_at,
                        "status": result.status,
                        "user_input": asdict(user_input),
                        "structure": campaign_structure
                    }
                    
                except Exception as e:
                    self.logger.error(f"Error publicando en {platform}: {e}")
                    continue
            
            # 7. Iniciar optimización automática
            if user_input.autonomy_mode == AutonomyMode.FULL_AUTONOMOUS:
                self._start_auto_optimization(results)
            
            self.logger.info(f"Campaña creada exitosamente: {len(results)} plataformas")
            
        except Exception as e:
            self.logger.error(f"Error creando campaña: {e}")
            raise
        
        return results
    
    def _publish_meta_campaign(
        self,
        campaign_structure: Dict[str, Any],
        creatives: List[Dict[str, Any]],
        user_input: UserInput
    ) -> CampaignResult:
        """Publica campaña en Meta Ads."""
        self.logger.info("Publicando campaña en Meta Ads...")
        
        # Crear campaña
        campaign_id = self.meta_ads.create_campaign(
            name=user_input.campaign_name or f"Top Ads Campaign {datetime.now().strftime('%Y%m%d_%H%M%S')}",
            objective=campaign_structure["objective"],
            status="ACTIVE"
        )
        
        # Crear ad sets
        ad_set_ids = []
        ad_ids = []
        
        for ad_set_config in campaign_structure["ad_sets"]:
            ad_set_id = self.meta_ads.create_ad_set(
                campaign_id=campaign_id,
                name=ad_set_config["name"],
                budget=ad_set_config["budget"],
                targeting=ad_set_config["targeting"],
                optimization_goal=ad_set_config["optimization_goal"]
            )
            ad_set_ids.append(ad_set_id)
            
            # Crear ads
            for ad_config in ad_set_config["ads"]:
                creative = creatives[ad_config["creative_index"]]
                
                ad_id = self.meta_ads.create_ad(
                    ad_set_id=ad_set_id,
                    name=ad_config["name"],
                    creative=creative,
                    status="ACTIVE"
                )
                ad_ids.append(ad_id)
        
        return CampaignResult(
            campaign_id=campaign_id,
            platform="meta",
            ad_set_ids=ad_set_ids,
            ad_ids=ad_ids,
            status="ACTIVE",
            created_at=datetime.now().isoformat()
        )
    
    def _publish_tiktok_campaign(
        self,
        campaign_structure: Dict[str, Any],
        creatives: List[Dict[str, Any]],
        user_input: UserInput
    ) -> CampaignResult:
        """Publica campaña en TikTok Ads."""
        self.logger.info("Publicando campaña en TikTok Ads...")
        
        # Crear campaña
        campaign_id = self.tiktok_ads.create_campaign(
            name=user_input.campaign_name or f"Top Ads Campaign {datetime.now().strftime('%Y%m%d_%H%M%S')}",
            objective=campaign_structure["objective"],
            budget=user_input.budget
        )
        
        # Crear ad groups
        ad_set_ids = []
        ad_ids = []
        
        for ad_set_config in campaign_structure["ad_sets"]:
            ad_group_id = self.tiktok_ads.create_ad_group(
                campaign_id=campaign_id,
                name=ad_set_config["name"],
                budget=ad_set_config["budget"],
                targeting=ad_set_config["targeting"]
            )
            ad_set_ids.append(ad_group_id)
            
            # Crear ads
            for ad_config in ad_set_config["ads"]:
                creative = creatives[ad_config["creative_index"]]
                
                ad_id = self.tiktok_ads.create_ad(
                    ad_group_id=ad_group_id,
                    name=ad_config["name"],
                    creative=creative
                )
                ad_ids.append(ad_id)
        
        return CampaignResult(
            campaign_id=campaign_id,
            platform="tiktok",
            ad_set_ids=ad_set_ids,
            ad_ids=ad_ids,
            status="ACTIVE",
            created_at=datetime.now().isoformat()
        )
    
    def _start_auto_optimization(self, campaign_results: List[CampaignResult]):
        """Inicia optimización automática de campañas."""
        self.logger.info("Iniciando optimización automática...")
        
        # Programar optimización periódica
        # En producción, esto se haría con un scheduler (Celery, etc.)
        for result in campaign_results:
            self.logger.info(f"Programando optimización para campaña {result.campaign_id}")
            # Aquí se iniciaría un proceso asíncrono de optimización continua
    
    def optimize_campaign(
        self,
        campaign_id: str,
        platform: str
    ) -> Dict[str, Any]:
        """
        Optimiza una campaña existente.
        
        Acciones:
        - Recolectar métricas
        - Evaluar performance
        - Ajustar presupuesto
        - Pausar ads malos
        - Escalar ads ganadores
        - Generar nuevas variantes
        """
        self.logger.info(f"Optimizando campaña {campaign_id} en {platform}")
        
        # Recolectar métricas
        metrics = self.metrics_collector.collect_campaign_metrics(
            campaign_id=campaign_id,
            platform=platform
        )
        
        # Evaluar performance
        evaluation = self.optimizer.evaluate_performance(metrics)
        
        # Aplicar optimizaciones
        optimizations = self.optimizer.optimize_campaign(
            campaign_id=campaign_id,
            platform=platform,
            metrics=metrics,
            evaluation=evaluation
        )
        
        return {
            "campaign_id": campaign_id,
            "platform": platform,
            "metrics": metrics,
            "evaluation": evaluation,
            "optimizations_applied": optimizations,
            "timestamp": datetime.now().isoformat()
        }
    
    def get_campaign_metrics(
        self,
        campaign_id: str,
        platform: str,
        date_range: Optional[Tuple[str, str]] = None
    ) -> CampaignMetrics:
        """Obtiene métricas de una campaña."""
        metrics = self.metrics_collector.collect_campaign_metrics(
            campaign_id=campaign_id,
            platform=platform,
            date_range=date_range
        )
        
        return CampaignMetrics(
            campaign_id=campaign_id,
            platform=platform,
            impressions=metrics.get("impressions", 0),
            clicks=metrics.get("clicks", 0),
            ctr=metrics.get("ctr", 0.0),
            cpc=metrics.get("cpc", 0.0),
            cpa=metrics.get("cpa", 0.0),
            roas=metrics.get("roas", 0.0),
            conversions=metrics.get("conversions", 0),
            spend=metrics.get("spend", 0.0),
            timestamp=datetime.now().isoformat()
        )
    
    def pause_campaign(
        self,
        campaign_id: str,
        platform: str
    ) -> bool:
        """Pausa una campaña."""
        self.logger.info(f"Pausando campaña {campaign_id} en {platform}")
        
        if platform == "meta":
            return self.meta_ads.pause_campaign(campaign_id)
        elif platform == "tiktok":
            return self.tiktok_ads.pause_campaign(campaign_id)
        else:
            raise ValueError(f"Plataforma no soportada: {platform}")
    
    def resume_campaign(
        self,
        campaign_id: str,
        platform: str
    ) -> bool:
        """Reanuda una campaña pausada."""
        self.logger.info(f"Reanudando campaña {campaign_id} en {platform}")
        
        if platform == "meta":
            return self.meta_ads.resume_campaign(campaign_id)
        elif platform == "tiktok":
            return self.tiktok_ads.resume_campaign(campaign_id)
        else:
            raise ValueError(f"Plataforma no soportada: {platform}")
    
    def create_dynamic_creative_for_user(
        self,
        user_profile: UserProfile
    ) -> Dict[str, Any]:
        """
        Crea un creative dinámico optimizado para un usuario específico (DCO).
        
        Similar a Meta's Dynamic Creative Optimization: combina componentes
        automáticamente según perfil del usuario.
        
        Args:
            user_profile: Perfil del usuario
        
        Returns:
            Creative dinámico optimizado
        """
        self.logger.info(f"Creando creative dinámico para usuario: {user_profile.age} años")
        
        dynamic_creative = self.dco.create_dynamic_creative(user_profile)
        
        return {
            "creative": dynamic_creative,
            "image_path": dynamic_creative.image_path,
            "headline": dynamic_creative.headline,
            "primary_text": dynamic_creative.primary_text,
            "description": dynamic_creative.description,
            "cta": dynamic_creative.cta,
            "combination_score": dynamic_creative.combination_score,
            "reasoning": "Creative optimizado dinámicamente según perfil de usuario"
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Obtiene estadísticas del sistema."""
        dco_stats = self.dco.get_statistics()
        return {
            "active_campaigns": len(self.active_campaigns),
            "total_campaigns": len(self.campaign_history),
            "platforms": {
                "meta": self.meta_ads.is_connected(),
                "tiktok": self.tiktok_ads.is_connected()
            },
            "optimization_runs": self.optimizer.get_optimization_count(),
            "creatives_generated": self.copy_generator.get_generation_count(),
            "dco": {
                "combinations_created": dco_stats.get("combinations_created", 0),
                "total_components": dco_stats.get("total_components", {}),
                "average_score": dco_stats.get("average_score", 0.0)
            }
        }


# Funciones de conveniencia para Gradio
_top_ads_mode_instance: Optional[TopAdsMode] = None


def get_top_ads_mode(
    config: Optional[AppConfig] = None,
    llm: Optional[BaseLanguageModel] = None
) -> TopAdsMode:
    """Obtiene o crea la instancia singleton de Top Ads Mode."""
    global _top_ads_mode_instance
    
    if _top_ads_mode_instance is None:
        if config is None:
            from .config import load_config
            config = load_config()
        
        _top_ads_mode_instance = TopAdsMode(config=config, llm=llm)
    
    return _top_ads_mode_instance


def run_top_ads_mode(
    images: List[str],
    videos: List[str],
    texts: List[str],
    business_objective: str,
    budget: float,
    autonomy_mode: str,
    campaign_name: Optional[str] = None,
    platforms: List[str] = None,
    config: Optional[AppConfig] = None
) -> Dict[str, Any]:
    """
    Función principal para ejecutar Top Ads Mode.
    Compatible con Gradio.
    """
    if config is None:
        from .config import load_config
        config = load_config()
    
    top_ads = get_top_ads_mode(config=config)
    
    # Crear UserInput
    user_input = UserInput(
        images=images or [],
        videos=videos or [],
        texts=texts or [],
        business_objective=CampaignObjective(business_objective),
        budget=budget,
        autonomy_mode=AutonomyMode(autonomy_mode),
        campaign_name=campaign_name
    )
    
    # Crear campaña
    results = top_ads.create_campaign(
        user_input=user_input,
        platforms=platforms or ["meta", "tiktok"]
    )
    
    return {
        "status": "success",
        "campaigns_created": len(results),
        "results": [asdict(r) for r in results]
    }


