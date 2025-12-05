"""Adaptive Chain of Actions: Planificación dinámica y re-planificación.

Basado en el paper de Corvic AI sobre L4 RAG:
- Planifica estrategia de retrieval dinámicamente
- Re-planifica si no encuentra resultados
- Adapta estrategia según tipo de query
- Self-reflection: detecta gaps y re-ejecuta

Permite encontrar información que requiere múltiples pasos.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


class ActionType(str, Enum):
    """Tipo de acción en la cadena."""
    SEMANTIC_SEARCH = "semantic_search"
    STRUCTURAL_SEARCH = "structural_search"
    METADATA_SEARCH = "metadata_search"
    TABLE_LOOKUP = "table_lookup"
    CROSS_REFERENCE = "cross_reference"
    AGGREGATION = "aggregation"
    CALCULATION = "calculation"
    SYNTHESIS = "synthesis"


@dataclass
class RetrievalAction:
    """Acción de retrieval en la cadena."""
    action_type: ActionType
    query: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    expected_result: Optional[str] = None
    executed: bool = False
    result: Optional[Any] = None
    success: bool = False
    confidence: float = 0.0


@dataclass
class RetrievalPlan:
    """Plan de retrieval adaptativo."""
    original_query: str
    actions: List[RetrievalAction] = field(default_factory=list)
    current_step: int = 0
    max_iterations: int = 5
    confidence_threshold: float = 0.7
    completed: bool = False
    final_results: List[Any] = field(default_factory=list)


class AdaptiveChainOfActions:
    """Cadena adaptativa de acciones para retrieval."""
    
    def __init__(self, mixture_of_spaces: Any, llm: Any):
        self.mixture_of_spaces = mixture_of_spaces
        self.llm = llm
        self.execution_history: List[RetrievalPlan] = []
    
    def execute_query(
        self,
        query: str,
        max_iterations: int = 5,
        confidence_threshold: float = 0.7,
    ) -> Tuple[List[Any], RetrievalPlan]:
        """Ejecuta query con planificación adaptativa."""
        plan = RetrievalPlan(
            original_query=query,
            max_iterations=max_iterations,
            confidence_threshold=confidence_threshold,
        )
        
        # Plan inicial
        initial_actions = self._plan_initial_actions(query)
        plan.actions = initial_actions
        
        # Ejecutar plan iterativamente
        for iteration in range(max_iterations):
            if plan.completed:
                break
            
            # Ejecutar siguiente acción
            action = self._get_next_action(plan)
            if not action:
                break
            
            # Ejecutar acción
            result = self._execute_action(action, plan)
            action.executed = True
            action.result = result
            action.success = result is not None and len(result) > 0
            
            # Evaluar si necesitamos re-planificar
            if not action.success or self._needs_replanning(plan, action):
                # Re-planificar
                new_actions = self._replan(plan, action)
                plan.actions.extend(new_actions)
            
            # Verificar si tenemos suficiente información
            if self._has_sufficient_information(plan):
                plan.completed = True
                plan.final_results = self._synthesize_results(plan)
                break
        
        self.execution_history.append(plan)
        return plan.final_results, plan
    
    def _plan_initial_actions(self, query: str) -> List[RetrievalAction]:
        """Planifica acciones iniciales basadas en la query."""
        actions = []
        
        # Analizar query para determinar estrategia
        query_lower = query.lower()
        
        # Si menciona tablas o números, buscar estructuralmente
        if any(keyword in query_lower for keyword in ["tabla", "table", "columna", "fila", "número", "número"]):
            actions.append(RetrievalAction(
                action_type=ActionType.STRUCTURAL_SEARCH,
                query=query,
                parameters={"search_type": "table"},
            ))
        
        # Si menciona secciones o capítulos, buscar por headings
        if any(keyword in query_lower for keyword in ["sección", "capítulo", "heading", "título"]):
            actions.append(RetrievalAction(
                action_type=ActionType.STRUCTURAL_SEARCH,
                query=query,
                parameters={"search_type": "heading"},
            ))
        
        # Si menciona tags o categorías, buscar por metadata
        if any(keyword in query_lower for keyword in ["tag", "categoría", "tipo", "domain"]):
            actions.append(RetrievalAction(
                action_type=ActionType.METADATA_SEARCH,
                query=query,
            ))
        
        # Siempre incluir búsqueda semántica como fallback
        actions.append(RetrievalAction(
            action_type=ActionType.SEMANTIC_SEARCH,
            query=query,
        ))
        
        return actions
    
    def _get_next_action(self, plan: RetrievalPlan) -> Optional[RetrievalAction]:
        """Obtiene siguiente acción a ejecutar."""
        for action in plan.actions:
            if not action.executed:
                return action
        return None
    
    def _execute_action(self, action: RetrievalAction, plan: RetrievalPlan) -> List[Any]:
        """Ejecuta una acción de retrieval."""
        try:
            if action.action_type == ActionType.SEMANTIC_SEARCH:
                results = self.mixture_of_spaces.search(
                    query=action.query,
                    k=5,
                    use_semantic=True,
                    use_structural=False,
                    use_metadata=False,
                )
                return results
            
            elif action.action_type == ActionType.STRUCTURAL_SEARCH:
                search_type = action.parameters.get("search_type", "heading")
                
                if search_type == "heading":
                    doc_ids = self.mixture_of_spaces.structural_space.search_by_heading(
                        action.query,
                        k=5,
                    )
                elif search_type == "table":
                    doc_ids = self.mixture_of_spaces.structural_space.search_by_table(
                        action.query,
                        k=5,
                    )
                else:
                    doc_ids = []
                
                # Convertir doc_ids a Documents (simplificado)
                # En producción, recuperarías los documentos completos
                return [{"doc_id": doc_id, "type": "structural"} for doc_id in doc_ids]
            
            elif action.action_type == ActionType.METADATA_SEARCH:
                # Buscar por tags
                tag_doc_ids = self.mixture_of_spaces.metadata_space.search_by_tag(
                    action.query,
                    k=5,
                )
                # Buscar por domain
                domain_doc_ids = self.mixture_of_spaces.metadata_space.search_by_domain(
                    action.query,
                    k=5,
                )
                
                all_doc_ids = list(set(tag_doc_ids + domain_doc_ids))
                return [{"doc_id": doc_id, "type": "metadata"} for doc_id in all_doc_ids]
            
            else:
                return []
        
        except Exception as e:
            print(f"⚠️ Error ejecutando acción {action.action_type}: {e}")
            return []
    
    def _needs_replanning(self, plan: RetrievalPlan, last_action: RetrievalAction) -> bool:
        """Determina si necesitamos re-planificar."""
        # Si la última acción falló
        if not last_action.success:
            return True
        
        # Si tenemos resultados pero con baja confianza
        if last_action.success and last_action.confidence < plan.confidence_threshold:
            return True
        
        # Si no hay más acciones y no tenemos resultados suficientes
        remaining_actions = [a for a in plan.actions if not a.executed]
        if not remaining_actions and len(plan.final_results) == 0:
            return True
        
        return False
    
    def _replan(self, plan: RetrievalPlan, failed_action: RetrievalAction) -> List[RetrievalAction]:
        """Re-planifica después de una acción fallida."""
        new_actions = []
        
        # Si falló búsqueda semántica, intentar estructural
        if failed_action.action_type == ActionType.SEMANTIC_SEARCH:
            new_actions.append(RetrievalAction(
                action_type=ActionType.STRUCTURAL_SEARCH,
                query=plan.original_query,
                parameters={"search_type": "heading"},
            ))
            new_actions.append(RetrievalAction(
                action_type=ActionType.METADATA_SEARCH,
                query=plan.original_query,
            ))
        
        # Si falló búsqueda estructural, intentar metadata
        elif failed_action.action_type == ActionType.STRUCTURAL_SEARCH:
            new_actions.append(RetrievalAction(
                action_type=ActionType.METADATA_SEARCH,
                query=plan.original_query,
            ))
            new_actions.append(RetrievalAction(
                action_type=ActionType.SEMANTIC_SEARCH,
                query=plan.original_query,
            ))
        
        # Si falló metadata, intentar semántica con query expandida
        elif failed_action.action_type == ActionType.METADATA_SEARCH:
            # Expandir query
            expanded_query = self._expand_query(plan.original_query)
            new_actions.append(RetrievalAction(
                action_type=ActionType.SEMANTIC_SEARCH,
                query=expanded_query,
            ))
        
        return new_actions
    
    def _expand_query(self, query: str) -> str:
        """Expande query con sinónimos o términos relacionados."""
        # Simplificado: en producción usarías un LLM o thesaurus
        expansions = {
            "ventas": ["ventas", "revenue", "ingresos", "sales"],
            "costos": ["costos", "costs", "gastos", "expenses"],
            "roi": ["roi", "return on investment", "retorno"],
            "q4": ["q4", "cuarto trimestre", "fourth quarter"],
        }
        
        query_lower = query.lower()
        expanded_terms = [query]
        
        for key, synonyms in expansions.items():
            if key in query_lower:
                expanded_terms.extend(synonyms)
        
        return " ".join(expanded_terms)
    
    def _has_sufficient_information(self, plan: RetrievalPlan) -> bool:
        """Determina si tenemos suficiente información para responder."""
        successful_actions = [a for a in plan.actions if a.success]
        
        # Si tenemos al menos una acción exitosa con resultados
        if successful_actions:
            total_results = sum(len(a.result) if a.result else 0 for a in successful_actions)
            return total_results > 0
        
        return False
    
    def _synthesize_results(self, plan: RetrievalPlan) -> List[Any]:
        """Sintetiza resultados de múltiples acciones."""
        all_results = []
        
        for action in plan.actions:
            if action.success and action.result:
                all_results.extend(action.result)
        
        # Deduplicar (simplificado)
        seen = set()
        unique_results = []
        for result in all_results:
            if isinstance(result, dict):
                result_id = result.get("doc_id") or str(result)
            else:
                result_id = str(result)
            
            if result_id not in seen:
                seen.add(result_id)
                unique_results.append(result)
        
        return unique_results

