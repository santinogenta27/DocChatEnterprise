"""
Chain of Thought Reasoning - Razonamiento paso a paso
Guía procesos complejos paso a paso, recordando el contexto completo
Mejora la experiencia de usuario en conversaciones multi-turno
"""

from __future__ import annotations

import json
import time
import uuid
from typing import List, Dict, Optional, Any, Callable
from dataclasses import dataclass, field, asdict
from pathlib import Path
from enum import Enum

from langchain_core.language_models import BaseLanguageModel
from langchain_core.prompts import ChatPromptTemplate

from .config import AppConfig


class ReasoningStepType(str, Enum):
    """Tipo de paso de razonamiento."""
    OBSERVATION = "observation"
    ANALYSIS = "analysis"
    HYPOTHESIS = "hypothesis"
    VERIFICATION = "verification"
    CONCLUSION = "conclusion"
    ACTION = "action"


@dataclass
class ReasoningStep:
    """Un paso en la cadena de razonamiento."""
    step_id: str
    step_type: ReasoningStepType
    content: str  # Contenido del paso
    reasoning: str  # Razonamiento detrás del paso
    confidence: float = 0.0  # Confianza en este paso
    dependencies: List[str] = field(default_factory=list)  # IDs de pasos de los que depende
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ThoughtChain:
    """Una cadena completa de razonamiento."""
    chain_id: str
    query: str  # Consulta original
    steps: List[ReasoningStep]  # Pasos de razonamiento
    final_answer: Optional[str] = None
    status: str = "in_progress"  # "in_progress", "completed", "failed"
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class ChainOfThoughtReasoner:
    """
    Sistema de razonamiento paso a paso (Chain of Thought).
    
    Características:
    - Guía procesos complejos paso a paso
    - Mantiene contexto completo de razonamiento
    - Mejora la experiencia de usuario
    - Diferencia competitiva
    - Relativamente simple de implementar
    """
    
    def __init__(
        self,
        config: AppConfig,
        llm: Optional[BaseLanguageModel] = None
    ):
        self.config = config
        self.llm = llm
        
        # Cadenas activas
        self.active_chains: Dict[str, ThoughtChain] = {}
        
        # Historial de cadenas completadas
        self.completed_chains: List[ThoughtChain] = []
        
        # Directorio para persistencia
        self.storage_dir = Path(config.memory_dir) / "chain_of_thought"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Cargar historial
        self._load_history()
        
        # Prompt para generar pasos de razonamiento
        self.reasoning_prompt = ChatPromptTemplate.from_messages([
            ("system", """Eres un razonador experto que guía procesos complejos paso a paso.

Tu tarea es descomponer un problema o consulta en pasos de razonamiento claros y lógicos.

Cada paso debe:
1. Ser específico y accionable
2. Construir sobre pasos anteriores
3. Tener un propósito claro
4. Llevar hacia la solución final

Responde en JSON:
{{
    "steps": [
        {{
            "step_type": "observation|analysis|hypothesis|verification|conclusion|action",
            "content": "descripción del paso",
            "reasoning": "por qué este paso es necesario",
            "confidence": 0.0,
            "depends_on": []
        }}
    ],
    "reasoning": "razonamiento general sobre el enfoque"
}}"""),
            ("human", """Consulta: {query}

Contexto anterior: {previous_context}

Genera los siguientes pasos de razonamiento para resolver esta consulta.""")
        ])
    
    def _load_history(self):
        """Carga historial de cadenas completadas."""
        history_file = self.storage_dir / "completed_chains.json"
        if history_file.exists():
            try:
                with open(history_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for chain_data in data.get("chains", [])[-100:]:  # Últimas 100
                        chain = ThoughtChain(**chain_data)
                        # Reconstruir steps
                        chain.steps = [
                            ReasoningStep(**s_data) for s_data in chain_data.get("steps", [])
                        ]
                        self.completed_chains.append(chain)
                    print(f"✅ [Chain of Thought] {len(self.completed_chains)} cadenas cargadas")
            except Exception as e:
                print(f"⚠️ [Chain of Thought] Error cargando historial: {e}")
    
    def _save_history(self):
        """Guarda historial de cadenas completadas."""
        history_file = self.storage_dir / "completed_chains.json"
        try:
            with open(history_file, "w", encoding="utf-8") as f:
                json.dump({
                    "chains": [
                        {
                            **asdict(chain),
                            "steps": [asdict(step) for step in chain.steps]
                        }
                        for chain in self.completed_chains[-100:]
                    ]
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️ [Chain of Thought] Error guardando historial: {e}")
    
    def create_chain(self, query: str, context: str = "") -> str:
        """
        Crea una nueva cadena de razonamiento.
        
        Returns:
            chain_id: ID de la cadena creada
        """
        chain_id = str(uuid.uuid4())
        
        chain = ThoughtChain(
            chain_id=chain_id,
            query=query,
            steps=[],
            metadata={"initial_context": context}
        )
        
        self.active_chains[chain_id] = chain
        
        print(f"🔗 [Chain of Thought] Cadena creada para: {query[:50]}...")
        
        return chain_id
    
    async def add_reasoning_steps(
        self,
        chain_id: str,
        previous_context: str = ""
    ) -> List[ReasoningStep]:
        """
        Agrega pasos de razonamiento a una cadena.
        
        Returns:
            Lista de pasos generados
        """
        if chain_id not in self.active_chains:
            raise ValueError(f"Cadena {chain_id} no encontrada")
        
        chain = self.active_chains[chain_id]
        
        # Generar pasos usando LLM
        steps_data = await self._generate_steps(chain.query, previous_context, chain.steps)
        
        # Crear objetos ReasoningStep
        new_steps = []
        for step_data in steps_data.get("steps", []):
            step = ReasoningStep(
                step_id=str(uuid.uuid4()),
                step_type=ReasoningStepType(step_data.get("step_type", "analysis")),
                content=step_data.get("content", ""),
                reasoning=step_data.get("reasoning", ""),
                confidence=step_data.get("confidence", 0.5),
                dependencies=step_data.get("depends_on", [])
            )
            chain.steps.append(step)
            new_steps.append(step)
        
        print(f"✅ [Chain of Thought] {len(new_steps)} pasos agregados a la cadena")
        
        return new_steps
    
    async def _generate_steps(
        self,
        query: str,
        previous_context: str,
        existing_steps: List[ReasoningStep]
    ) -> Dict[str, Any]:
        """Genera pasos de razonamiento usando LLM."""
        if not self.llm:
            # Fallback: pasos básicos
            return {
                "steps": [
                    {
                        "step_type": "observation",
                        "content": f"Observar: {query}",
                        "reasoning": "Primer paso de observación",
                        "confidence": 0.5,
                        "depends_on": []
                    },
                    {
                        "step_type": "analysis",
                        "content": "Analizar la información disponible",
                        "reasoning": "Segundo paso de análisis",
                        "confidence": 0.5,
                        "depends_on": []
                    }
                ],
                "reasoning": "Razonamiento básico"
            }
        
        # Construir contexto de pasos anteriores
        previous_steps_context = ""
        if existing_steps:
            previous_steps_context = "\n".join([
                f"Paso {i+1} ({step.step_type.value}): {step.content}"
                for i, step in enumerate(existing_steps[-5:])  # Últimos 5 pasos
            ])
        
        prompt = self.reasoning_prompt.format_messages(
            query=query,
            previous_context=f"{previous_context}\n\nPasos anteriores:\n{previous_steps_context}"
        )
        
        try:
            response = await self.llm.ainvoke(prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            
            # Parsear JSON con manejo robusto de errores
            json_str = None
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                # Intentar extraer de cualquier bloque de código
                parts = content.split("```")
                if len(parts) > 1:
                    json_str = parts[1].strip()
                    if json_str.startswith("json"):
                        json_str = json_str[4:].strip()
            else:
                json_str = content.strip()
            
            # Limpiar el JSON string
            if json_str:
                # Eliminar espacios y saltos de línea al inicio
                json_str = json_str.strip()
                
                # Si comienza con salto de línea o espacios, limpiar
                while json_str.startswith('\n') or json_str.startswith(' '):
                    json_str = json_str.lstrip()
                
                # Eliminar líneas que no sean JSON válido
                lines = json_str.split('\n')
                json_lines = []
                in_json = False
                brace_count = 0
                for line in lines:
                    line_stripped = line.strip()
                    if not line_stripped:
                        continue
                    
                    # Detectar inicio de JSON
                    if line_stripped.startswith('{') or line_stripped.startswith('['):
                        in_json = True
                        brace_count = line_stripped.count('{') - line_stripped.count('}')
                    
                    if in_json:
                        json_lines.append(line)
                        brace_count += line_stripped.count('{') - line_stripped.count('}')
                        # Si cerramos todas las llaves, terminamos
                        if brace_count <= 0 and (line_stripped.endswith('}') or line_stripped.endswith(']')):
                            break
                
                json_str = '\n'.join(json_lines).strip()
            
            if not json_str:
                raise ValueError("No se pudo extraer JSON de la respuesta")
            
            # Intentar parsear
            try:
                data = json.loads(json_str)
            except json.JSONDecodeError as je:
                # Intentar extraer JSON del texto si falla
                import re
                # Buscar objeto JSON entre llaves
                json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', json_str, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                    data = json.loads(json_str)
                else:
                    raise je
            
            # Validar estructura
            if not isinstance(data, dict):
                raise ValueError("El JSON no es un objeto")
            
            if "steps" not in data:
                data["steps"] = []
            
            return data
            
        except Exception as e:
            print(f"⚠️ [Chain of Thought] Error generando pasos: {e}")
            print(f"   Contenido recibido: {content[:200] if 'content' in locals() else 'N/A'}")
            # Retornar estructura básica en caso de error
            return {
                "steps": [
                    {
                        "step_type": "analysis",
                        "content": f"Analizar: {query[:100]}",
                        "reasoning": "Análisis básico debido a error en generación",
                        "confidence": 0.5,
                        "depends_on": []
                    }
                ],
                "reasoning": f"Error en generación: {str(e)[:100]}"
            }
    
    def execute_step(
        self,
        chain_id: str,
        step_id: str,
        result: Any,
        success: bool = True
    ):
        """Ejecuta un paso y registra el resultado."""
        if chain_id not in self.active_chains:
            return
        
        chain = self.active_chains[chain_id]
        step = next((s for s in chain.steps if s.step_id == step_id), None)
        
        if not step:
            return
        
        step.metadata["result"] = result
        step.metadata["success"] = success
        step.metadata["executed_at"] = time.time()
    
    def complete_chain(
        self,
        chain_id: str,
        final_answer: str,
        success: bool = True
    ):
        """Completa una cadena de razonamiento."""
        if chain_id not in self.active_chains:
            return
        
        chain = self.active_chains[chain_id]
        chain.final_answer = final_answer
        chain.status = "completed" if success else "failed"
        chain.completed_at = time.time()
        
        # Mover a completadas
        self.completed_chains.append(chain)
        del self.active_chains[chain_id]
        
        # Guardar periódicamente
        if len(self.completed_chains) % 10 == 0:
            self._save_history()
        
        print(f"✅ [Chain of Thought] Cadena completada: {chain.query[:50]}...")
    
    def get_chain(self, chain_id: str) -> Optional[ThoughtChain]:
        """Obtiene una cadena por ID."""
        if chain_id in self.active_chains:
            return self.active_chains[chain_id]
        
        # Buscar en completadas
        return next((c for c in self.completed_chains if c.chain_id == chain_id), None)
    
    def format_chain_for_display(self, chain_id: str) -> str:
        """
        Formatea una cadena para visualización.
        
        Returns:
            Cadena formateada legible
        """
        chain = self.get_chain(chain_id)
        if not chain:
            return f"Cadena {chain_id} no encontrada"
        
        output = f"🔗 CADENA DE RAZONAMIENTO\n"
        output += f"{'='*60}\n\n"
        output += f"Consulta: {chain.query}\n"
        output += f"Estado: {chain.status}\n"
        output += f"Pasos: {len(chain.steps)}\n\n"
        
        output += f"📋 PASOS:\n"
        output += f"{'-'*60}\n"
        
        for i, step in enumerate(chain.steps, 1):
            output += f"\n{i}. [{step.step_type.value.upper()}] {step.content}\n"
            output += f"   Razonamiento: {step.reasoning}\n"
            output += f"   Confianza: {step.confidence*100:.1f}%\n"
            
            if step.metadata.get("result"):
                output += f"   Resultado: {step.metadata['result']}\n"
            
            if step.dependencies:
                output += f"   Depende de: {', '.join(step.dependencies)}\n"
        
        if chain.final_answer:
            output += f"\n\n✅ RESPUESTA FINAL:\n"
            output += f"{chain.final_answer}\n"
        
        return output
    
    def get_statistics(self) -> Dict[str, Any]:
        """Obtiene estadísticas de razonamiento."""
        total_chains = len(self.active_chains) + len(self.completed_chains)
        completed_count = len(self.completed_chains)
        
        total_steps = sum(len(c.steps) for c in self.active_chains.values())
        total_steps += sum(len(c.steps) for c in self.completed_chains)
        
        return {
            "active_chains": len(self.active_chains),
            "completed_chains": completed_count,
            "total_chains": total_chains,
            "total_steps": total_steps,
            "average_steps_per_chain": (
                total_steps / total_chains if total_chains > 0 else 0
            ),
            "completion_rate": (
                completed_count / total_chains * 100 if total_chains > 0 else 0
            )
        }
