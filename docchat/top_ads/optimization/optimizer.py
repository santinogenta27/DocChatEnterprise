"""
Campaign Optimizer - Optimización automática de campañas
basada en métricas de performance
"""

from __future__ import annotations

from typing import Dict, List, Optional, Any
from langchain_core.language_models import BaseLanguageModel
from langchain_core.messages import SystemMessage, HumanMessage
import json
import re

from ...config import AppConfig
from ..utils.logger import TopAdsLogger


class CampaignOptimizer:
    """
    Optimizador de campañas publicitarias.
    
    Acciones:
    - Ajustar presupuesto
    - Pausar ads malos
    - Escalar ads ganadores
    - Cambiar segmentación
    - Regenerar creativos
    """
    
    def __init__(
        self,
        config: AppConfig,
        llm: BaseLanguageModel,
        logger: TopAdsLogger
    ):
        self.config = config
        self.llm = llm
        self.logger = logger
        self.optimization_count = 0
    
    def evaluate_performance(
        self,
        metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Evalúa el performance de una campaña.
        
        Args:
            metrics: Métricas de la campaña
        
        Returns:
            Evaluación con score y recomendaciones
        """
        # Calcular score de performance
        score = 0.0
        
        # CTR (peso: 30%)
        ctr = metrics.get("ctr", 0.0)
        if ctr > 2.0:  # CTR > 2% es bueno
            score += 30
        elif ctr > 1.0:
            score += 15
        
        # CPA (peso: 30%)
        cpa = metrics.get("cpa", 0.0)
        target_cpa = 20.0  # CPA objetivo
        if cpa > 0 and cpa < target_cpa:
            score += 30
        elif cpa < target_cpa * 1.5:
            score += 15
        
        # ROAS (peso: 30%)
        roas = metrics.get("roas", 0.0)
        if roas > 3.0:  # ROAS > 3x es excelente
            score += 30
        elif roas > 2.0:
            score += 15
        
        # Conversiones (peso: 10%)
        conversions = metrics.get("conversions", 0)
        if conversions > 10:
            score += 10
        elif conversions > 5:
            score += 5
        
        evaluation = {
            "performance_score": min(score, 100),
            "metrics": metrics,
            "issues": [],
            "strengths": [],
            "recommendations": []
        }
        
        # Identificar issues
        if ctr < 0.5:
            evaluation["issues"].append("CTR muy bajo")
            evaluation["recommendations"].append("Mejorar creativos o targeting")
        
        if cpa > target_cpa * 2:
            evaluation["issues"].append("CPA muy alto")
            evaluation["recommendations"].append("Optimizar pujas o audiencias")
        
        if roas < 1.0:
            evaluation["issues"].append("ROAS negativo")
            evaluation["recommendations"].append("Revisar estrategia de conversión")
        
        # Identificar strengths
        if ctr > 2.0:
            evaluation["strengths"].append("CTR excelente")
        
        if roas > 3.0:
            evaluation["strengths"].append("ROAS excelente")
        
        if conversions > 10:
            evaluation["strengths"].append("Alto volumen de conversiones")
        
        return evaluation
    
    def optimize_campaign(
        self,
        campaign_id: str,
        platform: str,
        metrics: Dict[str, Any],
        evaluation: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Optimiza una campaña basado en métricas y evaluación.
        
        Args:
            campaign_id: ID de la campaña
            platform: Plataforma ("meta" o "tiktok")
            metrics: Métricas actuales
            evaluation: Evaluación de performance
        
        Returns:
            Lista de optimizaciones aplicadas
        """
        self.logger.info(f"Optimizando campaña {campaign_id} en {platform}")
        
        optimizations = []
        performance_score = evaluation.get("performance_score", 50)
        issues = evaluation.get("issues", [])
        
        # Aplicar optimizaciones basadas en performance
        if performance_score < 30:
            # Performance muy bajo: pausar y regenerar
            optimizations.append({
                "action": "pause_campaign",
                "reason": "Performance muy bajo",
                "campaign_id": campaign_id,
                "platform": platform
            })
            
            optimizations.append({
                "action": "regenerate_creatives",
                "reason": "Necesita nuevos creativos",
                "campaign_id": campaign_id
            })
        
        elif performance_score < 60:
            # Performance bajo: ajustar presupuesto y targeting
            if "CTR muy bajo" in issues:
                optimizations.append({
                    "action": "adjust_targeting",
                    "reason": "Mejorar CTR",
                    "campaign_id": campaign_id,
                    "platform": platform
                })
            
            if "CPA muy alto" in issues:
                optimizations.append({
                    "action": "reduce_budget",
                    "reason": "CPA muy alto",
                    "campaign_id": campaign_id,
                    "platform": platform,
                    "budget_reduction": 0.2  # Reducir 20%
                })
        
        elif performance_score >= 80:
            # Performance excelente: escalar
            optimizations.append({
                "action": "scale_budget",
                "reason": "Performance excelente",
                "campaign_id": campaign_id,
                "platform": platform,
                "budget_increase": 0.3  # Aumentar 30%
            })
        
        self.optimization_count += 1
        return optimizations
    
    def get_optimization_count(self) -> int:
        """Retorna el número de optimizaciones realizadas."""
        return self.optimization_count


