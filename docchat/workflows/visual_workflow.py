"""
Workflows visuales sin código para automatización.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..config import AppConfig
from datetime import datetime


class NodeType(Enum):
    """Tipos de nodos en workflow."""
    TRIGGER = "trigger"
    ACTION = "action"
    CONDITION = "condition"
    LOOP = "loop"
    DELAY = "delay"
    WEBHOOK = "webhook"


@dataclass
class WorkflowNode:
    """Nodo en workflow visual."""
    node_id: str
    node_type: NodeType
    config: Dict[str, Any] = field(default_factory=dict)
    position: Dict[str, float] = field(default_factory=dict)  # x, y
    connections: List[str] = field(default_factory=list)  # IDs de nodos conectados


@dataclass
class Workflow:
    """Workflow visual."""
    workflow_id: str
    name: str
    description: str
    nodes: List[WorkflowNode] = field(default_factory=list)
    status: str = "draft"  # draft, active, paused
    created_at: str = ""
    updated_at: str = ""


class VisualWorkflowEngine:
    """
    Motor de workflows visuales sin código.
    """
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.data_dir = Path(config.memory_dir) / "workflows"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.workflows_file = self.data_dir / "workflows.json"
        self.workflows: Dict[str, Workflow] = self._load_workflows()
    
    def _load_workflows(self) -> Dict[str, Workflow]:
        """Carga workflows desde archivo."""
        try:
            if self.workflows_file.exists():
                with open(self.workflows_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return {
                        wf_id: Workflow(
                            workflow_id=wf["workflow_id"],
                            name=wf["name"],
                            description=wf["description"],
                            nodes=[
                                WorkflowNode(
                                    node_id=n["node_id"],
                                    node_type=NodeType(n["node_type"]),
                                    config=n.get("config", {}),
                                    position=n.get("position", {}),
                                    connections=n.get("connections", [])
                                )
                                for n in wf.get("nodes", [])
                            ],
                            status=wf.get("status", "draft"),
                            created_at=wf.get("created_at", ""),
                            updated_at=wf.get("updated_at", "")
                        )
                        for wf_id, wf in data.items()
                    }
            return {}
        except Exception:
            return {}
    
    def _save_workflows(self):
        """Guarda workflows."""
        try:
            data = {
                wf_id: {
                    "workflow_id": wf.workflow_id,
                    "name": wf.name,
                    "description": wf.description,
                    "nodes": [
                        {
                            "node_id": n.node_id,
                            "node_type": n.node_type.value,
                            "config": n.config,
                            "position": n.position,
                            "connections": n.connections
                        }
                        for n in wf.nodes
                    ],
                    "status": wf.status,
                    "created_at": wf.created_at,
                    "updated_at": wf.updated_at
                }
                for wf_id, wf in self.workflows.items()
            }
            with open(self.workflows_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error guardando workflows: {e}")
    
    def create_workflow(self, name: str, description: str = "") -> Workflow:
        """Crea nuevo workflow."""
        import uuid
        from datetime import datetime
        
        workflow_id = str(uuid.uuid4())
        workflow = Workflow(
            workflow_id=workflow_id,
            name=name,
            description=description,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )
        
        self.workflows[workflow_id] = workflow
        self._save_workflows()
        
        return workflow
    
    def add_node(
        self,
        workflow_id: str,
        node_type: NodeType,
        config: Dict[str, Any] = None,
        position: Dict[str, float] = None
    ) -> WorkflowNode:
        """Agrega nodo a workflow."""
        import uuid
        
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow {workflow_id} no encontrado")
        
        node_id = str(uuid.uuid4())
        node = WorkflowNode(
            node_id=node_id,
            node_type=node_type,
            config=config or {},
            position=position or {"x": 0, "y": 0}
        )
        
        workflow.nodes.append(node)
        workflow.updated_at = datetime.now().isoformat()
        self._save_workflows()
        
        return node
    
    def connect_nodes(self, workflow_id: str, from_node_id: str, to_node_id: str):
        """Conecta dos nodos en workflow."""
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow {workflow_id} no encontrado")
        
        from_node = next((n for n in workflow.nodes if n.node_id == from_node_id), None)
        if from_node:
            if to_node_id not in from_node.connections:
                from_node.connections.append(to_node_id)
                workflow.updated_at = datetime.now().isoformat()
                self._save_workflows()
    
    def execute_workflow(self, workflow_id: str, trigger_data: Dict[str, Any] = None):
        """Ejecuta workflow."""
        workflow = self.workflows.get(workflow_id)
        if not workflow or workflow.status != "active":
            return {"success": False, "message": "Workflow no activo"}
        
        # Ejecutar nodos en orden
        results = []
        executed_nodes = set()
        
        # Encontrar nodos trigger
        trigger_nodes = [n for n in workflow.nodes if n.node_type == NodeType.TRIGGER]
        
        for trigger in trigger_nodes:
            result = self._execute_node(trigger, trigger_data or {})
            results.append(result)
            executed_nodes.add(trigger.node_id)
            
            # Ejecutar nodos conectados
            self._execute_connected_nodes(workflow, trigger, executed_nodes, results)
        
        return {
            "success": True,
            "workflow_id": workflow_id,
            "results": results
        }
    
    def _execute_node(self, node: WorkflowNode, data: Dict[str, Any]) -> Dict[str, Any]:
        """Ejecuta un nodo individual."""
        if node.node_type == NodeType.ACTION:
            action = node.config.get("action", "")
            # Ejecutar acción según configuración
            return {"node_id": node.node_id, "action": action, "result": "executed"}
        
        elif node.node_type == NodeType.CONDITION:
            condition = node.config.get("condition", "")
            # Evaluar condición
            return {"node_id": node.node_id, "condition": condition, "result": True}
        
        return {"node_id": node.node_id, "result": "executed"}
    
    def _execute_connected_nodes(
        self,
        workflow: Workflow,
        node: WorkflowNode,
        executed_nodes: set,
        results: list
    ):
        """Ejecuta nodos conectados recursivamente."""
        for connected_id in node.connections:
            if connected_id in executed_nodes:
                continue
            
            connected_node = next((n for n in workflow.nodes if n.node_id == connected_id), None)
            if connected_node:
                result = self._execute_node(connected_node, {})
                results.append(result)
                executed_nodes.add(connected_id)
                
                # Continuar con nodos conectados
                self._execute_connected_nodes(workflow, connected_node, executed_nodes, results)

