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
        
        Similar a Meta Ads Manager 2026: elimina controles manuales en modo autónomo,
        forzando broad targeting y optimización por IA.
        
        Args:
            plan: Plan de campaña generado por el planner
            autonomy_mode: Modo de autonomía
        
        Returns:
            Estructura de campaña final con decisiones aplicadas
        """
        self.logger.info(f"Decidiendo estructura de campaña (autonomy: {autonomy_mode.value})")
        
        # Si es full autonomous, forzar broad targeting y eliminar controles manuales
        if autonomy_mode == AutonomyMode.FULL_AUTONOMOUS:
            plan = self._force_broad_targeting(plan)
            plan["autonomy_mode"] = "full_autonomous"
            plan["manual_controls_removed"] = True
            self.logger.info("Modo FULL_AUTONOMOUS: Broad targeting forzado, controles manuales eliminados")
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
    
    def _force_broad_targeting(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fuerza broad targeting en todos los ad sets, eliminando targeting manual detallado.
        
        Similar a Meta's Advantage+ Audience: permite que la IA expanda audiencias
        automáticamente más allá de los parámetros básicos.
        
        Args:
            plan: Plan de campaña original
        
        Returns:
            Plan modificado con broad targeting forzado
        """
        modified_plan = plan.copy()
        
        # Modificar cada ad set para usar broad targeting
        if "ad_sets" in modified_plan:
            for ad_set in modified_plan["ad_sets"]:
                # Crear targeting broad (solo parámetros básicos, sin intereses/behaviors detallados)
                broad_targeting = {
                    "age_min": 18,
                    "age_max": 65,
                    "genders": [1, 2],  # All genders
                    "geo_locations": {
                        "countries": ["US"]  # Por defecto, se puede expandir
                    },
                    # Eliminar targeting detallado
                    "interests": [],  # Vacío - IA decidirá
                    "behaviors": [],  # Vacío - IA decidirá
                    "custom_audiences": [],  # Vacío - IA decidirá
                    "lookalike_audiences": [],  # Vacío - IA decidirá
                    # Marcar como broad targeting
                    "targeting_type": "broad",
                    "advantage_plus_audience": True,  # Similar a Meta's Advantage+ Audience
                    "ai_expansion": True  # Permitir expansión por IA
                }
                
                # Si había targeting manual, guardarlo como referencia pero no usarlo
                if "targeting" in ad_set:
                    original_targeting = ad_set["targeting"]
                    ad_set["original_targeting"] = original_targeting  # Guardar como referencia
                    self.logger.info(f"Targeting manual guardado como referencia para {ad_set.get('name', 'ad_set')}")
                
                # Aplicar broad targeting
                ad_set["targeting"] = broad_targeting
                ad_set["targeting_notes"] = "Broad targeting forzado por modo FULL_AUTONOMOUS. IA expandirá audiencia automáticamente."
        
        modified_plan["targeting_strategy"] = "broad_ai_expanded"
        modified_plan["manual_targeting_removed"] = True
        
        return modified_plan
    
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

