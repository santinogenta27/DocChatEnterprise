"""
Reinforcement Learning y Planning - Razonamiento por árboles de decisiones
Sistema que prueba, falla, retrocede, intenta otra cosa
Base para inteligencia real según Eric Schmidt
"""

from __future__ import annotations

import json
import time
import uuid
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from langchain_core.language_models import BaseLanguageModel
from langchain_core.prompts import ChatPromptTemplate

from .config import AppConfig


class DecisionNodeStatus(str, Enum):
    """Estado de un nodo en el árbol de decisiones."""
    PENDING = "pending"
    EXPLORING = "exploring"
    SUCCESS = "success"
    FAILED = "failed"
    PRUNED = "pruned"  # Podado porque otro camino es mejor


@dataclass
class DecisionNode:
    """Nodo en el árbol de decisiones."""
    node_id: str
    parent_id: Optional[str]
    depth: int
    action: str  # Acción a probar
    reasoning: str  # Razonamiento para esta acción
    expected_outcome: str  # Qué esperamos obtener
    status: DecisionNodeStatus = DecisionNodeStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    confidence: float = 0.0
    execution_time: float = 0.0
    timestamp: float = field(default_factory=time.time)
    children: List[str] = field(default_factory=list)  # IDs de nodos hijos


@dataclass
class DecisionTree:
    """Árbol completo de decisiones."""
    tree_id: str
    goal: str  # Objetivo principal
    root_node_id: str
    nodes: Dict[str, DecisionNode] = field(default_factory=dict)
    best_path: List[str] = field(default_factory=list)  # IDs de nodos del mejor camino
    best_result: Optional[Any] = None
    max_depth: int = 10
    max_branches: int = 5  # Máximo de ramas por nodo
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    total_explorations: int = 0
    successful_paths: int = 0
    failed_paths: int = 0


