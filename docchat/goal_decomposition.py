"""
Goal-oriented Task Decomposition - Descomposición de objetivos
Permite objetivos de alto nivel que se descomponen automáticamente en pasos
Potencia las custom tasks existentes
"""

from __future__ import annotations

import json
import time
import uuid
from typing import List, Dict, Optional, Any, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path

from langchain_core.language_models import BaseLanguageModel
from langchain_core.prompts import ChatPromptTemplate

from .config import AppConfig


class TaskStatus(str, Enum):
    """Estado de una subtarea."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"  # Bloqueada por otra tarea


@dataclass
class Subtask:
    """Una subtarea descompuesta."""
    subtask_id: str
    parent_goal_id: str
    description: str
    dependencies: List[str] = field(default_factory=list)  # IDs de subtareas de las que depende
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_order: int = 0  # Orden de ejecución
    estimated_time: float = 0.0
    actual_time: float = 0.0
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Goal:
    """Un objetivo de alto nivel."""
    goal_id: str
    description: str  # Objetivo en lenguaje natural
    subtasks: List[Subtask] = field(default_factory=list)
    status: str = "pending"  # "pending", "in_progress", "completed", "failed"
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    progress: float = 0.0  # 0.0 - 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class GoalDecomposer:
    """
    Sistema de descomposición de objetivos de alto nivel.
    
    Características:
    - Toma objetivos de alto nivel en lenguaje natural
    - Los descompone automáticamente en subtareas
    - Identifica dependencias entre subtareas
    - Ejecuta subtareas en el orden correcto
    - Potencia las custom tasks existentes
    """
    
    def __init__(
        self,
        config: AppConfig,
        llm: Optional[BaseLanguageModel] = None
    ):
        self.config = config
        self.llm = llm
        
        # Objetivos activos
        self.goals: Dict[str, Goal] = {}
        
        # Directorio para persistencia
        self.storage_dir = Path(config.memory_dir) / "goal_decomposition"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Cargar objetivos guardados
        self._load_goals()
        
        # Prompts
        self.decomposition_prompt = ChatPromptTemplate.from_messages([
            ("system", """Eres un experto en descomponer objetivos complejos en subtareas ejecutables.

Dado un objetivo de alto nivel, descomponlo en subtareas específicas, identificando:
1. Qué pasos son necesarios
2. Qué dependencias hay entre pasos
3. Qué orden de ejecución es correcto
4. Qué recursos se necesitan

Responde en JSON:
{
    "subtasks": [
        {
            "description": "descripción de la subtarea",
            "dependencies": ["descripción de subtarea de la que depende"] o [],
            "estimated_time": tiempo estimado en minutos,
            "resources_needed": ["recurso1", "recurso2"],
            "priority": "high|medium|low"
        }
    ],
    "reasoning": "razonamiento sobre la descomposición",
    "estimated_total_time": tiempo total estimado
}"""),
            ("human", """Objetivo: {goal}

Contexto: {context}

