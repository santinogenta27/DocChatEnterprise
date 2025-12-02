"""Integrations module for LangGraph, CrewAI, and Composio."""

from .langgraph_integration import LangGraphIntegration, WorkflowState
from .crewai_integration import CrewAIIntegration
from .composio_integration import ComposioIntegration

# Exportar también los módulos existentes de integrations
try:
    from .integration_manager import IntegrationManager, IntegrationType, IntegrationConnection
except ImportError:
    pass

try:
    from .unified_search import UnifiedSearch
except ImportError:
    pass

try:
    from .oauth_handler import OAuthHandler
except ImportError:
    pass

__all__ = [
    "LangGraphIntegration",
    "WorkflowState",
    "CrewAIIntegration",
    "ComposioIntegration",
    "IntegrationManager",
    "IntegrationType",
    "IntegrationConnection",
    "UnifiedSearch",
    "OAuthHandler"
]
