"""
Decision Engine - Toma decisiones sobre estructura de campaña
y acciones de optimización basadas en autonomía configurada.
"""

from __future__ import annotations

from typing import Dict, Optional, Any
from langchain_core.language_models import BaseLanguageModel
from langchain_core.messages import SystemMessage, HumanMessage
import json
import re

from ...config import AppConfig
from ..utils.logger import TopAdsLogger
from ...top_ads_mode import AutonomyMode


class DecisionEngine:
    """
    Motor de decisión del sistema Top Ads.
    
    Responsabilidades:
    - Decidir estructura de campaña basada en plan
    - Aplicar modo de autonomía (full/approval/recommendation)
    - Decidir acciones de optimización
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
    
    def decide_campaign_structure(
        self,
        plan: Dict[str, Any],
        autonomy_mode: AutonomyMode
    ) -> Dict[str, Any]:
        """
        Decide la estructura final de campaña basada en el plan.
        
        Args:
            plan: Plan de campaña generado por el planner
            autonomy_mode: Modo de autonomía
        
        Returns:
            Estructura de campaña final con decisiones aplicadas
        """
        self.logger.info(f"Decidiendo estructura de campaña (autonomy: {autonomy_mode.value})")
        
        # Si es full autonomous, usar el plan directamente
        if autonomy_mode == AutonomyMode.FULL_AUTONOMOUS:
            return plan
        
        # Si es approval required, marcar para aprobación
        if autonomy_mode == AutonomyMode.APPROVAL_REQUIRED:
            plan["requires_approval"] = True
            plan["approval_status"] = "pending"
            return plan
        
        # Si es recommendation only, marcar como recomendación
        if autonomy_mode == AutonomyMode.RECOMMENDATION_ONLY:
            plan["is_recommendation"] = True
            return plan
        
        return plan
    
    def decide_optimization_action(
        self,
        metrics: Dict[str, Any],
        evaluation: Dict[str, Any],
        autonomy_mode: AutonomyMode
    ) -> Dict[str, Any]:
        """
        Decide qué acción de optimización tomar.
        
        Args:
            metrics: Métricas actuales
            evaluation: Evaluación de performance
            autonomy_mode: Modo de autonomía
        
        Returns:
            Decisión de optimización
        """
        self.logger.info(f"Decidiendo acción de optimización (autonomy: {autonomy_mode.value})")
        
        # Si no es full autonomous, solo recomendar
        if autonomy_mode != AutonomyMode.FULL_AUTONOMOUS:
            return {
                "action": "recommend",
                "recommendations": evaluation.get("recommendations", []),
                "requires_approval": autonomy_mode == AutonomyMode.APPROVAL_REQUIRED
            }
        
        # Full autonomous: decidir acción automáticamente
        performance_score = evaluation.get("performance_score", 50)
        issues = evaluation.get("issues", [])
        recommendations = evaluation.get("recommendations", [])
        
        # Lógica de decisión basada en performance
        if performance_score < 30:
            # Performance muy bajo: pausar y regenerar
            action = "pause_and_regenerate"
        elif performance_score < 60:
            # Performance bajo: ajustar presupuesto y audiencias
            action = "adjust_budget_and_targeting"
        elif any("CPA" in issue or "cost" in issue.lower() for issue in issues):
            # CPA alto: optimizar pujas
            action = "optimize_bids"
        else:
            # Performance aceptable: escalar ganadores
            action = "scale_winners"
        
        return {
            "action": action,
            "parameters": {
                "performance_score": performance_score,
                "issues": issues,
                "recommendations": recommendations
            },
            "autonomy_mode": autonomy_mode.value
        }

