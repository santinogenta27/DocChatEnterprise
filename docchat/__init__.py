"""DocChat Enterprise - Multi-agent RAG system with autonomous agents."""

from .config import AppConfig, load_config  # noqa: F401
from .document_processor import DocumentProcessor  # noqa: F401
try:
    from docling.document_converter import DocumentConverter  # noqa: F401
except ImportError:
    DocumentConverter = None  # noqa: F401
from .retriever_builder import RetrieverBuilder  # noqa: F401
from .workflow import AgentWorkflow  # noqa: F401
from .mass_processor import MassDocumentProcessor  # noqa: F401
from .memory import MemoryStore, ContextManager  # noqa: F401
from .audit import AuditLogger  # noqa: F401
# AutonomousAgent ahora se importa desde la nueva implementación (línea 44)
from .advanced_agent import AdvancedAutonomousAgent  # noqa: F401
from .enterprise_api import EnterpriseAPIMode  # noqa: F401
from .enterprise_agentic_ai import EnterpriseAgenticAI, IDPResult, AgenticTask  # noqa: F401
from .customer_service_agent import CustomerServiceAgent, CustomerInquiry, ServiceResponse
from .rpa_automation import RPAAutomationEngine, RPATask, RPAAutomation  # noqa: F401
from .rpa_enterprise_integration import RPAEnterpriseIntegration, EnterpriseConnection, RealtimeDataEvent  # noqa: F401
from .chatbot_mode import ChatbotMode, ChatbotConnection, RAGResponse  # noqa: F401
from .leads_mode import LeadsMode, Lead, Message, Sequence  # noqa: F401
from .marketing_agent import MarketingAgent, CampaignCopy, AudienceSegment, MarketingCampaign, CampaignPerformance  # noqa: F401
from .semantic_data_engine import SemanticDataEngine, SemanticDocument, SemanticQuery, DataLineage, DataModality  # noqa: F401
from .cloud_integrations import CloudStorageIntegration, WebhookProcessor  # noqa: F401
from .auth import UserManager, WorkspaceManager  # noqa: F401
from .integrations import IntegrationManager, UnifiedSearch, OAuthHandler  # noqa: F401
from .tools import (  # noqa: F401
    EmailTool, ReportTool, DatabaseTool, PresentationTool,
    IntegrationTool, TableAnalysisTool, SchedulerTool
)
from .tools.crm_tool import CRMTool  # noqa: F401
from .tools.lead_generation_tool import LeadGenerationTool  # noqa: F401

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

