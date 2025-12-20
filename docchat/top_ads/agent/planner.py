"""
Campaign Planner - Planifica estrategias de campaña publicitaria
"""

from __future__ import annotations

from typing import List, Dict, Optional, Any
from langchain_core.language_models import BaseLanguageModel
from langchain_core.messages import SystemMessage, HumanMessage
import json
import re

from ...config import AppConfig
from ..utils.logger import TopAdsLogger


class CampaignPlanner:
    """
    Planificador de campañas publicitarias.
    
    Responsabilidades:
    - Planear estructura de campaña
    - Definir ad sets y targeting
    - Asignar presupuesto
    - Seleccionar creativos por ad set
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
    
    def plan_campaign(
        self,
        business_objective: str,
        budget: float,
        creatives: List[Dict[str, Any]],
        target_audience: Optional[Dict[str, Any]] = None,
        force_broad_targeting: bool = False
    ) -> Dict[str, Any]:
        """
        Planifica una campaña completa.
        
        Args:
            business_objective: Objetivo de negocio
            budget: Presupuesto total
            creatives: Lista de creativos disponibles
            target_audience: Audiencia objetivo (opcional)
            force_broad_targeting: Si True, fuerza broad targeting (modo FULL_AUTONOMOUS)
        
        Returns:
            Plan de campaña con estructura completa
        """
        targeting_note = "Broad (IA expandirá automáticamente)" if force_broad_targeting else (target_audience or "Broad")
        self.logger.info(f"Planificando campaña: objetivo={business_objective}, budget=${budget}, broad_targeting={force_broad_targeting}")
        
        prompt = f"""Planifica una campaña publicitaria completa:

Objetivo: {business_objective}
Presupuesto total: ${budget}
Número de creativos: {len(creatives)}
Audiencia objetivo: {targeting_note}
{"⚠️ IMPORTANTE: Usar BROAD TARGETING únicamente. La IA expandirá la audiencia automáticamente." if force_broad_targeting else ""}

Crea un plan que incluya:

1. Estructura de campaña:
   - Número de ad sets recomendados
   - Objetivo de optimización por ad set
   - Presupuesto por ad set

2. Estrategia de audiencia:
   {"- SOLO BROAD TARGETING (edad 18-65, todos los géneros, sin intereses/behaviors específicos)" if force_broad_targeting else "- Tipos de audiencia (broad, interest-based, lookalike, retargeting)"}
   {"- La IA expandirá automáticamente la audiencia basándose en performance" if force_broad_targeting else "- Segmentación demográfica"}
   {"- NO incluir intereses o comportamientos detallados" if force_broad_targeting else "- Intereses y comportamientos"}

3. Asignación de creativos:
   - Qué creativos usar en cada ad set
   - Número de ads por ad set

4. Estrategia de testing:
   - Qué variantes probar
   - Criterios de éxito

