"""
LangGraph Integration - Workflow orchestration avanzado
Integración de LangGraph para workflows complejos con estado persistente.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, TypedDict, Annotated, Tuple
from datetime import datetime

try:
    from langgraph.graph import StateGraph, END
    from langgraph.graph.message import add_messages
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.prebuilt import ToolNode
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    print("⚠️ LangGraph no está instalado. Instala con: pip install langgraph")

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.language_models import BaseLanguageModel

from ..config import AppConfig


class WorkflowState(TypedDict):
    """Estado del workflow LangGraph."""
    messages: Annotated[List[BaseMessage], add_messages]
    data: Dict[str, Any]
    step: str
    metadata: Dict[str, Any]


class LangGraphIntegration:
    """
    Integración de LangGraph para workflows avanzados.
    
    Características:
    - Workflows con estado persistente
    - Graph-based execution
    - Manejo de errores y retries
    - Flujos condicionales complejos
    """
    
    def __init__(self, config: AppConfig, llm: Optional[BaseLanguageModel] = None):
        self.config = config
        self.llm = llm
        
        if not LANGGRAPH_AVAILABLE:
            raise ImportError("LangGraph no está instalado. Instala con: pip install langgraph")
        
        # Memory para checkpointing
        self.memory = MemorySaver()
        self.graphs: Dict[str, StateGraph] = {}
    
    def create_workflow(
        self,
        workflow_id: str,
        nodes: Dict[str, Any],
        edges: List[Tuple[str, str]],
        entry_point: str = "start",
        exit_point: str = "end"
    ) -> StateGraph:
        """
        Crea un workflow LangGraph.
        
        Args:
            workflow_id: ID único del workflow
            nodes: Diccionario de nodos {name: callable}
            edges: Lista de edges [(from, to)]
            entry_point: Nodo de entrada
            exit_point: Nodo de salida
        """
        graph = StateGraph(WorkflowState)
        
        # Agregar nodos
        for node_name, node_func in nodes.items():
            graph.add_node(node_name, node_func)
        
        # Agregar edges
        for from_node, to_node in edges:
            graph.add_edge(from_node, to_node)
        
        # Set entry point
        graph.set_entry_point(entry_point)
        
        # Compilar con memory
        compiled_graph = graph.compile(checkpointer=self.memory)
        
        self.graphs[workflow_id] = compiled_graph
        return compiled_graph
    
    def execute_workflow(
        self,
        workflow_id: str,
        initial_data: Dict[str, Any],
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Ejecuta un workflow.
        
        Args:
            workflow_id: ID del workflow
            initial_data: Datos iniciales
            config: Configuración de ejecución
        """
        if workflow_id not in self.graphs:
            raise ValueError(f"Workflow {workflow_id} no encontrado")
        
        graph = self.graphs[workflow_id]
        
        # Crear estado inicial
        initial_state = {
            "messages": [],
            "data": initial_data,
            "step": "start",
            "metadata": {}
        }
        
        # Configuración de ejecución
        run_config = config or {"configurable": {"thread_id": workflow_id}}
        
        # Ejecutar
        result = graph.invoke(initial_state, config=run_config)
        
        return {
            "success": True,
            "result": result,
            "final_data": result.get("data", {}),
            "messages": result.get("messages", [])
        }
    
    def create_conditional_edge(
        self,
        from_node: str,
        condition_func: callable,
        path_map: Dict[str, str]
    ):
        """
        Crea un edge condicional.
        
        Args:
            from_node: Nodo origen
            condition_func: Función que retorna la ruta
            path_map: Mapeo de condiciones a nodos destino
        """
        # Esto se implementaría en create_workflow
        pass

