"""
Ads Optimization Engine - Versión Production-Ready
Integra todos los módulos de producción
"""

from __future__ import annotations

import os
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, asdict

import numpy as np

# LangChain
from langchain_core.language_models import BaseLanguageModel

# Config
from ..config import AppConfig
from ..utils.llm_factory import create_llm

# Módulos de producción
from .models import ModelManager
from .database import DatabaseManager
from .retry_logic import APIClient, RetryConfig
from .rate_limiter import RateLimiterManager, RateLimitError
from .logging_config import setup_logging, get_logger, LoggerAdapter
from .tenant_manager import TenantManager, Tenant
from .billing import BillingManager
from .google_ads_integration import GoogleAdsIntegration
from .auth import AuthManager, User, Role, Permission
from .creative_generator import CreativeGenerator, AutonomousCampaignCreator, BusinessInfo

# Imports del engine original
from ..ads_optimization_engine import (
    CreativeAsset, AdVariation, Campaign, PerformanceMetrics,
    CreativeType, CampaignObjective, Platform,
    CreativeAssetManager, GenerativeAdVariationsEngine,
    CreativeSelector, CampaignManager, RLAutoOptimizer, AutoScalingSystem
)


class ProductionAdsOptimizationEngine:
    """
    Motor de optimización de anuncios - Versión Production-Ready
    Integra todos los módulos de producción
    """
    
    def __init__(
        self,
        config: AppConfig,
        llm: Optional[BaseLanguageModel] = None,
        tenant_id: Optional[str] = None
    ):
        self.config = config
        self.llm = llm or create_llm(config, provider="openai")
        self.tenant_id = tenant_id or "default"
        
        # Directorio de datos
        self.data_dir = Path(config.memory_dir) / "ads_optimization" if config.memory_dir else Path("data/ads_optimization")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup logging
        log_file = self.data_dir / "logs" / "ads_optimization.log"
        self.logger = setup_logging(
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            log_file=log_file,
            enable_sentry=os.getenv("SENTRY_DSN") is not None,
            sentry_dsn=os.getenv("SENTRY_DSN")
        )
        self.log = LoggerAdapter(self.logger, tenant_id=self.tenant_id)
        
        # Inicializar módulos de producción
        self.log.info("Inicializando módulos de producción...")
        
        # Database
        self.db_manager = DatabaseManager(config)
        self.log.info("Database manager inicializado")
        
        # Models
        self.model_manager = ModelManager(config)
        self.log.info("Model manager inicializado")
        
        # Tenant
        self.tenant_manager = TenantManager(self.data_dir)
        if not self.tenant_manager.get_tenant(self.tenant_id):
            # Crear tenant por defecto si no existe
            self.tenant_manager.create_tenant("Default Tenant", "default@example.com", "free")
        self.log.info(f"Tenant manager inicializado para tenant: {self.tenant_id}")
        
        # Billing
        self.billing_manager = BillingManager(self.data_dir)
        self.log.info("Billing manager inicializado")
        
        # Auth
        self.auth_manager = AuthManager(self.data_dir)
        self.log.info("Auth manager inicializado")
        
        # Cache
        self.cache_manager = CacheManager(os.getenv("REDIS_URL"))
        self.prediction_cache = PredictionCache(self.cache_manager)
        self.api_cache = APICache(self.cache_manager)
        self.log.info("Cache manager inicializado")
        
        # Monitoring
        self.monitoring = MonitoringSystem(
            start_metrics_server=os.getenv("ENABLE_METRICS_SERVER", "false").lower() == "true",
            metrics_port=int(os.getenv("METRICS_PORT", "8000"))
        )
        self.log.info("Monitoring system inicializado")
        
        # Rate Limiter
        try:
            import redis
            redis_client = redis.Redis.from_url(
                os.getenv("REDIS_URL", "redis://localhost:6379"),
                decode_responses=True
            )
            redis_client.ping()  # Test connection
            self.rate_limiter = RateLimiterManager(redis_client)
            self.log.info("Rate limiter con Redis inicializado")
        except Exception:
            self.rate_limiter = RateLimiterManager()
            self.log.warning("Rate limiter en memoria (Redis no disponible)")
        
        # Google Ads Integration
        self.google_ads = GoogleAdsIntegration(config)
        self.log.info("Google Ads integration inicializada")
        
        # Creative Generator (Zuckerberg-style: genera todo desde cero)
        self.creative_generator = CreativeGenerator(config)
        self.autonomous_creator = AutonomousCampaignCreator(config)
        self.log.info("Creative Generator inicializado (generación completa de activos)")
        
        # API Clients con retry y circuit breakers
        retry_config = RetryConfig(
            max_attempts=3,
            initial_wait=1.0,
            max_wait=60.0
        )
        self.meta_client = APIClient("meta", retry_config)
        self.google_client = APIClient("google", retry_config)
        self.tiktok_client = APIClient("tiktok", retry_config)
        
        # Componentes del engine original
        self.asset_manager = CreativeAssetManager(self.data_dir)
        self.generative_engine = GenerativeAdVariationsEngine(config, self.llm)
        self.creative_selector = CreativeSelector(
            self.model_manager.get_model("sowide_v2")
        )
        self.campaign_manager = CampaignManager(self.data_dir)
        self.rl_optimizer = RLAutoOptimizer(config)
        self.auto_scaler = AutoScalingSystem()
        
        self.log.info("✅ Ads Optimization Engine inicializado (Production Mode)")
    
    def _check_quota(self, resource: str, amount: int = 1) -> bool:
        """Verifica cuota antes de operación"""
        if not self.tenant_manager.check_quota(self.tenant_id, resource, amount):
            tenant = self.tenant_manager.get_tenant(self.tenant_id)
            quota = self.tenant_manager.get_quota(self.tenant_id)
            self.log.warning(f"Quota excedida para {resource}")
            raise ValueError(
                f"Quota excedida para {resource}. "
                f"Plan: {tenant.plan if tenant else 'unknown'}. "
                f"Upgrade a plan superior para más recursos."
            )
        return True
    
    def _record_usage(self, resource: str, amount: float = 1.0):
        """Registra uso para facturación"""
        self.tenant_manager.increment_usage(self.tenant_id, resource, int(amount))
        self.billing_manager.record_usage(
            self.tenant_id,
            resource,
            amount
        )
    
    async def upload_creative_asset(
        self,
        asset_type: CreativeType,
        content: Union[str, bytes, Path],
        metadata: Optional[Dict[str, Any]] = None
    ) -> CreativeAsset:
        """Sube un asset creativo con validación y tracking"""
        self.log.info(f"Subiendo asset tipo {asset_type.value}")
        
        # Verificar cuota
        self._check_quota("assets")
        
        # Subir asset
        asset = self.asset_manager.upload_asset(asset_type, content, metadata)
        
        # Guardar en DB
        self.db_manager.create_asset(
            asset_id=asset.asset_id,
            tenant_id=self.tenant_id,
            asset_type=asset_type.value,
            file_path=asset.file_path,
            file_size=asset.file_size,
            mime_type=asset.mime_type,
            metadata=metadata or {}
        )
        
        # Registrar uso
        self._record_usage("assets")
        
        self.log.info(f"Asset {asset.asset_id} subido exitosamente")
        return asset
    
    async def generate_ad_variations(
        self,
        asset_id: str,
        num_variations: int = 5,
        objective: Optional[CampaignObjective] = None,
        target_audience: Optional[Dict[str, Any]] = None
    ) -> List[AdVariation]:
        """Genera variaciones con validación"""
        self.log.info(f"Generando {num_variations} variaciones para asset {asset_id}")
        
        # Verificar cuota
        quota = self.tenant_manager.get_quota(self.tenant_id)
        if num_variations > quota.max_variations_per_asset:
            num_variations = quota.max_variations_per_asset
            self.log.warning(f"Limitando variaciones a {num_variations} por cuota")
        
        # Obtener asset
        asset = self.asset_manager.get_asset(asset_id)
        if not asset:
            raise ValueError(f"Asset {asset_id} no encontrado")
        
        # Generar variaciones
        variations = await self.generative_engine.generate_variations(
            asset, num_variations, objective, target_audience
        )
        
        # Registrar uso
        self._record_usage("variations", len(variations))
        
        self.log.info(f"Generadas {len(variations)} variaciones")
        return variations
    
    async def predict_performance(
        self,
        variations: List[AdVariation],
        platform: Platform,
        objective: CampaignObjective
    ) -> List[AdVariation]:
        """Predice performance usando modelos reales con cache"""
        self.log.info(f"Prediciendo performance para {len(variations)} variaciones")
        
        import time
        start_time = time.time()
        
        model = self.model_manager.get_model("sowide_v2")
        
        for variation in variations:
            # Verificar cache primero
            cache_key = f"{variation.variation_id}_{platform.value}_{objective.value}"
            cached = self.prediction_cache.get_prediction(
                variation.variation_id,
                platform.value,
                objective.value
            )
            
            if cached:
                variation.predicted_ctr = cached.get("ctr", 0.0)
                variation.predicted_cpc = cached.get("cpc", 0.0)
                variation.predicted_conversion_prob = cached.get("conversion_prob", 0.0)
                self.log.debug(f"Predicción desde cache para {variation.variation_id}")
                continue
            
            # Preparar datos para predicción
            ad_data = {
                "headline": variation.headline,
                "description": variation.description,
                "quality_score": variation.quality_score
            }
            
            # Predecir CTR usando modelo real
            variation.predicted_ctr = model.predict(ad_data)
            
            # Predecir CPC y conversión
            variation.predicted_cpc = self._predict_cpc(variation, platform, objective)
            variation.predicted_conversion_prob = self._predict_conversion_prob(
                variation, platform, objective
            )
            
            # Guardar en cache
            self.prediction_cache.set_prediction(
                variation.variation_id,
                platform.value,
                objective.value,
                {
                    "ctr": variation.predicted_ctr,
                    "cpc": variation.predicted_cpc,
                    "conversion_prob": variation.predicted_conversion_prob
                }
            )
            
            # Registrar uso de predicción
            self._record_usage("predictions", 1.0)
        
        latency = time.time() - start_time
        self.monitoring.record_prediction(latency)
        
        self.log.info(f"Predicciones completadas en {latency:.2f}s")
        return variations
    
    def _predict_cpc(
        self,
        variation: AdVariation,
        platform: Platform,
        objective: CampaignObjective
    ) -> float:
        """Predice CPC"""
        ctr = variation.predicted_ctr
        
        base_cpc = {
            Platform.META: 1.5,
            Platform.GOOGLE: 2.0,
            Platform.TIKTOK: 1.2,
            Platform.LINKEDIN: 5.0
        }.get(platform, 2.0)
        
        predicted_cpc = base_cpc * (1.0 / max(ctr, 0.001))
        
        objective_multiplier = {
            CampaignObjective.AWARENESS: 0.8,
            CampaignObjective.TRAFFIC: 1.0,
            CampaignObjective.ENGAGEMENT: 0.9,
            CampaignObjective.LEADS: 1.2,
            CampaignObjective.CONVERSIONS: 1.5,
            CampaignObjective.SALES: 1.8
        }.get(objective, 1.0)
        
        return float(predicted_cpc * objective_multiplier)
    
    def _predict_conversion_probability(
        self,
        variation: AdVariation,
        platform: Platform,
        objective: CampaignObjective
    ) -> float:
        """Predice probabilidad de conversión"""
        base_conversion_rate = {
            CampaignObjective.AWARENESS: 0.05,
            CampaignObjective.TRAFFIC: 0.10,
            CampaignObjective.ENGAGEMENT: 0.15,
            CampaignObjective.LEADS: 0.25,
            CampaignObjective.CONVERSIONS: 0.30,
            CampaignObjective.SALES: 0.20
        }.get(objective, 0.15)
        
        conversion_prob = base_conversion_rate * (1.0 + variation.predicted_ctr * 2.0)
        return float(np.clip(conversion_prob, 0.01, 0.50))
    
    async def create_and_launch_campaign(
        self,
        name: str,
        platform: Platform,
        objective: CampaignObjective,
        budget: float,
        asset_id: str,
        num_variations: int = 5,
        target_audience: Optional[Dict[str, Any]] = None,
        auto_select_best: bool = True,
        top_k: int = 3
    ) -> Dict[str, Any]:
        """Crea y lanza campaña con validación completa"""
        self.log.info(f"Creando campaña: {name}")
        
        # Verificar cuota de campañas
        self._check_quota("campaigns")
        
        # Verificar cuota de presupuesto
        quota = self.tenant_manager.get_quota(self.tenant_id)
        if budget > quota.max_budget_per_campaign:
            raise ValueError(f"Presupuesto ${budget} excede máximo ${quota.max_budget_per_campaign}")
        
        # Verificar rate limit
        platform_name = platform.value
        if not self.rate_limiter.is_allowed(platform_name, self.tenant_id):
            remaining = self.rate_limiter.get_remaining(platform_name, self.tenant_id)
            raise RateLimitError(f"Rate limit excedido. Requests restantes: {remaining}")
        
        # Registrar uso de API
        self._record_usage("api_calls", 1.0)
        
        # Generar variaciones
        variations = await self.generate_ad_variations(
            asset_id, num_variations, objective, target_audience
        )
        
        # Predecir performance
        variations = await self.predict_performance(variations, platform, objective)
        
        # Seleccionar mejores
        if auto_select_best:
            selected_variations = self.creative_selector.select_best_creatives(
                variations, platform, objective, top_k
            )
        else:
            selected_variations = variations
        
        # Crear campaña
        variation_ids = [v.variation_id for v in selected_variations]
        campaign = self.campaign_manager.create_campaign(
            name=name,
            platform=platform,
            objective=objective,
            budget=budget,
            target_audience=target_audience,
            ad_variations=variation_ids
        )
        
        # Guardar en DB
        self.db_manager.create_campaign(
            campaign_id=campaign.campaign_id,
            tenant_id=self.tenant_id,
            name=name,
            platform=platform.value,
            objective=objective.value,
            budget=budget,
            daily_budget=budget / 30,
            target_audience=target_audience
        )
        
        # Registrar uso
        self._record_usage("campaigns")
        
        # Lanzar campaña con retry y circuit breaker
        import time
        api_start = time.time()
        
        try:
            if platform == Platform.META:
                launch_result = await self.meta_client.call(
                    self.campaign_manager._launch_meta_campaign,
                    campaign
                )
                platform_name = "meta"
            elif platform == Platform.GOOGLE:
                # Usar integración completa de Google Ads
                launch_result = self.google_ads.create_campaign(
                    name=name,
                    budget=budget,
                    objective=objective.value
                )
                platform_name = "google"
            elif platform == Platform.TIKTOK:
                launch_result = await self.tiktok_client.call(
                    self.campaign_manager._launch_tiktok_campaign,
                    campaign
                )
                platform_name = "tiktok"
            else:
                launch_result = {"success": False, "error": "Platform not supported"}
                platform_name = "unknown"
            
            api_latency = time.time() - api_start
            self.monitoring.record_api_call(
                platform_name,
                launch_result.get("success", False),
                api_latency
            )
            
        except Exception as e:
            api_latency = time.time() - api_start
            self.monitoring.record_api_call(platform_name, False, api_latency)
            self.log.error(f"Error lanzando campaña: {e}")
            launch_result = {"success": False, "error": str(e)}
        
        if launch_result.get("success"):
            campaign.status = "active"
            self.campaign_manager._save_campaigns()
        
        self.log.info(f"Campaña {campaign.campaign_id} creada y lanzada")
        
        # Registrar métricas
        self.monitoring.record_campaign_created()
        
        # Verificar alertas
        metrics_dict = {
            "budget": budget,
            "spend": 0.0,
            "ctr": np.mean([v.predicted_ctr for v in selected_variations]),
            "cpc": np.mean([v.predicted_cpc for v in selected_variations]),
            "roas": 0.0
        }
        alerts = self.monitoring.check_campaign_alerts(
            campaign.campaign_id,
            self.tenant_id,
            metrics_dict
        )
        if alerts:
            self.log.warning(f"Alertas generadas para campaña {campaign.campaign_id}: {len(alerts)}")
        
        return {
            "campaign": campaign,
            "variations": selected_variations,
            "launch_result": launch_result,
            "predictions": {
                "avg_predicted_ctr": np.mean([v.predicted_ctr for v in selected_variations]),
                "avg_predicted_cpc": np.mean([v.predicted_cpc for v in selected_variations]),
                "avg_predicted_conversion_prob": np.mean([v.predicted_conversion_prob for v in selected_variations])
            },
            "alerts": [{"level": a.level.value, "message": a.message} for a in alerts]
        }
    
    def update_performance(
        self,
        campaign_id: str,
        metrics: PerformanceMetrics
    ):
        """Actualiza métricas con guardado en DB"""
        self.log.info(f"Actualizando métricas para campaña {campaign_id}")
        
        # Guardar en DB
        self.db_manager.save_performance_metrics(
            tenant_id=self.tenant_id,
            campaign_id=campaign_id,
            variation_id=None,
            impressions=metrics.impressions,
            clicks=metrics.clicks,
            conversions=metrics.conversions,
            spend=metrics.spend,
            ctr=metrics.ctr,
            cpc=metrics.cpc,
            cpm=metrics.cpm,
            cpa=metrics.cpa,
            roas=metrics.roas,
            conversion_rate=metrics.conversion_rate
        )
        
        # También guardar en sistema original (compatibilidad)
        if not hasattr(self, 'performance_metrics'):
            self.performance_metrics = {}
        if campaign_id not in self.performance_metrics:
            self.performance_metrics[campaign_id] = []
        self.performance_metrics[campaign_id].append(metrics)
    
    async def auto_optimize_campaign(self, campaign_id: str) -> Dict[str, Any]:
        """Auto-optimiza con logging completo"""
        self.log.info(f"Auto-optimizando campaña {campaign_id}")
        
        campaign = self.campaign_manager.get_campaign(campaign_id)
        if not campaign:
            raise ValueError(f"Campaña {campaign_id} no encontrada")
        
        # Obtener métricas más recientes de DB
        # Por ahora usar sistema original
        if not hasattr(self, 'performance_metrics') or campaign_id not in self.performance_metrics:
            raise ValueError("No hay métricas disponibles")
        
        latest_metrics = self.performance_metrics[campaign_id][-1]
        
        # Optimizar con RL
        rl_result = self.rl_optimizer.optimize_bidding(
            campaign_id,
            latest_metrics,
            target_cpc=2.0,
            target_roas=3.0
        )
        
        # Evaluar scaling
        scaling_result = self.auto_scaler.evaluate_and_scale(
            campaign_id,
            latest_metrics,
            budget=campaign.budget
        )
        
        # Aplicar acciones
        actions_taken = []
        if scaling_result["should_pause"]:
            campaign.status = "paused"
            actions_taken.append("Campaign paused")
            self.log.warning(f"Campaña {campaign_id} pausada por bajo performance")
        
        if scaling_result["should_scale"]:
            scale_action = scaling_result["actions"][0]
            campaign.budget = scale_action["new_budget"]
            actions_taken.append(f"Budget aumentado a ${campaign.budget:.2f}")
            self.log.info(f"Campaña {campaign_id} escalada a ${campaign.budget:.2f}")
        
        self.campaign_manager._save_campaigns()
        
        self.log.info(f"Optimización completada para campaña {campaign_id}")
        
        return {
            "success": True,
            "rl_optimization": rl_result,
            "scaling_decision": scaling_result,
            "actions_taken": actions_taken,
            "bid_multiplier": rl_result["bid_multiplier"]
        }
    
    def get_billing_summary(self) -> Dict[str, Any]:
        """Obtiene resumen de facturación"""
        tenant = self.tenant_manager.get_tenant(self.tenant_id)
        if not tenant:
            return {}
        
        usage_summary = self.billing_manager.get_usage_summary(self.tenant_id, days=30)
        quota = self.tenant_manager.get_quota(self.tenant_id)
        
        return {
            "tenant_id": self.tenant_id,
            "plan": tenant.plan,
            "usage": usage_summary,
            "quotas": {
                "max_campaigns": quota.max_campaigns,
                "max_assets": quota.max_assets,
                "max_variations": quota.max_variations_per_asset,
                "max_api_calls": quota.max_api_calls_per_day,
                "max_budget": quota.max_budget_per_campaign
            },
            "current_usage": tenant.usage
        }
    
    def generate_bill(self) -> Dict[str, Any]:
        """Genera factura para el tenant"""
        tenant = self.tenant_manager.get_tenant(self.tenant_id)
        if not tenant:
            raise ValueError("Tenant no encontrado")
        
        bill = self.billing_manager.generate_bill(
            self.tenant_id,
            tenant.plan
        )
        
        return asdict(bill)
    
    async def create_campaign_from_business_description(
        self,
        business_description: str,
        objective: str,
        budget: float,
        platform: Platform,
        max_cost_per_result: Optional[float] = None,
        generate_massive_variations: bool = True,
        num_variations: int = 100
    ) -> Dict[str, Any]:
        """
        Crea campaña completa solo con descripción del negocio y objetivo
        Similar a la visión de Zuckerberg: "solo dame tu objetivo y yo hago todo"
        
        Args:
            business_description: Descripción del negocio (ej: "Vendo zapatos online")
            objective: Objetivo (ej: "quiero nuevos clientes", "quiero vender 100 pares")
            budget: Presupuesto total
            platform: Plataforma (Meta, Google, TikTok)
            max_cost_per_result: Máximo costo por resultado
            generate_massive_variations: Si generar miles de variaciones (como Zuckerberg)
            num_variations: Número de variaciones a generar (hasta 4,000)
        """
        self.log.info(f"Creando campaña autónoma desde descripción del negocio")
        
        # 1. Extraer información del negocio
        business_info = await self.autonomous_creator._extract_business_info(business_description)
        self.log.info(f"Negocio identificado: {business_info.business_name} ({business_info.business_type})")
        
        # 2. Generar creativos masivamente
        if generate_massive_variations:
            self.log.info(f"Generando {num_variations} variaciones automáticamente...")
            creatives = await self.creative_generator.generate_massive_variations(
                business_info,
                objective,
                target_count=num_variations
            )
        else:
            creatives = await self.creative_generator.generate_complete_campaign_from_business(
                business_info,
                objective,
                budget,
                num_creatives=10
            )
        
        self.log.info(f"Generados {len(creatives)} creativos completos")
        
        # 3. Convertir a AdVariations y predecir performance
        from ..ads_optimization_engine import AdVariation, CampaignObjective as CO
        
        # Mapear objective string a enum
        obj_map = {
            "awareness": CO.AWARENESS,
            "traffic": CO.TRAFFIC,
            "conversions": CO.CONVERSIONS,
            "sales": CO.SALES,
            "leads": CO.LEADS,
            "quiero nuevos clientes": CO.LEADS,
            "quiero vender": CO.SALES
        }
        campaign_objective = obj_map.get(objective.lower(), CO.AWARENESS)
        
        variations = []
        for creative in creatives:
            variation = AdVariation(
                variation_id=creative.creative_id,
                original_asset_id="generated",
                headline=creative.headline,
                description=creative.description,
                image_path=creative.image_path,
                metadata={
                    **creative.metadata,
                    "cta_button": creative.cta_button_text,
                    "button_color": creative.cta_button_color,
                    "layout": creative.layout,
                    "generated_from": "business_description"
                }
            )
            variations.append(variation)
        
        # 4. Predecir performance de todos
        self.log.info("Prediciendo performance de todas las variaciones...")
        variations = await self.predict_performance(variations, platform, campaign_objective)
        
        # 5. Seleccionar mejores automáticamente (top 10% o top 50, lo que sea menor)
        top_k = min(50, max(10, len(variations) // 10))
        best_variations = self.creative_selector.select_best_creatives(
            variations, platform, campaign_objective, top_k
        )
        
        self.log.info(f"Seleccionados {len(best_variations)} mejores creativos de {len(variations)}")
        
        # 6. Crear campaña con los mejores
        campaign_name = f"{business_info.business_name} - {objective}"
        result = await self.create_and_launch_campaign(
            name=campaign_name,
            platform=platform,
            objective=campaign_objective,
            budget=budget,
            asset_id="generated",  # Usar creativos generados
            num_variations=len(best_variations),
            auto_select_best=False,  # Ya seleccionados
            top_k=len(best_variations)
        )
        
        # Sobrescribir con nuestros creativos generados
        result["variations"] = best_variations
        result["total_creatives_generated"] = len(creatives)
        result["business_info"] = {
            "name": business_info.business_name,
            "type": business_info.business_type,
            "description": business_info.description
        }
        
        self.log.info(f"Campaña autónoma creada: {result['campaign'].campaign_id}")
        
        return result

