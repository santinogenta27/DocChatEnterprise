"""
Agentes Autónomos que Aprenden
Basado en las ideas de Eric Schmidt sobre agentes que descubren, prueban y aprenden
"""

from __future__ import annotations

import time
import json
from typing import List, Dict, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import uuid

from langchain_core.language_models import BaseLanguageModel
from langchain_core.tools import BaseTool
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

from .config import AppConfig
from .long_context_manager import LongContextManager, ContextChunk


class AgentState(str, Enum):
    """Estados del agente."""
    IDLE = "idle"
    PERCEIVING = "perceiving"
    PLANNING = "planning"
    ACTING = "acting"
    OBSERVING = "observing"
    LEARNING = "learning"
    ERROR = "error"


@dataclass
class Hypothesis:
    """Hipótesis generada por el agente."""
    hypothesis_id: str
    description: str
    confidence: float  # 0-1
    test_plan: List[str]  # Pasos para probar
    created_at: float
    tested: bool = False
    test_results: Optional[Dict[str, Any]] = None
    validated: bool = False
    learned_insights: List[str] = field(default_factory=list)


@dataclass
class AgentAction:
    """Acción ejecutada por el agente."""
    action_id: str
    action_type: str  # "tool_call", "code_execution", "api_call", etc.
    tool_name: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    result: Optional[Any] = None
    success: bool = False
    error: Optional[str] = None
    timestamp: float = field(default_factory=time.time)


@dataclass
class AgentMemory:
    """Memoria del agente para aprendizaje."""
    agent_id: str
    successful_patterns: List[Dict[str, Any]] = field(default_factory=list)
    failed_patterns: List[Dict[str, Any]] = field(default_factory=list)
    learned_principles: List[str] = field(default_factory=list)
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    last_updated: float = field(default_factory=time.time)