class ReinforcementPlanner:
    """
    Sistema de planificación con reinforcement learning.
    
    Características:
    - Prueba diferentes enfoques
    - Si falla, retrocede y prueba otra cosa
    - Aprende qué funciona mejor
    - Construye árboles de decisiones
    """
    
    def __init__(
        self,
        config: AppConfig,
        llm: Optional[BaseLanguageModel] = None,
        max_depth: int = 10,
        max_branches: int = 5,
        learning_enabled: bool = True
    ):
        self.config = config
        self.llm = llm
        self.max_depth = max_depth
        self.max_branches = max_branches
        self.learning_enabled = learning_enabled
        
        # Historial de árboles y aprendizajes
        self.trees: Dict[str, DecisionTree] = {}
        self.learning_memory: Dict[str, Any] = {}  # Aprende qué funciona
        
        # Directorio para persistencia
        self.storage_dir = Path(config.memory_dir) / "reinforcement_planning"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Cargar aprendizaje previo
        self._load_learning_memory()
        
        # Prompts
        self.action_generation_prompt = ChatPromptTemplate.from_messages([
            ("system", """Eres un planificador inteligente que genera acciones para alcanzar objetivos.

Dado un objetivo y el contexto actual, genera posibles acciones a probar.

Para cada acción, considera:
1. ¿Es factible?
2. ¿Qué probabilidad tiene de éxito?
3. ¿Qué recursos requiere?
4. ¿Cuáles son los riesgos?

Responde en JSON:
{
    "actions": [
        {
            "action": "descripción de la acción",
            "reasoning": "por qué esta acción podría funcionar",
            "expected_outcome": "qué esperamos obtener",
            "confidence": 0.0-1.0,
            "risks": ["riesgo1", "riesgo2"],
            "resources_needed": ["recurso1", "recurso2"]
        }
    ],
    "reasoning": "razonamiento general sobre estas acciones"
}"""),
            ("human", """Objetivo: {goal}

Contexto actual:
{context}

Historial de intentos:
{attempt_history}

Genera acciones posibles para alcanzar el objetivo.""")
        ])
        
        self.evaluation_prompt = ChatPromptTemplate.from_messages([
            ("system", """Evalúa el resultado de una acción.

Dado una acción y su resultado, determina:
1. ¿Fue exitosa?
2. ¿Qué aprendimos?
3. ¿Qué deberíamos probar a continuación?
4. ¿Deberíamos retroceder y probar otra cosa?

Responde en JSON:
{
    "success": true/false,
    "success_score": 0.0-1.0,
    "lessons_learned": ["lección1", "lección2"],
    "next_actions": ["acción1", "acción2"] o null si debemos retroceder,
    "should_backtrack": true/false,
    "reasoning": "razonamiento detallado"
}"""),
            ("human", """Acción: {action}

Resultado: {result}

Error (si hubo): {error}

Evalúa este resultado.""")
        ])
    
    def _load_learning_memory(self):
        """Carga memoria de aprendizaje previo."""
        memory_file = self.storage_dir / "learning_memory.json"
        if memory_file.exists():
            try:
                with open(memory_file, "r", encoding="utf-8") as f:
                    self.learning_memory = json.load(f)
                print(f"✅ [Reinforcement Planner] Memoria de aprendizaje cargada")
            except Exception as e:
                print(f"⚠️ [Reinforcement Planner] Error cargando memoria: {e}")
    
    def _save_learning_memory(self):
        """Guarda memoria de aprendizaje."""
        memory_file = self.storage_dir / "learning_memory.json"
        try:
            with open(memory_file, "w", encoding="utf-8") as f:
                json.dump(self.learning_memory, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️ [Reinforcement Planner] Error guardando memoria: {e}")
    
    async def plan_and_execute(
        self,
        goal: str,
        context: str = "",
        initial_actions: Optional[List[str]] = None,
        executor: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Planifica y ejecuta un objetivo usando árboles de decisiones.
        
        Args:
            goal: Objetivo a alcanzar
            context: Contexto adicional
            initial_actions: Acciones iniciales sugeridas (opcional)
            executor: Función que ejecuta acciones (opcional)
        
        Returns:
            Resultado con el mejor camino encontrado
        """
        tree_id = str(uuid.uuid4())
        print(f"🌳 [Reinforcement Planner] Iniciando planificación para: {goal[:50]}...")
        
        # Crear árbol
        root_node = DecisionNode(
            node_id=str(uuid.uuid4()),
            parent_id=None,
            depth=0,
            action="START",
            reasoning="Nodo raíz",
            expected_outcome=goal
        )
        
        tree = DecisionTree(
            tree_id=tree_id,
            goal=goal,
            root_node_id=root_node.node_id,
            max_depth=self.max_depth,
            max_branches=self.max_branches
        )
        tree.nodes[root_node.node_id] = root_node
        
        # Explorar árbol
        best_result = await self._explore_tree(
            tree=tree,
            current_node_id=root_node.node_id,
            context=context,
            executor=executor
        )
        
        tree.completed_at = time.time()
        tree.best_result = best_result
        
        # Guardar árbol
        self.trees[tree_id] = tree
        
        # Aprender de este árbol
        if self.learning_enabled:
            await self._learn_from_tree(tree)
        
        return {
            "tree_id": tree_id,
            "goal": goal,
            "success": best_result is not None,
            "best_path": tree.best_path,
            "best_result": best_result,
            "total_explorations": tree.total_explorations,
            "successful_paths": tree.successful_paths,
            "failed_paths": tree.failed_paths,
            "execution_time": tree.completed_at - tree.created_at
        }
    
    async def _explore_tree(
        self,
        tree: DecisionTree,
        current_node_id: str,
        context: str,
        executor: Optional[callable] = None,
        attempt_history: List[str] = None
    ) -> Optional[Any]:
        """
        Explora el árbol de decisiones recursivamente.
        Prueba acciones, si falla retrocede, si funciona continúa.
        """
        if attempt_history is None:
            attempt_history = []
        
        current_node = tree.nodes[current_node_id]
        
        # Si ya alcanzamos la profundidad máxima, retroceder
        if current_node.depth >= tree.max_depth:
            return None
        
        # Si este nodo ya fue explorado exitosamente, retornar resultado
        if current_node.status == DecisionNodeStatus.SUCCESS:
            return current_node.result
        
        # Generar acciones posibles desde este nodo
        actions = await self._generate_actions(
            goal=tree.goal,
            context=context,
            current_depth=current_node.depth,
            attempt_history=attempt_history,
            parent_action=current_node.action
        )
        
        # Limitar número de ramas
        actions = actions[:tree.max_branches]
        
        best_result = None
        best_node_id = None
        
        # Probar cada acción
        for action_data in actions:
            action = action_data.get("action", "")
            reasoning = action_data.get("reasoning", "")
            expected_outcome = action_data.get("expected_outcome", "")
            confidence = action_data.get("confidence", 0.5)
            
            # Crear nodo hijo
            child_node = DecisionNode(
                node_id=str(uuid.uuid4()),
                parent_id=current_node_id,
                depth=current_node.depth + 1,
                action=action,
                reasoning=reasoning,
                expected_outcome=expected_outcome,
                confidence=confidence
            )
            
            tree.nodes[child_node.node_id] = child_node
            current_node.children.append(child_node.node_id)
            tree.total_explorations += 1
            
            # Ejecutar acción
            child_node.status = DecisionNodeStatus.EXPLORING
            start_time = time.time()
            
            try:
                # Ejecutar acción (si hay executor, usarlo; sino, solo simular)
                if executor:
                    result = await executor(action, context)
                else:
                    # Simular ejecución
                    result = await self._simulate_action(action, context)
                
                child_node.execution_time = time.time() - start_time
                child_node.result = result
                
                # Evaluar resultado
                evaluation = await self._evaluate_result(
                    action=action,
                    result=result,
                    error=None
                )
                
                if evaluation.get("success", False):
                    # ¡Éxito! Continuar desde aquí
                    child_node.status = DecisionNodeStatus.SUCCESS
                    child_node.confidence = evaluation.get("success_score", 0.8)
                    
                    # Actualizar mejor camino
                    if best_result is None or evaluation.get("success_score", 0) > child_node.confidence:
                        best_result = result
                        best_node_id = child_node.node_id
                    
                    # Si el objetivo está completo, retornar
                    if evaluation.get("goal_complete", False):
                        # Construir mejor camino
                        tree.best_path = self._build_path(tree, child_node.node_id)
                        tree.successful_paths += 1
                        return result
                    
                    # Continuar explorando desde este nodo exitoso
                    next_actions = evaluation.get("next_actions", [])
                    if next_actions:
                        # Explorar recursivamente
                        deeper_result = await self._explore_tree(
                            tree=tree,
                            current_node_id=child_node.node_id,
                            context=context + f"\nResultado anterior: {result}",
                            executor=executor,
                            attempt_history=attempt_history + [action]
                        )
                        
                        if deeper_result is not None:
                            # Actualizar mejor camino
                            tree.best_path = self._build_path(tree, child_node.node_id)
                            tree.successful_paths += 1
                            return deeper_result
                    
                else:
                    # Falla - retroceder
                    child_node.status = DecisionNodeStatus.FAILED
                    child_node.error = evaluation.get("reasoning", "Acción falló")
                    tree.failed_paths += 1
                    
                    # Aprender de la falla
                    if self.learning_enabled:
                        await self._learn_from_failure(action, result, evaluation)
                    
                    # Si deberíamos retroceder, no explorar más desde aquí
                    if evaluation.get("should_backtrack", True):
                        continue
                    
            except Exception as e:
                # Error en ejecución
                child_node.status = DecisionNodeStatus.FAILED
                child_node.error = str(e)
                child_node.execution_time = time.time() - start_time
                tree.failed_paths += 1
        
        # Si encontramos un mejor resultado, retornarlo
        if best_result is not None and best_node_id:
            tree.best_path = self._build_path(tree, best_node_id)
            tree.successful_paths += 1
            return best_result
        
        # Si llegamos aquí, ningún camino funcionó completamente
        return None
    
    async def _generate_actions(
        self,
        goal: str,
        context: str,
        current_depth: int,
        attempt_history: List[str],
        parent_action: str
    ) -> List[Dict[str, Any]]:
        """Genera acciones posibles usando LLM."""
        if not self.llm:
            # Fallback: acciones genéricas
            return [
                {
                    "action": f"Paso {current_depth + 1}: Analizar el problema",
                    "reasoning": "Análisis inicial",
                    "expected_outcome": "Comprensión del problema",
                    "confidence": 0.5
                }
            ]
        
        # Construir historial de intentos
        history_text = "\n".join([f"- {a}" for a in attempt_history[-5:]]) if attempt_history else "Ninguno"
        
        # Usar aprendizaje previo si existe
        learned_context = ""
        if goal in self.learning_memory:
            learned = self.learning_memory[goal]
            learned_context = f"\n\nAprendizaje previo: {learned.get('lessons', [])}"
        
        prompt = self.action_generation_prompt.format_messages(
            goal=goal,
            context=context + learned_context,
            attempt_history=history_text
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
                
                # Buscar el primer { o [ en todo el string
                first_brace = json_str.find('{')
                first_bracket = json_str.find('[')
                
                if first_brace >= 0 or first_bracket >= 0:
                    start_pos = min(
                        first_brace if first_brace >= 0 else len(json_str),
                        first_bracket if first_bracket >= 0 else len(json_str)
                    )
                    json_str = json_str[start_pos:]
                
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
                # Buscar JSON completo con regex más robusto
                json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', json_str, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                    data = json.loads(json_str)
                else:
                    # Si aún falla, retornar lista vacía
                    raise je
            
            if not isinstance(data, dict):
                raise ValueError("El JSON no es un objeto")
            
            actions = data.get("actions", [])
            if not isinstance(actions, list):
                actions = []
            
            return actions
            
        except Exception as e:
            print(f"⚠️ [Reinforcement Planner] Error generando acciones: {e}")
            print(f"   Contenido recibido: {content[:200] if 'content' in locals() else 'N/A'}")
            return []
    
    async def _simulate_action(self, action: str, context: str) -> Any:
        """Simula la ejecución de una acción (para cuando no hay executor)."""
        # Simulación básica - en producción esto debería ejecutar realmente
        return f"Resultado simulado de: {action}"
    
    async def _evaluate_result(
        self,
        action: str,
        result: Any,
        error: Optional[str]
    ) -> Dict[str, Any]:
        """Evalúa el resultado de una acción."""
        if not self.llm:
            # Fallback: evaluar básicamente
            return {
                "success": error is None,
                "success_score": 0.7 if error is None else 0.0,
                "should_backtrack": error is not None
            }
        
        prompt = self.evaluation_prompt.format_messages(
            action=action,
            result=str(result)[:1000] if result else "Sin resultado",
            error=error or "Ninguno"
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
                
                # Buscar el primer { o [ en todo el string
                first_brace = json_str.find('{')
                first_bracket = json_str.find('[')
                
                if first_brace >= 0 or first_bracket >= 0:
                    start_pos = min(
                        first_brace if first_brace >= 0 else len(json_str),
                        first_bracket if first_bracket >= 0 else len(json_str)
                    )
                    json_str = json_str[start_pos:]
                
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
                # Buscar JSON completo con regex más robusto
                json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', json_str, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                    data = json.loads(json_str)
                else:
                    # Si aún falla, usar valores por defecto
                    raise je
            
            if not isinstance(data, dict):
                raise ValueError("El JSON no es un objeto")
            
            # Validar campos requeridos
            if "success" not in data:
                data["success"] = error is None
            if "success_score" not in data:
                data["success_score"] = 0.5
            if "should_backtrack" not in data:
                data["should_backtrack"] = error is not None
            
            return data
            
        except Exception as e:
            print(f"⚠️ [Reinforcement Planner] Error evaluando resultado: {e}")
            print(f"   Contenido recibido: {content[:200] if 'content' in locals() else 'N/A'}")
            return {
                "success": error is None,
                "success_score": 0.5,
                "should_backtrack": error is not None
            }
    
    def _build_path(self, tree: DecisionTree, final_node_id: str) -> List[str]:
        """Construye el camino desde la raíz hasta un nodo."""
        path = []
        current_id = final_node_id
        
        while current_id:
            path.insert(0, current_id)
            node = tree.nodes.get(current_id)
            if node and node.parent_id:
                current_id = node.parent_id
            else:
                break
        
        return path
    
    async def _learn_from_tree(self, tree: DecisionTree):
        """Aprende de un árbol completado."""
        if not self.learning_enabled:
            return
        
        # Extraer lecciones
        successful_actions = []
        failed_actions = []
        
        for node_id in tree.best_path:
            node = tree.nodes.get(node_id)
            if node and node.status == DecisionNodeStatus.SUCCESS:
                successful_actions.append(node.action)
        
        for node in tree.nodes.values():
            if node.status == DecisionNodeStatus.FAILED:
                failed_actions.append({
                    "action": node.action,
                    "error": node.error
                })
        
        # Guardar aprendizaje
        goal_key = tree.goal[:100]  # Limitar longitud
        
        if goal_key not in self.learning_memory:
            self.learning_memory[goal_key] = {
                "successful_actions": [],
                "failed_actions": [],
                "lessons": [],
                "count": 0
            }
        
        memory = self.learning_memory[goal_key]
        memory["successful_actions"].extend(successful_actions)
        memory["failed_actions"].extend(failed_actions)
        memory["count"] += 1
        
        # Generar lecciones aprendidas
        if successful_actions:
            memory["lessons"].append(f"Acciones exitosas: {', '.join(successful_actions[:3])}")
        if failed_actions:
            memory["lessons"].append(f"Evitar: {failed_actions[0].get('action', '')}")
        
        # Limitar tamaño de memoria
        memory["successful_actions"] = memory["successful_actions"][-20:]
        memory["failed_actions"] = memory["failed_actions"][-20:]
        memory["lessons"] = memory["lessons"][-10:]
        
        self._save_learning_memory()
    
    async def _learn_from_failure(self, action: str, result: Any, evaluation: Dict[str, Any]):
        """Aprende de una falla específica."""
        if not self.learning_enabled:
            return
        
        failure_key = f"failure_{hash(action) % 10000}"
        
        if failure_key not in self.learning_memory:
            self.learning_memory[failure_key] = {
                "action": action,
                "failures": 0,
                "reasons": []
            }
        
        memory = self.learning_memory[failure_key]
        memory["failures"] += 1
        memory["reasons"].append(evaluation.get("reasoning", "Razón desconocida"))
        memory["reasons"] = memory["reasons"][-10:]  # Limitar
        
        self._save_learning_memory()
    
    def get_tree(self, tree_id: str) -> Optional[DecisionTree]:
        """Obtiene un árbol por ID."""
        return self.trees.get(tree_id)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Obtiene estadísticas del planner."""
        total_trees = len(self.trees)
        successful_trees = sum(1 for t in self.trees.values() if t.best_result is not None)
        
        return {
            "total_trees": total_trees,
            "successful_trees": successful_trees,
            "success_rate": (successful_trees / total_trees * 100) if total_trees > 0 else 0,
            "total_explorations": sum(t.total_explorations for t in self.trees.values()),
            "learning_memory_size": len(self.learning_memory)
        }

