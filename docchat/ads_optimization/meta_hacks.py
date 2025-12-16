"""
Meta Ads Hacks: Técnicas específicas para optimizar campañas en Meta
Basado en análisis de miles de campañas y reverse engineering del algoritmo
Implementa los 8 hacks principales identificados
"""

from __future__ import annotations

import time
import hashlib
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import defaultdict


@dataclass
class ClusterBombConfig:
    """Configuración para Cluster Bomb conversion trick"""
    high_converting_hours: List[int]  # Horas del día con más conversiones
    concentration_days: List[int]  # Días de la semana (0=Lunes, 6=Domingo)
    budget_multiplier: float = 1.67  # Multiplicador para días concentrados


@dataclass
class PopularKidConfig:
    """Configuración para Popular Kid strategy"""
    target_high_connectivity: bool = True
    min_friends: int = 500
    include_event_creators: bool = True
    include_group_admins: bool = True


class MetaAdsHacks:
    """
    Implementación de hacks específicos de Meta Ads
    Basado en análisis empírico de campañas exitosas
    """
    
    def __init__(self, config: Any):
        self.config = config
        self.conversion_clusters: Dict[str, List[datetime]] = defaultdict(list)
        self.confidence_scores: Dict[str, float] = {}
    
    def apply_cluster_bomb_trick(
        self,
        campaign_id: str,
        daily_budget: float,
        cluster_config: ClusterBombConfig
    ) -> Dict[str, Any]:
        """
        Hack #1: Cluster Bomb Conversion Trick
        Concentra presupuesto en horas/días de alta conversión para que Meta detecte "patrones"
        """
        # Calcular presupuesto concentrado
        total_days = len(cluster_config.concentration_days)
        if total_days == 0:
            total_days = 7
        
        concentrated_budget = daily_budget * (7 / total_days) * cluster_config.budget_multiplier
        
        schedule = {}
        for day in cluster_config.concentration_days:
            for hour in cluster_config.high_converting_hours:
                key = f"{day}_{hour}"
                schedule[key] = {
                    "budget": concentrated_budget / (len(cluster_config.high_converting_hours) * total_days),
                    "enabled": True
                }
        
        return {
            "strategy": "cluster_bomb",
            "original_budget": daily_budget,
            "concentrated_budget": concentrated_budget,
            "schedule": schedule,
            "rationale": "Concentrar conversiones en ventanas específicas ayuda al algoritmo a detectar patrones más rápido"
        }
    
    def apply_popular_kid_strategy(
        self,
        base_audience: Dict[str, Any],
        popular_kid_config: PopularKidConfig
    ) -> Dict[str, Any]:
        """
        Hack #2: Popular Kid Strategy
        Target usuarios altamente conectados durante fase de aprendizaje
        """
        enhanced_audience = {**base_audience}
        
        # Agregar intereses de usuarios altamente conectados
        if popular_kid_config.target_high_connectivity:
            if "interests" not in enhanced_audience:
                enhanced_audience["interests"] = []
            
            # Agregar intereses relacionados con creación de contenido
            if popular_kid_config.include_event_creators:
                enhanced_audience["interests"].append({
                    "name": "Event creators",
                    "type": "behavior"
                })
            
            if popular_kid_config.include_group_admins:
                enhanced_audience["interests"].append({
                    "name": "Group administrators",
                    "type": "behavior"
                })
        
        # Agregar custom audience de usuarios con muchos amigos
        enhanced_audience["custom_audiences"] = enhanced_audience.get("custom_audiences", [])
        enhanced_audience["custom_audiences"].append({
            "name": "High connectivity users",
            "min_friends": popular_kid_config.min_friends
        })
        
        return {
            "strategy": "popular_kid",
            "enhanced_audience": enhanced_audience,
            "rationale": "Usuarios altamente conectados entrenan el algoritmo más rápido"
        }
    
    def apply_breadcrumb_trail(
        self,
        main_conversion: str,
        micro_conversions: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        Hack #3: Breadcrumb Trail Method
        Crea micro-conversiones frecuentes antes de la conversión principal
        """
        conversion_funnel = {
            "main_conversion": main_conversion,
            "micro_conversions": micro_conversions,
            "optimization_target": micro_conversions[-1]["event"] if micro_conversions else main_conversion
        }
        
        # Ordenar micro-conversiones por frecuencia esperada (más frecuentes primero)
        conversion_funnel["micro_conversions"].sort(key=lambda x: x.get("expected_frequency", 0), reverse=True)
        
        return {
            "strategy": "breadcrumb_trail",
            "funnel": conversion_funnel,
            "rationale": "Más datos de micro-conversiones = algoritmo aprende más rápido"
        }
    
    def apply_time_machine_arbitrage(
        self,
        campaign_id: str,
        engagement_campaign_budget: float
    ) -> Dict[str, Any]:
        """
        Hack #4: Time Machine Arbitrage
        Front-load engagement, luego retarget rápidamente mientras algoritmo "recuerda"
        """
        strategy = {
            "phase_1": {
                "duration_days": 7,
                "objective": "engagement",
                "budget": engagement_campaign_budget,
                "content_type": "high_engagement",  # memes, contenido viral
                "goal": "Generar máximo engagement para etiquetar usuarios"
            },
            "phase_2": {
                "duration_days": 7,
                "objective": "conversions",
                "budget": engagement_campaign_budget * 1.5,
                "retargeting": {
                    "source": "phase_1_engagers",
                    "lookback_window_hours": 168,  # 7 días
                    "optimization": "engagement_signals_still_active"
                }
            }
        }
        
        return {
            "strategy": "time_machine_arbitrage",
            "phases": strategy,
            "rationale": "Engagement signals se actualizan en 5 min, conversiones en 1-7 días. Gap explotable."
        }
    
    def apply_twin_campaign_exploit(
        self,
        base_campaign: Dict[str, Any],
        offset_hours: int = 12
    ) -> List[Dict[str, Any]]:
        """
        Hack #5: Twin Campaign Exploit
        Duplica campaña con offset temporal para doblar datos de aprendizaje
        """
        campaign_a = {**base_campaign}
        campaign_a["id"] = f"{base_campaign.get('id', 'campaign')}_a"
        campaign_a["start_time"] = base_campaign.get("start_time", datetime.now())
        campaign_a["budget"] = base_campaign.get("budget", 100) / 2
        
        campaign_b = {**base_campaign}
        campaign_b["id"] = f"{base_campaign.get('id', 'campaign')}_b"
        campaign_b["start_time"] = campaign_a["start_time"] + timedelta(hours=offset_hours)
        campaign_b["budget"] = base_campaign.get("budget", 100) / 2
        
        return {
            "strategy": "twin_campaign",
            "campaigns": [campaign_a, campaign_b],
            "rationale": "Meta ve campañas separadas pero patrones exitosos se refuerzan 2x más rápido"
        }
    
    def apply_confidence_score_manipulation(
        self,
        conversion_event: str,
        confirmation_signals: List[str]
    ) -> Dict[str, Any]:
        """
        Hack #6: Confidence Score Manipulation
        Stack múltiples señales de confirmación para aumentar confidence score
        """
        tracking_setup = {
            "main_event": conversion_event,
            "confirmation_signals": confirmation_signals,
            "tracking_window_minutes": 30,  # Todas las señales dentro de 30 min
            "implementation": {
                "pixel": conversion_event,
                "conversions_api": confirmation_signals[0] if confirmation_signals else conversion_event,
                "server_events": confirmation_signals[1:] if len(confirmation_signals) > 1 else []
            }
        }
        
        return {
            "strategy": "confidence_score",
            "setup": tracking_setup,
            "rationale": "Múltiples señales de confirmación aumentan confidence score → algoritmo optimiza más agresivamente"
        }
    
    def apply_budget_surfing(
        self,
        current_budget: float,
        target_budget: float,
        increase_percentage: float = 0.20,
        interval_days: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Hack #7: Budget Surfing Technique
        Aumenta presupuesto gradualmente (max 20% cada 3 días) para evitar "pánico" del algoritmo
        """
        if target_budget <= current_budget:
            return []
        
        schedule = []
        current = current_budget
        day = 0
        
        while current < target_budget:
            increase = current * increase_percentage
            new_budget = min(current + increase, target_budget)
            
            schedule.append({
                "day": day,
                "budget": new_budget,
                "increase_percentage": (new_budget - current) / current * 100
            })
            
            current = new_budget
            day += interval_days
        
        return {
            "strategy": "budget_surfing",
            "schedule": schedule,
            "rationale": "Aumentos graduales evitan que el algoritmo 'resetee' optimización"
        }
    
    def apply_creative_exhaustion_override(
        self,
        creative_id: str,
        engagement_campaign_budget: float
    ) -> Dict[str, Any]:
        """
        Hack #8: Creative Exhaustion Override
        Extiende vida del creative manteniendo engagement alto
        """
        strategy = {
            "detection": {
                "metric": "engagement_rate_decline",
                "threshold": 0.20,  # 20% de declive
                "time_window_days": 3
            },
            "intervention": {
                "type": "engagement_boost",
                "budget": engagement_campaign_budget,
                "duration_days": 3,
                "goal": "Renovar interés en el creative existente"
            },
            "expected_outcome": {
                "creative_life_extension_days": 2,
                "performance_maintenance": "sustained"
            }
        }
        
        return {
            "strategy": "creative_exhaustion_override",
            "setup": strategy,
            "rationale": "Fatiga se mide por engagement, no tiempo. Boost de engagement = creative 'renovado'"
        }
    
    def get_optimal_hack_combination(
        self,
        campaign_type: str,
        budget: float,
        objective: str
    ) -> Dict[str, Any]:
        """
        Recomienda combinación óptima de hacks basado en tipo de campaña
        """
        recommendations = {
            "ecommerce": [
                "cluster_bomb",
                "breadcrumb_trail",
                "confidence_score"
            ],
            "lead_generation": [
                "popular_kid",
                "time_machine_arbitrage",
                "twin_campaign"
            ],
            "brand_awareness": [
                "time_machine_arbitrage",
                "creative_exhaustion_override"
            ],
            "app_install": [
                "breadcrumb_trail",
                "popular_kid",
                "twin_campaign"
            ]
        }
        
        hacks = recommendations.get(campaign_type, ["cluster_bomb", "budget_surfing"])
        
        return {
            "recommended_hacks": hacks,
            "rationale": f"Combinación optimizada para {campaign_type} con objetivo {objective}",
            "expected_improvement": "30-60% reduction in CPA"
        }
