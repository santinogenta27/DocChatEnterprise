"""
Workflow Builder - UI drag-and-drop para construir workflows de agentes
Similar a OpenAI Agent Builder pero integrado con documentos
"""

from __future__ import annotations

from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from .orchestrator import AgentOrchestrator, AgentWorkflow, AgentNode


@dataclass
class WorkflowNodeConfig:
    """Configuración de nodo para UI"""
    node_type: str  # "document_ingest", "llm_process", "database_write", etc.
    position: Dict[str, float]  # x, y para drag-and-drop
    connections: List[str] = None  # IDs de nodos conectados


class WorkflowBuilder:
    """
    Constructor visual de workflows
    Permite drag-and-drop de nodos y conexiones
    """
    
    def __init__(self, orchestrator: AgentOrchestrator):
        self.orchestrator = orchestrator
        self.workflow_configs: Dict[str, List[WorkflowNodeConfig]] = {}
    
    def create_workflow_from_ui(
        self,
        name: str,
        description: str,
        nodes: List[Dict[str, Any]]
    ) -> AgentWorkflow:
        """
        Crea workflow desde configuración de UI drag-and-drop
        
        nodes: [
            {
                "node_id": "node_1",
                "type": "document_ingest",
                "agent_id": "agent_123",
                "task": "Extraer información de documento",
                "position": {"x": 100, "y": 100},
                "connections": ["node_2"],
                "tools": ["mcp_document_reader"],
                "validation_rules": {...},
                "quality_checks": [...]
            },
            ...
        ]
        """
        workflow = self.orchestrator.create_workflow(name, description)
        
        # Crear nodos en orden de conexiones
        node_map = {n["node_id"]: n for n in nodes}
        created_nodes = {}
        
        # Primero crear todos los nodos
        for node_config in nodes:
            node = self.orchestrator.add_node(
                workflow_id=workflow.workflow_id,
                agent_id=node_config["agent_id"],
                task_description=node_config["task"],
                input_sources=node_config.get("input_sources", []),
                output_targets=node_config.get("output_targets", []),
                tools=node_config.get("tools", []),
                validation_rules=node_config.get("validation_rules", {}),
                quality_checks=node_config.get("quality_checks", []),
                temperature=node_config.get("temperature", 0.0),
                max_tokens=node_config.get("max_tokens", 2000)
            )
            created_nodes[node_config["node_id"]] = node
        
        # Luego establecer conexiones
        for node_config in nodes:
            node = created_nodes[node_config["node_id"]]
            connections = node_config.get("connections", [])
            
            # Actualizar output_targets con IDs reales
            for conn_id in connections:
                if conn_id in created_nodes:
                    target_node = created_nodes[conn_id]
                    if target_node.node_id not in node.output_targets:
                        node.output_targets.append(target_node.node_id)
                    if node.node_id not in target_node.input_sources:
                        target_node.input_sources.append(node.node_id)
        
        return workflow
    
    def get_workflow_visual_config(self, workflow_id: str) -> Dict[str, Any]:
        """Obtiene configuración visual del workflow para UI"""
        if workflow_id not in self.orchestrator.workflows:
            return {}
        
        workflow = self.orchestrator.workflows[workflow_id]
        
        nodes_visual = []
        for node in workflow.nodes:
            nodes_visual.append({
                "node_id": node.node_id,
                "agent_id": node.agent_id,
                "task": node.task_description,
                "status": node.status.value,
                "input_sources": node.input_sources,
                "output_targets": node.output_targets,
                "tools": node.tools,
                "run_count": node.run_count,
                "success_count": node.success_count,
                "failure_count": node.failure_count
            })
        
        return {
            "workflow_id": workflow_id,
            "name": workflow.name,
            "description": workflow.description,
            "nodes": nodes_visual,
            "total_runs": workflow.total_runs,
            "last_run": workflow.last_run
        }

