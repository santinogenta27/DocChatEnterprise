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

__version__ = "2.0.0"
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
]