Responde en formato JSON con esta estructura:
{{
    "objective": "...",
    "ad_sets": [
        {{
            "name": "...",
            "budget": ...,
            "optimization_goal": "...",
            "targeting": {{...}},
            "ads": [
                {{
                    "name": "...",
                    "creative_index": ...,
                    "format": "..."
                }}
            ]
        }}
    ],
    "reasoning": "..."
}}"""
        
        try:
            response = self.llm.invoke([
                SystemMessage(content="Eres un experto planificador de campañas publicitarias."),
                HumanMessage(content=prompt)
            ])
            
            content = response.content if hasattr(response, 'content') else str(response)
            
            # Parsear JSON
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                plan = json.loads(json_match.group())
            else:
                # Plan por defecto
                plan = self._create_default_plan(business_objective, budget, creatives, force_broad_targeting)
            
            self.logger.info(f"Plan de campaña generado: {len(plan.get('ad_sets', []))} ad sets")
            return plan
            
        except Exception as e:
            self.logger.error(f"Error planificando campaña: {e}")
            return self._create_default_plan(business_objective, budget, creatives, force_broad_targeting)
    
    def _create_default_plan(
        self,
        business_objective: str,
        budget: float,
        creatives: List[Dict[str, Any]],
        force_broad_targeting: bool = False
    ) -> Dict[str, Any]:
        """Crea un plan por defecto si falla la generación con LLM."""
        # Si force_broad_targeting, usar solo 1-2 ad sets con broad targeting
        if force_broad_targeting:
            budget_per_ad_set = budget / 2
            
            plan = {
                "objective": business_objective,
                "ad_sets": [
                    {
                        "name": "Broad Audience - AI Expanded",
                        "budget": budget_per_ad_set,
                        "optimization_goal": business_objective,
                        "targeting": {
                            "age_min": 18,
                            "age_max": 65,
                            "genders": [1, 2],  # All genders
                            "geo_locations": {"countries": ["US"]},
                            "interests": [],
                            "behaviors": [],
                            "targeting_type": "broad",
                            "advantage_plus_audience": True,
                            "ai_expansion": True
                        },
                        "ads": [
                            {
                                "name": f"Ad {i+1}",
                                "creative_index": i % len(creatives),
                                "format": "single_image"
                            }
                            for i in range(min(5, len(creatives)))
                        ]
                    },
                    {
                        "name": "Broad Audience - AI Expanded 2",
                        "budget": budget_per_ad_set,
                        "optimization_goal": business_objective,
                        "targeting": {
                            "age_min": 18,
                            "age_max": 65,
                            "genders": [1, 2],
                            "geo_locations": {"countries": ["US"]},
                            "interests": [],
                            "behaviors": [],
                            "targeting_type": "broad",
                            "advantage_plus_audience": True,
                            "ai_expansion": True
                        },
                        "ads": [
                            {
                                "name": f"Ad {i+1}",
                                "creative_index": (i + 5) % len(creatives),
                                "format": "single_image"
                            }
                            for i in range(min(5, len(creatives)))
                        ]
                    }
                ],
                "reasoning": "Plan por defecto con broad targeting forzado (modo FULL_AUTONOMOUS). IA expandirá audiencias automáticamente.",
                "targeting_strategy": "broad_ai_expanded"
            }
        else:
            # Plan normal con múltiples estrategias
            budget_per_ad_set = budget / 3
            
            plan = {
                "objective": business_objective,
                "ad_sets": [
                    {
                        "name": "Broad Audience",
                        "budget": budget_per_ad_set,
                        "optimization_goal": business_objective,
                        "targeting": {
                            "age_min": 18,
                            "age_max": 65,
                            "genders": [1, 2],  # All genders
                            "geo_locations": {"countries": ["US"]}
                        },
                        "ads": [
                            {
                                "name": f"Ad {i+1}",
                                "creative_index": i % len(creatives),
                                "format": "single_image"
                            }
                            for i in range(min(3, len(creatives)))
                        ]
                    },
                    {
                        "name": "Interest-Based Audience",
                        "budget": budget_per_ad_set,
                        "optimization_goal": business_objective,
                        "targeting": {
                            "age_min": 25,
                            "age_max": 55,
                            "interests": [],
                            "behaviors": []
                        },
                        "ads": [
                            {
                                "name": f"Ad {i+1}",
                                "creative_index": (i + 3) % len(creatives),
                                "format": "single_image"
                            }
                            for i in range(min(3, len(creatives)))
                        ]
                    },
                    {
                        "name": "Retargeting",
                        "budget": budget_per_ad_set,
                        "optimization_goal": business_objective,
                        "targeting": {
                            "custom_audiences": [],
                            "retargeting": True
                        },
                        "ads": [
                            {
                                "name": f"Ad {i+1}",
                                "creative_index": (i + 6) % len(creatives),
                                "format": "single_image"
                            }
                            for i in range(min(3, len(creatives)))
                        ]
                    }
                ],
                "reasoning": "Plan por defecto con 3 ad sets: Broad, Interest-Based, Retargeting"
            }
        
        return plan













