"""
Path-dependent Reasoning - Razonamiento dependiente del camino
Prueba diferentes enfoques y aprende qué funciona mejor
"""

from __future__ import annotations

import json
import time
import uuid
from typing import List, Dict, Optional, Any, Callable
from dataclasses import dataclass, field
from pathlib import Path

from langchain_core.language_models import BaseLanguageModel
from langchain_core.prompts import ChatPromptTemplate

from .config import AppConfig


@dataclass
class ReasoningPath:
    """Un camino de razonamiento probado."""
    path_id: str
    approach: str  # Enfoque probado
    steps: List[str]  # Pasos del camino
    result: Optional[Any] = None
    success: bool = False
    execution_time: float = 0.0
    confidence: float = 0.0
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


class PathDependentReasoner:
    """
    Sistema de razonamiento que prueba diferentes enfoques y aprende qué funciona mejor.
    
    Características:
    - Prueba múltiples enfoques para el mismo problema
    - Aprende qué enfoques funcionan mejor
    - Reutiliza enfoques exitosos
    - Evita enfoques que fallan
    """
    
    def __init__(
        self,
        config: AppConfig,
        llm: Optional[BaseLanguageModel] = None,
        max_paths: int = 5
    ):
        self.config = config
        self.llm = llm
        self.max_paths = max_paths
        
        # Historial de caminos
        self.paths: Dict[str, List[ReasoningPath]] = {}  # Por problema
        
        # Aprendizaje de qué funciona
        self.approach_effectiveness: Dict[str, Dict[str, float]] = {}  # approach -> {task_type: success_rate}
        
        # Directorio para persistencia
        self.storage_dir = Path(config.memory_dir) / "path_dependent_reasoning"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Cargar aprendizaje previo
        self._load_learning_data()
        
        # Prompt para generar enfoques
        self.approach_generation_prompt = ChatPromptTemplate.from_messages([
            ("system", """Eres un razonador que genera diferentes enfoques para resolver problemas.

Para un problema dado, genera múltiples enfoques diferentes, cada uno con una estrategia única.

Responde en JSON:
{
    "approaches": [
        {
            "approach": "nombre del enfoque",
            "description": "descripción del enfoque",
            "strategy": "estrategia específica",
            "expected_steps": ["paso1", "paso2", ...],
            "confidence": 0.0-1.0
        }
    ],
    "reasoning": "por qué estos enfoques podrían funcionar"
}"""),
            ("human", """Problema: {problem}

Contexto: {context}

Genera {num_approaches} enfoques diferentes para resolver este problema.""")
        ])
    
    def _load_learning_data(self):
        """Carga datos de aprendizaje previo."""
        learning_file = self.storage_dir / "approach_effectiveness.json"
        if learning_file.exists():
            try:
                with open(learning_file, "r", encoding="utf-8") as f:
                    self.approach_effectiveness = json.load(f)
                print(f"✅ [Path Dependent Reasoning] Aprendizaje cargado")
            except Exception as e:
                print(f"⚠️ [Path Dependent Reasoning] Error cargando aprendizaje: {e}")
    
    def _save_learning_data(self):
        """Guarda datos de aprendizaje."""
        learning_file = self.storage_dir / "approach_effectiveness.json"
        try:
            with open(learning_file, "w", encoding="utf-8") as f:
                json.dump(self.approach_effectiveness, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️ [Path Dependent Reasoning] Error guardando aprendizaje: {e}")
    
    async def reason_with_multiple_paths(
        self,
        problem: str,
        context: str = "",
        task_type: str = "general",
        executor: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Razona sobre un problema probando múltiples caminos.
        
        Returns:
            Resultado con el mejor camino encontrado
        """
        problem_key = problem[:100]  # Limitar longitud
        
        print(f"🛤️ [Path Dependent Reasoning] Probando múltiples caminos para: {problem[:50]}...")
        
        # Generar enfoques posibles
        approaches = await self._generate_approaches(
            problem=problem,
            context=context,
            num_approaches=self.max_paths
        )
        
        # Si hay aprendizaje previo, priorizar enfoques exitosos
        if task_type in self.approach_effectiveness:
            approaches = self._prioritize_by_learning(approaches, task_type)
        
        # Probar cada enfoque
        paths = []
        best_path = None
        best_result = None
        
        for approach_data in approaches:
            approach = approach_data.get("approach", "")
            description = approach_data.get("description", "")
            strategy = approach_data.get("strategy", "")
            expected_steps = approach_data.get("expected_steps", [])
            confidence = approach_data.get("confidence", 0.5)
            
            # Crear camino
            path = ReasoningPath(
                path_id=str(uuid.uuid4()),
                approach=approach,
                steps=expected_steps,
                confidence=confidence,
                metadata={
                    "description": description,
                    "strategy": strategy
                }
            )
            
            # Ejecutar camino
            start_time = time.time()
            try:
                if executor:
                    result = await executor(approach, strategy, expected_steps, context)
                else:
                    result = await self._simulate_path(approach, expected_steps, context)
                
                path.execution_time = time.time() - start_time
                path.result = result
                path.success = True
                
                # Si este es el mejor resultado hasta ahora
                if best_result is None or confidence > (best_path.confidence if best_path else 0):
                    best_path = path
                    best_result = result
                    
            except Exception as e:
                path.execution_time = time.time() - start_time
                path.success = False
                path.metadata["error"] = str(e)
            
            paths.append(path)
        
        # Guardar caminos probados
        if problem_key not in self.paths:
            self.paths[problem_key] = []
        self.paths[problem_key].extend(paths)
        
        # Aprender de los resultados
        await self._learn_from_paths(paths, task_type)
        
        return {
            "problem": problem,
            "paths_tested": len(paths),
            "successful_paths": sum(1 for p in paths if p.success),
            "best_path": {
                "approach": best_path.approach if best_path else None,
                "result": best_result,
                "confidence": best_path.confidence if best_path else 0.0
            },
            "all_paths": [
                {
                    "approach": p.approach,
                    "success": p.success,
                    "confidence": p.confidence,
                    "execution_time": p.execution_time
                }
                for p in paths
            ]
        }
    
    async def _generate_approaches(
        self,
        problem: str,
        context: str,
        num_approaches: int
    ) -> List[Dict[str, Any]]:
        """Genera diferentes enfoques usando LLM."""
        if not self.llm:
            # Fallback: enfoques genéricos
            return [
                {
                    "approach": "Análisis directo",
                    "description": "Enfoque directo al problema",
                    "strategy": "Analizar y resolver directamente",
                    "expected_steps": ["Analizar", "Resolver"],
                    "confidence": 0.5
                }
            ]
        
        prompt = self.approach_generation_prompt.format_messages(
            problem=problem,
            context=context,
            num_approaches=num_approaches
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
            
            approaches = data.get("approaches", [])
            if not isinstance(approaches, list):
                approaches = []
            
            return approaches
            
        except Exception as e:
            print(f"⚠️ [Path Dependent Reasoning] Error generando enfoques: {e}")
            print(f"   Contenido recibido: {content[:200] if 'content' in locals() else 'N/A'}")
            # Retornar enfoque básico en caso de error
            return [
                {
                    "approach": "Análisis directo",
                    "description": "Enfoque directo al problema",
                    "strategy": "Analizar y resolver directamente",
                    "expected_steps": ["Analizar", "Resolver"],
                    "confidence": 0.5
                }
            ]
    
    def _prioritize_by_learning(
        self,
        approaches: List[Dict[str, Any]],
        task_type: str
    ) -> List[Dict[str, Any]]:
        """Prioriza enfoques basándose en aprendizaje previo."""
        effectiveness = self.approach_effectiveness.get(task_type, {})
        
        # Agregar score de efectividad a cada enfoque
        for approach in approaches:
            approach_name = approach.get("approach", "")
            success_rate = effectiveness.get(approach_name, 0.5)  # Default 0.5 si no hay datos
            
            # Ajustar confianza basándose en aprendizaje
            original_confidence = approach.get("confidence", 0.5)
            approach["learned_confidence"] = (original_confidence * 0.3) + (success_rate * 0.7)
        
        # Ordenar por confianza aprendida
        approaches.sort(key=lambda x: x.get("learned_confidence", 0.5), reverse=True)
        
        return approaches
    
    async def _simulate_path(
        self,
        approach: str,
        steps: List[str],
        context: str
    ) -> Any:
        """Simula la ejecución de un camino."""
        # Simulación básica
        return f"Resultado simulado de enfoque: {approach}"
    
    async def _learn_from_paths(
        self,
        paths: List[ReasoningPath],
        task_type: str
    ):
        """Aprende de los caminos probados."""
        if task_type not in self.approach_effectiveness:
            self.approach_effectiveness[task_type] = {}
        
        effectiveness = self.approach_effectiveness[task_type]
        
        for path in paths:
            approach = path.approach
            
            if approach not in effectiveness:
                effectiveness[approach] = {
                    "successes": 0,
                    "total": 0,
                    "success_rate": 0.5
                }
            
            stats = effectiveness[approach]
            stats["total"] += 1
            
            if path.success:
                stats["successes"] += 1
            
            stats["success_rate"] = stats["successes"] / stats["total"] if stats["total"] > 0 else 0.5
        
        self._save_learning_data()
    
    def get_best_approach(self, task_type: str) -> Optional[str]:
        """Obtiene el mejor enfoque aprendido para un tipo de tarea."""
        if task_type not in self.approach_effectiveness:
            return None
        
        effectiveness = self.approach_effectiveness[task_type]
        
        if not effectiveness:
            return None
        
        # Encontrar enfoque con mayor tasa de éxito
        best_approach = None
        best_rate = 0.0
        
        for approach, stats in effectiveness.items():
            if isinstance(stats, dict):
                rate = stats.get("success_rate", 0.0)
            else:
                rate = stats  # Compatibilidad con formato antiguo
            
            if rate > best_rate:
                best_rate = rate
                best_approach = approach
        
        return best_approach
    
    def get_statistics(self) -> Dict[str, Any]:
        """Obtiene estadísticas del razonador."""
        total_paths = sum(len(paths) for paths in self.paths.values())
        successful_paths = sum(
            sum(1 for p in paths if p.success)
            for paths in self.paths.values()
        )
        
        return {
            "total_paths_tested": total_paths,
            "successful_paths": successful_paths,
            "success_rate": (successful_paths / total_paths * 100) if total_paths > 0 else 0,
            "learned_approaches": len(self.approach_effectiveness),
            "task_types": list(self.approach_effectiveness.keys())
        }

