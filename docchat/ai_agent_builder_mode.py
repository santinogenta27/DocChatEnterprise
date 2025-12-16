"""
AI Agent Builder Enterprise Mode
Modo principal que integra todos los componentes
"""

from __future__ import annotations

import json
from typing import Dict, Any, List, Optional
from pathlib import Path

from .config import AppConfig
try:
    from .ai_agent_builder.agent_builder_core import (
        AgentBuilderCore,
        AgentDefinition,
        AgentType,
        AgentCapability
    )
    from .ai_agent_builder.rag_engine import AdvancedRAGEngine, VectorDatabaseConfig
    from .ai_agent_builder.multimodal_processor import MultimodalProcessor, MediaType, MediaInput
    from .ai_agent_builder.agentic_frameworks import (
        LangGraphOrchestrator,
        CrewAIOrchestrator
    )
    from .ai_agent_builder.model_orchestrator import ModelOrchestrator
    from .ai_agent_builder.agent_templates import AgentTemplateLibrary
    from .ai_agent_builder.workflow_builder import WorkflowBuilder, WorkflowNode, WorkflowEdge, NodeType
    from .ai_agent_builder.agent_evaluator import AgentEvaluator, BenchmarkSuite
    AI_AGENT_BUILDER_MODULES_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Módulos de AI Agent Builder no disponibles: {e}")
    AI_AGENT_BUILDER_MODULES_AVAILABLE = False