class AutonomousAgent:
    """
    Agente autónomo que sigue el ciclo: Perceive → Plan → Act → Observe → Learn
    
    Basado en ChemCrow: descubre principios, prueba hipótesis y aprende.
    """
    
    def __init__(
        self,
        agent_id: str,
        config: AppConfig,
        llm: Optional[BaseLanguageModel] = None,
        tools: List[BaseTool] = None,
        context_manager: Optional[LongContextManager] = None
    ):
        self.agent_id = agent_id
        self.config = config
        self.llm = llm or self._create_llm()
        self.tools = tools or []
        self.context_manager = context_manager
        
        # Estado
        self.state = AgentState.IDLE
        self.current_task: Optional[str] = None
        self.hypotheses: List[Hypothesis] = []
        self.actions_history: List[AgentAction] = []
        self.memory = AgentMemory(agent_id=agent_id)
        
        # Prompts
        self.perception_prompt = ChatPromptTemplate.from_messages([
            ("system", """Eres un agente autónomo inteligente que descubre patrones y principios.
Tu tarea es analizar información y generar hipótesis sobre patrones, principios o insights.

Analiza la información proporcionada y genera hipótesis sobre:
1. Patrones que observas
2. Principios que podrían explicar estos patrones
3. Relaciones causales
4. Insights accionables

Responde en formato JSON con:
- "hypotheses": [{{"description": "...", "confidence": 0.0-1.0, "test_plan": ["paso1", "paso2"]}}]
- "insights": ["insight1", "insight2"]
- "questions": ["pregunta1", "pregunta2"]"""),
            ("human", "{input}")
        ])
        
        self.planning_prompt = ChatPromptTemplate.from_messages([
            ("system", """Eres un agente que planifica acciones para probar hipótesis.

Dada una hipótesis, genera un plan de acción detallado para probarla.
Cada paso debe ser ejecutable y verificable.

Responde en formato JSON con:
- "plan": [{{"step": 1, "action": "...", "tool": "...", "parameters": {{...}}, "expected_result": "..."}}]
- "validation_criteria": ["criterio1", "criterio2"]"""),
            ("human", "Hipótesis: {hypothesis}\n\nHerramientas disponibles: {tools}")
        ])
        
        self.learning_prompt = ChatPromptTemplate.from_messages([
            ("system", """Eres un agente que aprende de resultados.
            
Analiza los resultados de las pruebas y extrae:
1. Principios aprendidos
2. Patrones exitosos
3. Patrones que fallaron
4. Mejoras para futuras iteraciones
            
Responde en formato JSON con:
- "principles": ["principio1", "principio2"]
- "successful_patterns": [{{"pattern": "...", "context": "..."}}]
- "failed_patterns": [{{"pattern": "...", "reason": "..."}}]
- "improvements": ["mejora1", "mejora2"]"""),
            ("human", "Resultados: {results}\n\nHipótesis original: {hypothesis}")
        ])
    
    def _create_llm(self) -> BaseLanguageModel:
        """Crea el LLM según la configuración."""
        provider = getattr(self.config, 'ai_provider', 'openai')
        
        if provider == 'anthropic':
            return ChatAnthropic(
                model="claude-sonnet-4-20250514",
                temperature=0.7,
                max_tokens=4000
            )
        else:
            return ChatOpenAI(
                model="gpt-4-turbo-preview",
                temperature=0.7,
                max_tokens=4000
            )
    
    async def perceive(self, input_data: str) -> List[Hypothesis]:
        """
        Fase de percepción: analiza información y genera hipótesis.
        """
        self.state = AgentState.PERCEIVING
        
        try:
            # Obtener contexto si hay context manager
            context = ""
            if self.context_manager:
                context_text, _ = self.context_manager.get_context_for_prompt(
                    session_id=self.agent_id,
                    max_tokens=100_000
                )
                context = f"\n\nContexto disponible:\n{context_text[:50000]}"  # Limitar para no exceder
            
            # Generar hipótesis
            chain = self.perception_prompt | self.llm
            response = await chain.ainvoke({
                "input": f"{input_data}{context}"
            })
            
            # Parsear respuesta
            content = response.content
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0].strip()
            else:
                json_str = content
            
            try:
                data = json.loads(json_str)
            except json.JSONDecodeError:
                # Fallback: intentar extraer JSON del texto
                import re
                json_match = re.search(r'\{.*\}', json_str, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group())
                else:
                    data = {"hypotheses": [], "insights": []}
            
            # Crear objetos Hypothesis
            hypotheses = []
            for hyp_data in data.get("hypotheses", []):
                hypothesis = Hypothesis(
                    hypothesis_id=str(uuid.uuid4()),
                    description=hyp_data.get("description", ""),
                    confidence=hyp_data.get("confidence", 0.5),
                    test_plan=hyp_data.get("test_plan", []),
                    created_at=time.time()
                )
                hypotheses.append(hypothesis)
            
            self.hypotheses.extend(hypotheses)
            self.state = AgentState.IDLE
            
            return hypotheses
            
        except Exception as e:
            self.state = AgentState.ERROR
            print(f"❌ Error en perceive: {e}")
            return []
    
    async def plan(self, hypothesis: Hypothesis) -> List[Dict[str, Any]]:
        """
        Fase de planificación: genera plan para probar hipótesis.
        """
        self.state = AgentState.PLANNING
        
        try:
            tools_list = [tool.name for tool in self.tools] if self.tools else []
            
            chain = self.planning_prompt | self.llm
            response = await chain.ainvoke({
                "hypothesis": hypothesis.description,
                "tools": ", ".join(tools_list) if tools_list else "Ninguna herramienta disponible"
            })
            
            content = response.content
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
            else:
                json_str = content
            
            try:
                data = json.loads(json_str)
            except json.JSONDecodeError:
                import re
                json_match = re.search(r'\{.*\}', json_str, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group())
                else:
                    data = {"plan": []}
            
            plan = data.get("plan", [])
            hypothesis.test_plan = [step.get("action", "") for step in plan]
            
            self.state = AgentState.IDLE
            return plan
            
        except Exception as e:
            self.state = AgentState.ERROR
            print(f"❌ Error en plan: {e}")
            return []
    
    async def act(self, plan: List[Dict[str, Any]]) -> List[AgentAction]:
        """
        Fase de acción: ejecuta el plan.
        """
        self.state = AgentState.ACTING
        actions = []
        
        try:
            for step in plan:
                action_type = step.get("action", "").lower()
                tool_name = step.get("tool")
                parameters = step.get("parameters", {})
                
                action = AgentAction(
                    action_id=str(uuid.uuid4()),
                    action_type=action_type,
                    tool_name=tool_name,
                    parameters=parameters
                )
                
                # Ejecutar acción
                if tool_name and self.tools:
                    tool = next((t for t in self.tools if t.name == tool_name), None)
                    if tool:
                        try:
                            result = await tool.ainvoke(parameters)
                            action.result = result
                            action.success = True
                        except Exception as e:
                            action.error = str(e)
                            action.success = False
                    else:
                        action.error = f"Tool {tool_name} no encontrado"
                        action.success = False
                else:
                    # Acción sin tool (puede ser código, etc.)
                    action.result = "Acción planificada pero no ejecutada (requiere implementación)"
                    action.success = True
                
                actions.append(action)
                self.actions_history.append(action)
            
            self.state = AgentState.IDLE
            return actions
            
        except Exception as e:
            self.state = AgentState.ERROR
            print(f"❌ Error en act: {e}")
            return actions
    
    async def observe(self, actions: List[AgentAction], hypothesis: Hypothesis) -> Dict[str, Any]:
        """
        Fase de observación: analiza resultados de las acciones.
        """
        self.state = AgentState.OBSERVING
        
        results = {
            "actions_executed": len(actions),
            "successful_actions": sum(1 for a in actions if a.success),
            "failed_actions": sum(1 for a in actions if not a.success),
            "results": [{"action": a.action_type, "success": a.success, "result": str(a.result)[:500]} for a in actions],
            "errors": [a.error for a in actions if a.error]
        }
        
        hypothesis.tested = True
        hypothesis.test_results = results
        
        self.state = AgentState.IDLE
        return results
    
    async def learn(self, hypothesis: Hypothesis, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fase de aprendizaje: extrae principios y actualiza memoria.
        """
        self.state = AgentState.LEARNING
        
        try:
            chain = self.learning_prompt | self.llm
            response = await chain.ainvoke({
                "results": json.dumps(results, indent=2),
                "hypothesis": hypothesis.description
            })
            
            content = response.content
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
            else:
                json_str = content
            
            try:
                data = json.loads(json_str)
            except json.JSONDecodeError:
                import re
                json_match = re.search(r'\{.*\}', json_str, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group())
                else:
                    data = {}
            
            # Actualizar memoria
            principles = data.get("principles", [])
            self.memory.learned_principles.extend(principles)
            hypothesis.learned_insights = principles
            
            successful_patterns = data.get("successful_patterns", [])
            self.memory.successful_patterns.extend(successful_patterns)
            
            failed_patterns = data.get("failed_patterns", [])
            self.memory.failed_patterns.extend(failed_patterns)
            
            # Validar hipótesis
            success_rate = results.get("successful_actions", 0) / max(results.get("actions_executed", 1), 1)
            hypothesis.validated = success_rate > 0.7  # 70% de éxito
            
            self.memory.last_updated = time.time()
            self.state = AgentState.IDLE
            
            return {
                "principles_learned": len(principles),
                "hypothesis_validated": hypothesis.validated,
                "success_rate": success_rate,
                "insights": hypothesis.learned_insights
            }
            
        except Exception as e:
            self.state = AgentState.ERROR
            print(f"❌ Error en learn: {e}")
            return {}
    
    async def run_full_cycle(self, input_data: str) -> Dict[str, Any]:
        """
        Ejecuta el ciclo completo: Perceive → Plan → Act → Observe → Learn
        """
        print(f"🤖 [Agente {self.agent_id}] Iniciando ciclo completo...")
        
        # 1. Perceive
        print("🔍 [Agente] Fase 1: Percepción...")
        hypotheses = await self.perceive(input_data)
        
        if not hypotheses:
            return {"error": "No se generaron hipótesis"}
        
        # Tomar la hipótesis con mayor confianza
        best_hypothesis = max(hypotheses, key=lambda h: h.confidence)
        print(f"💡 [Agente] Hipótesis seleccionada: {best_hypothesis.description[:100]}...")
        
        # 2. Plan
        print("📋 [Agente] Fase 2: Planificación...")
        plan = await self.plan(best_hypothesis)
        
        if not plan:
            return {"error": "No se generó un plan"}
        
        # 3. Act
        print("⚡ [Agente] Fase 3: Acción...")
        actions = await self.act(plan)
        
        # 4. Observe
        print("👀 [Agente] Fase 4: Observación...")
        results = await self.observe(actions, best_hypothesis)
        
        # 5. Learn
        print("🧠 [Agente] Fase 5: Aprendizaje...")
        learning_results = await self.learn(best_hypothesis, results)
        
        return {
            "hypothesis": best_hypothesis.description,
            "hypothesis_validated": best_hypothesis.validated,
            "actions_executed": len(actions),
            "results": results,
            "learning": learning_results,
            "principles_learned": self.memory.learned_principles[-5:]  # Últimos 5
        }
    
    def get_memory_summary(self) -> Dict[str, Any]:
        """Obtiene resumen de la memoria del agente."""
        return {
            "agent_id": self.agent_id,
            "total_principles": len(self.memory.learned_principles),
            "successful_patterns": len(self.memory.successful_patterns),
            "failed_patterns": len(self.memory.failed_patterns),
            "recent_principles": self.memory.learned_principles[-10:],
            "state": self.state.value,
            "hypotheses_count": len(self.hypotheses),
            "actions_count": len(self.actions_history)
        }
