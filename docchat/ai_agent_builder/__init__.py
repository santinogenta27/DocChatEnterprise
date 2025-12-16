"""
AI Agent Builder Enterprise - Constructor de Agentes AI sin Código
Producto estrella que combina RAG, Multimodal AI, y Agentic AI

Características principales:
- Constructor visual de agentes sin código
- RAG avanzado (múltiples bases vectoriales, retrievers híbridos)
- Multimodal (texto, imágenes, audio, video)
- Frameworks agentic (LangChain, LangGraph, CrewAI, AG2, BAI Framework)
- Multi-model orchestration
- Templates pre-construidos
"""

from .agent_builder_core import AgentBuilderCore, AgentDefinition, AgentTemplate
from .rag_engine import AdvancedRAGEngine, VectorDatabaseManager, HybridRetriever
from .multimodal_processor import MultimodalProcessor, MediaType
from .agentic_frameworks import (
    LangGraphOrchestrator,
    CrewAIOrchestrator,
    AG2Orchestrator,
    BAIOrchestrator
)
from .model_orchestrator import ModelOrchestrator, ModelSelector
from .agent_templates import AgentTemplateLibrary
from .workflow_builder import WorkflowBuilder, WorkflowNode, WorkflowEdge
from .agent_evaluator import AgentEvaluator, BenchmarkSuite

__all__ = [
    "AgentBuilderCore",
    "AgentDefinition",
    "AgentTemplate",
    "AdvancedRAGEngine",
    "VectorDatabaseManager",
    "HybridRetriever",
    "MultimodalProcessor",
    "MediaType",
    "LangGraphOrchestrator",
    "CrewAIOrchestrator",
    "AG2Orchestrator",
    "BAIOrchestrator",
    "ModelOrchestrator",
    "ModelSelector",
    "AgentTemplateLibrary",
    "WorkflowBuilder",
    "WorkflowNode",
    "WorkflowEdge",
    "AgentEvaluator",
    "BenchmarkSuite"
]