class AIAgentBuilderMode:
    """
    AI Agent Builder Enterprise - Modo principal
    Constructor de agentes AI sin código que combina RAG, Multimodal, y Agentic AI
    """
    
    def __init__(self, config: AppConfig):
        self.config = config
        
        if not AI_AGENT_BUILDER_MODULES_AVAILABLE:
            raise ImportError("Módulos de AI Agent Builder no están disponibles. Instala dependencias.")
        
        # Inicializar componentes
        # Intentar obtener retriever_builder del sistema si está disponible
        retriever_builder = None
        try:
            from .retriever_builder import RetrieverBuilder
            retriever_builder = RetrieverBuilder(config)
        except Exception:
            pass
        
        self.agent_builder = AgentBuilderCore(config, retriever_builder=retriever_builder)
        self.rag_engine = AdvancedRAGEngine(config)
        self.multimodal_processor = MultimodalProcessor(config)
        self.langgraph_orchestrator = LangGraphOrchestrator(config)
        self.crewai_orchestrator = CrewAIOrchestrator(config)
        self.model_orchestrator = ModelOrchestrator(config)
        self.workflow_builder = WorkflowBuilder(config)
        self.agent_evaluator = AgentEvaluator(config)
        self.template_library = AgentTemplateLibrary()
        
        # Cargar agentes guardados
        try:
            self.agent_builder.load_agents()
        except Exception as e:
            print(f"⚠️ Error cargando agentes guardados: {e}")
        
        # Inicializar document processor para RAG
        try:
            from .document_processor import DocumentProcessor
            self.document_processor = DocumentProcessor(config)
        except Exception as e:
            print(f"⚠️ Error inicializando DocumentProcessor: {e}")
            self.document_processor = None
        
        print("✅ AI Agent Builder Enterprise inicializado")
    
    def create_agent_from_template(
        self,
        template_id: str,
        customizations: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Crea un agente desde un template
        
        Args:
            template_id: ID del template
            customizations: Personalizaciones opcionales
            
        Returns:
            agent_id: ID del agente creado
        """
        template = self.template_library.get_template(template_id)
        definition = template.agent_definition
        
        # Aplicar personalizaciones
        if customizations:
            definition_dict = definition.to_dict()
            definition_dict.update(customizations)
            definition = AgentDefinition.from_dict(definition_dict)
        
        # Crear agente
        agent_id = self.agent_builder.create_agent(definition)
        return agent_id
    
    def create_custom_agent(
        self,
        name: str,
        description: str,
        agent_type: str,
        capabilities: List[str],
        system_prompt: str,
        **kwargs
    ) -> str:
        """
        Crea un agente personalizado
        
        Args:
            name: Nombre del agente
            description: Descripción
            agent_type: "simple", "rag", "multimodal", "agentic", "hybrid"
            capabilities: Lista de capacidades
            system_prompt: Prompt del sistema
            **kwargs: Configuraciones adicionales
            
        Returns:
            agent_id
        """
        definition = AgentDefinition(
            name=name,
            description=description,
            agent_type=AgentType(agent_type),
            capabilities=[AgentCapability(c) for c in capabilities],
            system_prompt=system_prompt,
            **kwargs
        )
        
        agent_id = self.agent_builder.create_agent(definition)
        return agent_id
    
    def execute_agent(
        self,
        agent_id: str,
        input_data: Any,
        context: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Ejecuta un agente"""
        return self.agent_builder.execute_agent(agent_id, input_data, context)
    
    def list_agents(self) -> List[Dict[str, Any]]:
        """Lista todos los agentes"""
        return self.agent_builder.list_agents()
    
    def get_agent(self, agent_id: str) -> Optional[AgentDefinition]:
        """Obtiene un agente"""
        return self.agent_builder.get_agent(agent_id)
    
    def get_available_templates(self) -> List[Dict[str, Any]]:
        """Obtiene templates disponibles"""
        templates = self.template_library.get_all_templates()
        return [
            {
                "template_id": template_id,
                "name": template.name,
                "description": template.description,
                "category": template.category,
                "use_cases": template.use_cases,
                "complexity": template.complexity_level,
                "estimated_cost": template.estimated_cost_per_1k_requests
            }
            for template_id, template in templates.items()
        ]
    
    def setup_rag_for_agent(
        self,
        agent_id: str,
        db_configs: List[Dict[str, Any]],
        retriever_type: str = "hybrid",
        top_k: int = 5
    ) -> bool:
        """Configura RAG para un agente"""
        vector_configs = [
            VectorDatabaseConfig(**config) for config in db_configs
        ]
        
        rag_id = self.rag_engine.setup_rag(
            vector_configs,
            retriever_type=retriever_type,
            top_k=top_k
        )
        
        # Actualizar agente con RAG
        self.agent_builder.update_agent(agent_id, {
            "rag_enabled": True,
            "rag_id": rag_id
        })
        
        return True
    
    def evaluate_agent(
        self,
        agent_id: str,
        test_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Evalúa un agente"""
        agent = self.agent_builder.get_agent(agent_id)
        if not agent:
            raise ValueError(f"Agente {agent_id} no encontrado")
        
        # Crear executor
        def agent_executor(input_text: str):
            return self.agent_builder.execute_agent(agent_id, input_text)
        
        # Ejecutar evaluación
        results = self.agent_evaluator.evaluate_agent(
            agent_id,
            agent_executor,
            test_ids=test_ids
        )
        
        return results
    
    def create_workflow(
        self,
        workflow_id: str,
        name: str,
        nodes: List[Dict[str, Any]],
        edges: List[Dict[str, Any]]
    ) -> str:
        """Crea un workflow"""
        self.workflow_builder.create_workflow(workflow_id, name)
        
        # Agregar nodos
        for node_data in nodes:
            node = WorkflowNode(
                node_id=node_data["node_id"],
                node_type=NodeType(node_data["node_type"]),
                name=node_data["name"],
                config=node_data.get("config", {}),
                position=node_data.get("position", {"x": 0, "y": 0})
            )
            self.workflow_builder.add_node(workflow_id, node)
        
        # Agregar edges
        for edge_data in edges:
            edge = WorkflowEdge(
                edge_id=edge_data["edge_id"],
                from_node=edge_data["from_node"],
                to_node=edge_data["to_node"],
                condition=edge_data.get("condition"),
                label=edge_data.get("label")
            )
            self.workflow_builder.add_edge(workflow_id, edge)
        
        return workflow_id