# Next Generation Modules (Eric Schmidt)
from .long_context_manager import LongContextManager, ContextChunk, WorkingSet, MemoryTier  # noqa: F401
from .autonomous_agent import AutonomousAgent, Hypothesis, AgentMemory, AgentState  # noqa: F401
from .text_to_action import TextToAction, ActionPlan, ActionResult, ActionType, CodeSafetyChecker  # noqa: F401
# ChainOfThought importado más abajo con los nuevos módulos
from .adversarial_testing import AdversarialTester, AdversarialTest, TestSuite, AttackType, TestResult  # noqa: F401
from .next_gen_workflow import NextGenWorkflow, NextGenWorkflowConfig  # noqa: F401
from .expert_guide_nextgen import ExpertGuideNextGen  # noqa: F401
from .jarvis_agent import JarvisAgent, JarvisMemory, JarvisTask, JarvisInsight, JarvisAlert  # noqa: F401
from .jarvis_manager import JarvisManager  # noqa: F401
from .persistent_storage import PersistentStorage, DocumentRecord, QueryRecord, JarvisDataRecord  # noqa: F401
from .jarvis_api import JarvisAPI, WebhookPayload, AlertNotification, APIResponse, APIEndpoint  # noqa: F401
from .jarvis_api_server import JarvisAPIServer  # noqa: F401
from .mcp_server import MCPServer, MCPClient, MCPTool, MCPResource  # noqa: F401
from .mcp_manager import MCPManager, MCPConnection  # noqa: F401
from .schema_annotations import SchemaAnnotationManager, SchemaAnnotation, SchemaObjectType  # noqa: F401
from .custom_tasks import CustomTaskManager, CustomTask, TaskSchedule, TaskExecution  # noqa: F401
from .agent_templates import AgentTemplateManager, AgentTemplate, AgentTemplateType  # noqa: F401
# Advanced AI Capabilities (Eric Schmidt)
from .reinforcement_planning import ReinforcementPlanner, DecisionTree, DecisionNode  # noqa: F401
from .test_time_training import TestTimeTrainer, LearningEpisode, LearnedPattern  # noqa: F401
from .path_dependent_reasoning import PathDependentReasoner, ReasoningPath  # noqa: F401
from .goal_decomposition import GoalDecomposer, Goal, Subtask  # noqa: F401
# Chat Conversacional 2 - Modo avanzado para empresas
from .chat_conversational_2 import ChatConversational2, run_chat_conversational_2, get_chat_conversational_2  # noqa: F401
# Alien Mode - Clonado de Chat Conversational 2 Enterprise
from .alien_mode import AlienMode, run_alien_mode, get_alien_mode  # noqa: F401
from .invoice import InvoiceMode, run_invoice_mode, get_invoice_mode  # noqa: F401
from .context_folding import ContextFolder, ContextBranch, FoldedContext, BranchStatus  # noqa: F401
from .data_provenance import DataProvenanceTracker, DataProvenance, DataSourceType, ProvenanceRecord  # noqa: F401
from .chain_of_thought import ChainOfThoughtReasoner, ThoughtChain, ReasoningStep, ReasoningStepType  # noqa: F401
from .person_in_the_loop import PersonInTheLoop, HumanApproval, ApprovalRule, ApprovalStatus, DecisionCriticality  # noqa: F401
# Agent Orchestration Studio - Nuevo modo innovador
from .agent_orchestration_studio import (  # noqa: F401
    AgentOrchestrationStudio,
    SpecializedAgent,
    AgentRole,
    AgentStatus,
    Workflow,
    WorkflowStatus,
    WorkflowStep,
    AgentConnection,
    AgentMessage
)
# Agentic Workflow Orchestrator - Multi-agent workflows con CrewAI
from .agentic_workflow_orchestrator import (  # noqa: F401
    AgenticWorkflowOrchestrator,
    WorkflowAgent,
    WorkflowStep,
    WorkflowExecution,
    WorkflowStatus,
    AgentStatus,
)
from .agentic_memory import (  # noqa: F401
    AgenticMemory,
    RewardSignal,
    AgentDecision,
)
from .agentic_crewai_tools import (  # noqa: F401
    get_crewai_tools,
    get_tool_by_name,
    JiraCreateTicketTool,
    SlackSendMessageTool,
    TeamsSendMessageTool,
    EmailSendTool,
    SQLQueryTool,
    FileWriteTool,
    PDFExportTool,
)
from .agentic_rl_advanced import (  # noqa: F401
    AdvancedRLManager,
    QLearningAgent,
    PolicyGradientAgent,
    RLState,
    RLAction,
    RLExperience,
)
from .agentic_a2a_protocol import (  # noqa: F401
    A2AProtocol,
    AgentCard,
    A2AMessage,
    A2ATask,
    A2AArtifact,
    TaskStatus,
    MessageType,
)
from .agentic_mcp_a2a_bridge import (  # noqa: F401
    MCPA2ABridge,
    MCPToolCapability,
)
from .mcp_progressive_disclosure import (  # noqa: F401
    MCPProgressiveDisclosure,
    ToolDetailLevel,
    ResponseFormat,
    ToolSearchResult,
)
from .mcp_tool_optimizer import (  # noqa: F401
    MCPToolOptimizer,
    OptimizedToolDescription,
)
# Enterprise Data Intelligence - SQL Generation + Data Registry + Agent Registry
from .enterprise_data_intelligence import EnterpriseDataIntelligence, QueryResult  # noqa: F401
from .data_registry import (  # noqa: F401
    DataRegistry,
    DatabaseConnection,
    TableMetadata,
    ColumnMetadata,
    DataSource,
)
from .agent_registry import AgentRegistry, AgentMetadata, AgentParameter  # noqa: F401
from .sql_generation import SQLGenerator, SQLGenerationResult  # noqa: F401
from .sql_agents import (  # noqa: F401
    MultiAgentSQLFramework,
    SQLRunner,
    SQLEnhancer,
    SQLExecutionResult,
)
from .deep_research import DeepResearch, DeepResearchResult  # noqa: F401