Descompón este objetivo en subtareas ejecutables.""")
        ])
    
    def _load_goals(self):
        """Carga objetivos guardados."""
        goals_file = self.storage_dir / "goals.json"
        if goals_file.exists():
            try:
                with open(goals_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for goal_data in data.get("goals", []):
                        goal = Goal(**goal_data)
                        # Reconstruir subtareas
                        goal.subtasks = [
                            Subtask(**st_data) for st_data in goal_data.get("subtasks", [])
                        ]
                        self.goals[goal.goal_id] = goal
                print(f"✅ [Goal Decomposition] {len(self.goals)} objetivos cargados")
            except Exception as e:
                print(f"⚠️ [Goal Decomposition] Error cargando objetivos: {e}")
    
    def _save_goals(self):
        """Guarda objetivos."""
        goals_file = self.storage_dir / "goals.json"
        try:
            data = {
                "goals": [
                    {
                        **asdict(goal),
                        "subtasks": [asdict(st) for st in goal.subtasks]
                    }
                    for goal in self.goals.values()
                ]
            }
            with open(goals_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️ [Goal Decomposition] Error guardando objetivos: {e}")
    
    async def decompose_goal(
        self,
        goal_description: str,
        context: str = ""
    ) -> str:
        """
        Descompone un objetivo de alto nivel en subtareas.
        
        Returns:
            goal_id: ID del objetivo creado
        """
        goal_id = str(uuid.uuid4())
        print(f"🎯 [Goal Decomposition] Descomponiendo objetivo: {goal_description[:50]}...")
        
        # Descomponer usando LLM
        subtasks_data = await self._decompose_with_llm(goal_description, context)
        
        # Crear subtareas
        subtasks = []
        for i, st_data in enumerate(subtasks_data.get("subtasks", [])):
            subtask = Subtask(
                subtask_id=str(uuid.uuid4()),
                parent_goal_id=goal_id,
                description=st_data.get("description", ""),
                estimated_time=st_data.get("estimated_time", 5.0),
                execution_order=i,
                metadata={
                    "resources_needed": st_data.get("resources_needed", []),
                    "priority": st_data.get("priority", "medium")
                }
            )
            subtasks.append(subtask)
        
        # Resolver dependencias (convertir descripciones a IDs)
        self._resolve_dependencies(subtasks, subtasks_data.get("subtasks", []))
        
        # Crear objetivo
        goal = Goal(
            goal_id=goal_id,
            description=goal_description,
            subtasks=subtasks,
            metadata={
                "reasoning": subtasks_data.get("reasoning", ""),
                "estimated_total_time": subtasks_data.get("estimated_total_time", 0.0)
            }
        )
        
        self.goals[goal_id] = goal
        self._save_goals()
        
        print(f"✅ [Goal Decomposition] Objetivo descompuesto en {len(subtasks)} subtareas")
        
        return goal_id
    
    async def _decompose_with_llm(
        self,
        goal_description: str,
        context: str
    ) -> Dict[str, Any]:
        """Descompone objetivo usando LLM."""
        if not self.llm:
            # Fallback: descomposición básica
            return {
                "subtasks": [
                    {
                        "description": f"Paso 1: Analizar el objetivo",
                        "dependencies": [],
                        "estimated_time": 5.0,
                        "priority": "high"
                    },
                    {
                        "description": f"Paso 2: Ejecutar acciones necesarias",
                        "dependencies": ["Paso 1: Analizar el objetivo"],
                        "estimated_time": 10.0,
                        "priority": "high"
                    }
                ],
                "reasoning": "Descomposición básica",
                "estimated_total_time": 15.0
            }
        
        prompt = self.decomposition_prompt.format_messages(
            goal=goal_description,
            context=context
        )
        
        try:
            response = await self.llm.ainvoke(prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            
            # Parsear JSON con manejo robusto de errores
            json_str = None
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
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
                import re
                json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', json_str, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                    data = json.loads(json_str)
                else:
                    raise je
            
            if not isinstance(data, dict):
                raise ValueError("El JSON no es un objeto")
            
            # Validar estructura
            if "subtasks" not in data:
                data["subtasks"] = []
            if "reasoning" not in data:
                data["reasoning"] = ""
            if "estimated_total_time" not in data:
                data["estimated_total_time"] = 0.0
            
            return data
            
        except Exception as e:
            print(f"⚠️ [Goal Decomposition] Error descomponiendo: {e}")
            print(f"   Contenido recibido: {content[:200] if 'content' in locals() else 'N/A'}")
            return {"subtasks": [], "reasoning": "", "estimated_total_time": 0.0}
    
    def _resolve_dependencies(
        self,
        subtasks: List[Subtask],
        subtasks_data: List[Dict[str, Any]]
    ):
        """Resuelve dependencias entre subtareas."""
        # Crear mapa de descripción -> ID
        desc_to_id = {st.description: st.subtask_id for st in subtasks}
        
        for i, st_data in enumerate(subtasks_data):
            dependencies = st_data.get("dependencies", [])
            subtask = subtasks[i]
            
            # Convertir descripciones de dependencias a IDs
            for dep_desc in dependencies:
                # Buscar subtarea con esa descripción
                for other_st in subtasks:
                    if dep_desc in other_st.description or other_st.description in dep_desc:
                        if other_st.subtask_id not in subtask.dependencies:
                            subtask.dependencies.append(other_st.subtask_id)
                        break
    
    async def execute_goal(
        self,
        goal_id: str,
        executor: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Ejecuta un objetivo descompuesto.
        
        Ejecuta las subtareas en el orden correcto, respetando dependencias.
        """
        if goal_id not in self.goals:
            return {"success": False, "error": "Objetivo no encontrado"}
        
        goal = self.goals[goal_id]
        goal.status = "in_progress"
        
        print(f"🚀 [Goal Decomposition] Ejecutando objetivo: {goal.description[:50]}...")
        
        # Ordenar subtareas por orden de ejecución y dependencias
        execution_order = self._calculate_execution_order(goal.subtasks)
        
        completed = 0
        failed = 0
        
        # Ejecutar subtareas en orden
        for subtask_id in execution_order:
            subtask = next(st for st in goal.subtasks if st.subtask_id == subtask_id)
            
            # Verificar que todas las dependencias estén completadas
            if not all(
                next(st for st in goal.subtasks if st.subtask_id == dep_id).status == TaskStatus.COMPLETED
                for dep_id in subtask.dependencies
            ):
                subtask.status = TaskStatus.BLOCKED
                continue
            
            # Ejecutar subtarea
            subtask.status = TaskStatus.IN_PROGRESS
            start_time = time.time()
            
            try:
                if executor:
                    result = await executor(subtask.description, subtask.metadata)
                else:
                    result = await self._simulate_subtask(subtask)
                
                subtask.actual_time = time.time() - start_time
                subtask.result = result
                subtask.status = TaskStatus.COMPLETED
                completed += 1
                
            except Exception as e:
                subtask.actual_time = time.time() - start_time
                subtask.error = str(e)
                subtask.status = TaskStatus.FAILED
                failed += 1
        
        # Actualizar progreso
        total = len(goal.subtasks)
        goal.progress = completed / total if total > 0 else 0.0
        
        # Actualizar estado del objetivo
        if completed == total:
            goal.status = "completed"
            goal.completed_at = time.time()
        elif failed > 0:
            goal.status = "failed"
        else:
            goal.status = "in_progress"
        
        self._save_goals()
        
        return {
            "goal_id": goal_id,
            "status": goal.status,
            "progress": goal.progress,
            "completed": completed,
            "failed": failed,
            "total": total
        }
    
    def _calculate_execution_order(self, subtasks: List[Subtask]) -> List[str]:
        """Calcula el orden de ejecución respetando dependencias."""
        # Topological sort
        in_degree = {st.subtask_id: len(st.dependencies) for st in subtasks}
        queue = [st.subtask_id for st in subtasks if in_degree[st.subtask_id] == 0]
        order = []
        
        while queue:
            current = queue.pop(0)
            order.append(current)
            
            # Reducir grado de entrada de dependientes
            for st in subtasks:
                if current in st.dependencies:
                    in_degree[st.subtask_id] -= 1
                    if in_degree[st.subtask_id] == 0:
                        queue.append(st.subtask_id)
        
        # Si hay subtareas con dependencias no resueltas, agregarlas al final
        remaining = [st.subtask_id for st in subtasks if st.subtask_id not in order]
        order.extend(remaining)
        
        return order
    
    async def _simulate_subtask(self, subtask: Subtask) -> Any:
        """Simula la ejecución de una subtarea."""
        return f"Resultado simulado de: {subtask.description}"
    
    def get_goal(self, goal_id: str) -> Optional[Goal]:
        """Obtiene un objetivo por ID."""
        return self.goals.get(goal_id)
    
    def list_goals(self, status_filter: Optional[str] = None) -> List[Goal]:
        """Lista objetivos."""
        goals = list(self.goals.values())
        
        if status_filter:
            goals = [g for g in goals if g.status == status_filter]
        
        return sorted(goals, key=lambda g: g.created_at, reverse=True)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Obtiene estadísticas de descomposición."""
        total_goals = len(self.goals)
        completed_goals = sum(1 for g in self.goals.values() if g.status == "completed")
        total_subtasks = sum(len(g.subtasks) for g in self.goals.values())
        
        return {
            "total_goals": total_goals,
            "completed_goals": completed_goals,
            "in_progress_goals": sum(1 for g in self.goals.values() if g.status == "in_progress"),
            "total_subtasks": total_subtasks,
            "average_subtasks_per_goal": total_subtasks / total_goals if total_goals > 0 else 0
        }

