"""DocChat Enterprise - Multi-agent RAG system with autonomous agents."""

from .config import AppConfig, load_config  # noqa: F401
from .document_processor import DocumentProcessor  # noqa: F401
from .retriever_builder import RetrieverBuilder  # noqa: F401
from .workflow import AgentWorkflow  # noqa: F401
from .mass_processor import MassDocumentProcessor  # noqa: F401
from .memory import MemoryStore, ContextManager  # noqa: F401
from .audit import AuditLogger  # noqa: F401
from .autonomous_agent import AutonomousAgent, AgentTask  # noqa: F401
from .advanced_agent import AdvancedAutonomousAgent  # noqa: F401
from .enterprise_api import EnterpriseAPIMode  # noqa: F401
from .enterprise_agentic_ai import EnterpriseAgenticAI, IDPResult, AgenticTask  # noqa: F401
from .customer_service_agent import CustomerServiceAgent, CustomerInquiry, ServiceResponse
from .rpa_automation import RPAAutomationEngine, RPATask, RPAAutomation  # noqa: F401
from .rpa_enterprise_integration import RPAEnterpriseIntegration, EnterpriseConnection, RealtimeDataEvent  # noqa: F401
from .chatbot_mode import ChatbotMode, ChatbotConnection, RAGResponse  # noqa: F401
from .cloud_integrations import CloudStorageIntegration, WebhookProcessor  # noqa: F401
from .auth import UserManager, WorkspaceManager  # noqa: F401
from .integrations import (  # noqa: F401
    GmailIntegration, DriveIntegration, SlackIntegration,
    NotionIntegration, TeamsIntegration
)
from .tools import (  # noqa: F401
    EmailTool, ReportTool, DatabaseTool, PresentationTool,
    IntegrationTool, TableAnalysisTool, SchedulerTool
)

# Nuevos módulos de mejoras
from .cache.embedding_cache import EmbeddingCache, CachedOpenAIEmbeddings  # noqa: F401
from .async_processor import AsyncDocumentProcessor  # noqa: F401
from .streaming.response_streamer import ResponseStreamer  # noqa: F401
from .analytics.analytics_engine import AnalyticsEngine  # noqa: F401
from .security.encryption import DocumentEncryption, Watermarking  # noqa: F401
from .security.rbac import RBACManager, Role, Permission  # noqa: F401
from .rag.graph_rag import GraphRAG, KnowledgeGraph  # noqa: F401
from .rag.multimodal_rag import MultiModalRAG  # noqa: F401
from .rag.context_compression import ContextCompressor  # noqa: F401
from .integrations.premium_integrations import PremiumIntegrations, AutoSyncManager  # noqa: F401
from .workflows.visual_workflow import VisualWorkflowEngine, Workflow  # noqa: F401
from .observability.monitoring import MonitoringSystem  # noqa: F401

__version__ = "2.1.0"
__all__ = [
    "AppConfig",
    "load_config",
    "DocumentProcessor",
    "RetrieverBuilder",
    "AgentWorkflow",
    "MassDocumentProcessor",
    "MemoryStore",
    "ContextManager",
    "AuditLogger",
    "AutonomousAgent",
    "AgentTask",
    "AdvancedAutonomousAgent",
    "EnterpriseAPIMode",
    "EnterpriseAgenticAI",
    "IDPResult",
    "AgenticTask",
    "CustomerServiceAgent",
    "CustomerInquiry",
    "ServiceResponse",
    "RPAAutomationEngine",
    "RPATask",
    "RPAAutomation",
    "RPAEnterpriseIntegration",
    "EnterpriseConnection",
    "RealtimeDataEvent",
    "ChatbotMode",
    "ChatbotConnection",
    "RAGResponse",
    "CloudStorageIntegration",
    "WebhookProcessor",
    "UserManager",
    "WorkspaceManager",
    "GmailIntegration",
    "DriveIntegration",
    "SlackIntegration",
    "NotionIntegration",
    "TeamsIntegration",
    "EmailTool",
    "ReportTool",
    "DatabaseTool",
    "PresentationTool",
    "IntegrationTool",
    "TableAnalysisTool",
    "SchedulerTool",
    # Nuevos módulos
    "EmbeddingCache",
    "CachedOpenAIEmbeddings",
    "AsyncDocumentProcessor",
    "ResponseStreamer",
    "AnalyticsEngine",
    "DocumentEncryption",
    "Watermarking",
    "RBACManager",
    "Role",
    "Permission",
    "GraphRAG",
    "KnowledgeGraph",
    "MultiModalRAG",
    "ContextCompressor",
    "PremiumIntegrations",
    "AutoSyncManager",
    "VisualWorkflowEngine",
    "Workflow",
    "MonitoringSystem",
]
