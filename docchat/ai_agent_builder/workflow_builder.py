"""
Workflow Builder - Constructor visual de workflows
Permite crear workflows complejos sin código
"""

from __future__ import annotations

import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum


class NodeType(str, Enum):
    """Tipos de nodos en workflows"""
    START = "start"
    END = "end"
    AGENT = "agent"
    CONDITION = "condition"
    PARALLEL = "parallel"
    LOOP = "loop"
    TRANSFORM = "transform"


@dataclass
class WorkflowNode:
    """Nodo en un workflow"""
    node_id: str
    node_type: NodeType
    name: str
    config: Dict[str, Any] = field(default_factory=dict)
    position: Dict[str, float] = field(default_factory=lambda: {"x": 0, "y": 0})


@dataclass
class WorkflowEdge:
    """Edge (conexión) en un workflow"""
    edge_id: str
    from_node: str
    to_node: str
    condition: Optional[str] = None  # Para conditional edges
    label: Optional[str] = None


class WorkflowBuilder:
    """
    Constructor de workflows visuales
    Permite crear workflows complejos sin código
    """
    
    def __init__(self, config: Any):
        self.config = config
        self.workflows: Dict[str, Dict[str, Any]] = {}
    
    def create_workflow(
        self,
        workflow_id: str,
        name: str,
        description: str = ""
    ) -> str:
        """Crea un nuevo workflow"""
        self.workflows[workflow_id] = {
            "workflow_id": workflow_id,
            "name": name,
            "description": description,
            "nodes": [],
            "edges": [],
            "created_at": None
        }
        return workflow_id
    
    def add_node(
        self,
        workflow_id: str,
        node: WorkflowNode
    ) -> str:
        """Agrega un nodo al workflow"""
        if workflow_id not in self.workflows:
            raise ValueError(f"Workflow {workflow_id} no encontrado")
        
        self.workflows[workflow_id]["nodes"].append({
            "node_id": node.node_id,
            "node_type": node.node_type.value,
            "name": node.name,
            "config": node.config,
            "position": node.position
        })
        
        return node.node_id
    
    def add_edge(
        self,
        workflow_id: str,
        edge: WorkflowEdge
    ) -> str:
        """Agrega un edge al workflow"""
        if workflow_id not in self.workflows:
            raise ValueError(f"Workflow {workflow_id} no encontrado")
        
        # Validar que los nodos existan
        node_ids = [n["node_id"] for n in self.workflows[workflow_id]["nodes"]]
        if edge.from_node not in node_ids:
            raise ValueError(f"Nodo {edge.from_node} no encontrado")
        if edge.to_node not in node_ids:
            raise ValueError(f"Nodo {edge.to_node} no encontrado")
        
        self.workflows[workflow_id]["edges"].append({
            "edge_id": edge.edge_id,
            "from_node": edge.from_node,
            "to_node": edge.to_node,
            "condition": edge.condition,
            "label": edge.label
        })
        
        return edge.edge_id
    
    def get_workflow(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene un workflow"""
        return self.workflows.get(workflow_id)
    
    def export_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Exporta workflow a formato JSON"""
        if workflow_id not in self.workflows:
            raise ValueError(f"Workflow {workflow_id} no encontrado")
        
        return self.workflows[workflow_id]
    
    def import_workflow(self, workflow_data: Dict[str, Any]) -> str:
        """Importa workflow desde JSON"""
        workflow_id = workflow_data["workflow_id"]
        self.workflows[workflow_id] = workflow_data
        return workflow_id
    
    def validate_workflow(self, workflow_id: str) -> tuple[bool, List[str]]:
        """
        Valida un workflow
        
        Returns:
            (is_valid, errors)
        """
        if workflow_id not in self.workflows:
            return False, [f"Workflow {workflow_id} no encontrado"]
        
        workflow = self.workflows[workflow_id]
        errors = []
        
        # Validar que hay al menos un nodo START y END
        node_types = [n["node_type"] for n in workflow["nodes"]]
        if NodeType.START.value not in node_types:
            errors.append("Workflow debe tener al menos un nodo START")
        if NodeType.END.value not in node_types:
            errors.append("Workflow debe tener al menos un nodo END")
        
        # Validar que todos los edges conectan nodos válidos
        node_ids = {n["node_id"] for n in workflow["nodes"]}
        for edge in workflow["edges"]:
            if edge["from_node"] not in node_ids:
                errors.append(f"Edge conecta desde nodo inexistente: {edge['from_node']}")
            if edge["to_node"] not in node_ids:
                errors.append(f"Edge conecta a nodo inexistente: {edge['to_node']}")
        
        # Validar que no hay ciclos sin condiciones (simplificado)
        # Validación más compleja se puede agregar después
        
        return len(errors) == 0, errors