__version__ = "2.1.0"
__all__ = [
    "AppConfig",
    "load_config",
    "DocumentProcessor",
    "DocumentConverter",
    "RetrieverBuilder",
    "AgentWorkflow",
    "MassDocumentProcessor",
    "MemoryStore",
    "ContextManager",
    "AuditLogger",
    "AutonomousAgent",  # Nueva implementación con Hypothesis, AgentMemory, AgentState
    "Hypothesis",
    "AgentMemory",
    "AgentState",
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
    "SemanticDataEngine",
    "SemanticDocument",
    "SemanticQuery",
    "DataLineage",
    "DataModality",
    "CloudStorageIntegration",
    "WebhookProcessor",
    "UserManager",
    "WorkspaceManager",
    "IntegrationManager",
    "UnifiedSearch",
    "OAuthHandler",
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
    # Next Generation (Eric Schmidt)
    "LongContextManager",
    "ContextChunk",
    "WorkingSet",
    "MemoryTier",
    "AutonomousAgent",
    "Hypothesis",
    "AgentMemory",
    "AgentState",
    "TextToAction",
    "ActionPlan",
    "ActionResult",
    "ActionType",
    "CodeSafetyChecker",
    "ChainOfThoughtReasoner",
    "ThoughtChain",
    "ReasoningStep",
    "ReasoningStepType",
    "AdversarialTester",
    "AdversarialTest",
    "TestSuite",
    "AttackType",
    "TestResult",
    "NextGenWorkflow",
    "NextGenWorkflowConfig",
    "ExpertGuideNextGen",
    "JarvisAgent",
    "JarvisManager",
    "JarvisMemory",
    "JarvisTask",
    "JarvisInsight",
    "JarvisAlert",
    "PersistentStorage",
    "DocumentRecord",
    "QueryRecord",
    "JarvisDataRecord",
    "JarvisAPI",
    "WebhookPayload",
    "AlertNotification",
    "APIResponse",
    "APIEndpoint",
    "JarvisAPIServer",
    # MCP (Model Context Protocol)
    "MCPServer",
    "MCPClient",
    "MCPTool",
    "MCPResource",
    "MCPManager",
    "MCPConnection",
    # Schema Annotations
    "SchemaAnnotationManager",
    "SchemaAnnotation",
    "SchemaObjectType",
    # Custom Tasks
    "CustomTaskManager",
    "CustomTask",
    "TaskSchedule",
    "TaskExecution",
    # Agent Templates
    "AgentTemplateManager",
    "AgentTemplate",
    "AgentTemplateType",
    # Advanced AI Capabilities (Eric Schmidt)
    "ReinforcementPlanner",
    "DecisionTree",
    "DecisionNode",
    "TestTimeTrainer",
    "LearningEpisode",
    "LearnedPattern",
    "PathDependentReasoner",
    "ReasoningPath",
    "GoalDecomposer",
    "Goal",
    "Subtask",
    # Chat Conversacional 2
    "ChatConversational2",
    "run_chat_conversational_2",
    "get_chat_conversational_2",
    # Alien Mode
    "AlienMode",
    "run_alien_mode",
    "get_alien_mode",
    "InvoiceMode",
    "run_invoice_mode",
    "get_invoice_mode",
    "ContextFolder",
    "ContextBranch",
    "FoldedContext",
    "BranchStatus",
    "DataProvenanceTracker",
    "DataProvenance",
    "DataSourceType",
    "ProvenanceRecord",
    "ChainOfThoughtReasoner",
    "ThoughtChain",
    "ReasoningStep",
    "ReasoningStepType",
    "PersonInTheLoop",
    "HumanApproval",
    "ApprovalRule",
    "ApprovalStatus",
    "DecisionCriticality",
    # Agent Orchestration Studio
    "AgentOrchestrationStudio",
    "SpecializedAgent",
    "AgentRole",
    "AgentStatus",
    "Workflow",
    "WorkflowStatus",
    "WorkflowStep",
    "AgentConnection",
    "AgentMessage",
    # Leads Mode
    "LeadsMode",
    "Lead",
    "Message",
    "Sequence",
    # Marketing Agent
    "MarketingAgent",
    "CampaignCopy",
    "AudienceSegment",
    "MarketingCampaign",
    "CampaignPerformance",
    # Enterprise Data Intelligence
    "EnterpriseDataIntelligence",
    "QueryResult",
    "DataRegistry",
    "DatabaseConnection",
    "TableMetadata",
    "ColumnMetadata",
    "DataSource",
    "AgentRegistry",
    "AgentMetadata",
    "AgentParameter",
    "SQLGenerator",
    "SQLGenerationResult",
    "MultiAgentSQLFramework",
    "SQLRunner",
    "SQLEnhancer",
    "SQLExecutionResult",
    # Deep Research Mode
    "DeepResearch",
    "DeepResearchResult",
    # Agentic Workflow Orchestrator
    "AgenticWorkflowOrchestrator",
    "WorkflowAgent",
    "WorkflowStep",
    "WorkflowExecution",
    "WorkflowStatus",
    "AgentStatus",
    "AgenticMemory",
    "RewardSignal",
    "AgentDecision",
    # Agentic CrewAI Tools
    "get_crewai_tools",
    "get_tool_by_name",
    "JiraCreateTicketTool",
    "SlackSendMessageTool",
    "TeamsSendMessageTool",
    "EmailSendTool",
    "SQLQueryTool",
    "FileWriteTool",
    "PDFExportTool",
    # Agentic RL Advanced
    "AdvancedRLManager",
    "QLearningAgent",
    "PolicyGradientAgent",
    "RLState",
    "RLAction",
    "RLExperience",
    # A2A Protocol
    "A2AProtocol",
    "AgentCard",
    "A2AMessage",
    "A2ATask",
    "A2AArtifact",
    "TaskStatus",
    "MessageType",
    # MCP × A2A Bridge
    "MCPA2ABridge",
    "MCPToolCapability",
    # MCP Progressive Disclosure
    "MCPProgressiveDisclosure",
    "ToolDetailLevel",
    "ResponseFormat",
    "ToolSearchResult",
    # MCP Tool Optimizer
    "MCPToolOptimizer",
    "OptimizedToolDescription",
]
