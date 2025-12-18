"""
Core Agent - Brain del sistema Top Ads
Motor de razonamiento basado en LLM con capacidad de planificación,
toma de decisiones, evaluación de performance y auto-corrección.
"""

from __future__ import annotations

from typing import List, Dict, Optional, Any
from langchain_core.language_models import BaseLanguageModel
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate

from ...config import AppConfig
from ..utils.logger import TopAdsLogger


class TopAdsCoreAgent:
    """
    Core Agent - El cerebro del sistema Top Ads.
    
    Responsabilidades:
    - Interpretar objetivos de negocio
    - Decidir tipo de campaña
    - Diseñar estructura publicitaria
    - Seleccionar audiencias
    - Evaluar performance
    - Decidir acciones correctivas
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
        
        # System prompt para el agente
        self.system_prompt = """Eres un experto en marketing publicitario y gestión de campañas digitales.
Tu objetivo es crear, optimizar y gestionar campañas publicitarias de forma autónoma.

Capacidades:
- Analizar objetivos de negocio y traducirlos a estrategias publicitarias
- Diseñar estructuras de campaña optimizadas
- Seleccionar audiencias efectivas
- Evaluar performance y tomar decisiones de optimización
- Aprender de resultados y mejorar continuamente

Siempre justifica tus decisiones con razonamiento claro."""
    
    def reason_about_objective(
        self,
        business_objective: str,
        budget: float,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Razona sobre el objetivo de negocio y genera estrategia inicial.
        
        Args:
            business_objective: Objetivo de negocio (conversions, leads, traffic, etc.)
            budget: Presupuesto disponible
            context: Contexto adicional (audiencia, producto, etc.)
        
        Returns:
            Estrategia razonada con justificación
        """
        prompt = f"""Analiza el siguiente objetivo de negocio y genera una estrategia publicitaria:

Objetivo: {business_objective}
Presupuesto: ${budget}
Contexto: {context or "N/A"}

Genera una estrategia que incluya:
1. Tipo de campaña recomendado
2. Objetivo de optimización
3. Estrategia de audiencia
4. Distribución de presupuesto
5. Justificación de cada decisión

Responde en formato JSON con las siguientes claves:
- campaign_type
- optimization_objective
- audience_strategy
- budget_allocation
- reasoning"""
        
        try:
            response = self.llm.invoke([
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=prompt)
            ])
            
            content = response.content if hasattr(response, 'content') else str(response)
            
            # Parsear JSON de la respuesta
            import re
            import json
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                strategy = json.loads(json_match.group())
            else:
                # Fallback: crear estrategia básica
                strategy = {
                    "campaign_type": "conversion",
                    "optimization_objective": business_objective,
                    "audience_strategy": "broad",
                    "budget_allocation": {"daily": budget},
                    "reasoning": content
                }
            
            self.logger.info(f"Estrategia generada para objetivo: {business_objective}")
            return strategy
            
        except Exception as e:
            self.logger.error(f"Error razonando objetivo: {e}")
            # Estrategia por defecto
            return {
                "campaign_type": "conversion",
                "optimization_objective": business_objective,
                "audience_strategy": "broad",
                "budget_allocation": {"daily": budget},
                "reasoning": f"Estrategia por defecto debido a error: {e}"
            }
    
    def evaluate_performance(
        self,
        metrics: Dict[str, Any],
        goals: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Evalúa el performance de una campaña comparado con objetivos.
        
        Args:
            metrics: Métricas actuales (CTR, CPA, ROAS, etc.)
            goals: Objetivos esperados
        
        Returns:
            Evaluación con recomendaciones
        """
        prompt = f"""Evalúa el performance de esta campaña:

Métricas actuales:
{json.dumps(metrics, indent=2)}

Objetivos:
{json.dumps(goals, indent=2)}

Analiza:
1. ¿Se están cumpliendo los objetivos?
2. ¿Qué métricas están por debajo/encima de lo esperado?
3. ¿Qué acciones correctivas recomiendas?
4. ¿Qué está funcionando bien?

Responde en formato JSON con:
- performance_score (0-100)
- goals_met (lista de objetivos cumplidos)
- issues (lista de problemas identificados)
- recommendations (lista de acciones recomendadas)
- strengths (qué está funcionando bien)"""
        
        try:
            response = self.llm.invoke([
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=prompt)
            ])
            
            content = response.content if hasattr(response, 'content') else str(response)
            
            import re
            import json
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                evaluation = json.loads(json_match.group())
            else:
                evaluation = {
                    "performance_score": 50,
                    "goals_met": [],
                    "issues": ["No se pudo evaluar automáticamente"],
                    "recommendations": ["Revisar métricas manualmente"],
                    "strengths": []
                }
            
            return evaluation
            
        except Exception as e:
            self.logger.error(f"Error evaluando performance: {e}")
            return {
                "performance_score": 0,
                "goals_met": [],
                "issues": [f"Error en evaluación: {e}"],
                "recommendations": ["Revisar manualmente"],
                "strengths": []
            }
    
    def decide_action(
        self,
        situation: Dict[str, Any],
        available_actions: List[str]
    ) -> Dict[str, Any]:
        """
        Decide qué acción tomar basado en la situación actual.
        
        Args:
            situation: Situación actual (métricas, estado, etc.)
            available_actions: Lista de acciones disponibles
        
        Returns:
            Decisión con acción seleccionada y justificación
        """
        prompt = f"""Decide qué acción tomar en esta situación:

Situación:
{json.dumps(situation, indent=2)}

Acciones disponibles:
{', '.join(available_actions)}

Analiza la situación y decide:
1. ¿Qué acción es la más apropiada?
2. ¿Por qué?
3. ¿Qué parámetros necesita esta acción?

Responde en formato JSON con:
- action (nombre de la acción)
- parameters (parámetros necesarios)
- reasoning (justificación)
- expected_outcome (resultado esperado)"""
        
        try:
            response = self.llm.invoke([
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=prompt)
            ])
            
            content = response.content if hasattr(response, 'content') else str(response)
            
            import re
            import json
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                decision = json.loads(json_match.group())
            else:
                decision = {
                    "action": available_actions[0] if available_actions else "wait",
                    "parameters": {},
                    "reasoning": "Decisión por defecto",
                    "expected_outcome": "Sin cambios"
                }
            
            return decision
            
        except Exception as e:
            self.logger.error(f"Error decidiendo acción: {e}")
            return {
                "action": "wait",
                "parameters": {},
                "reasoning": f"Error en decisión: {e}",
                "expected_outcome": "Sin cambios"
            }

