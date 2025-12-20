from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

from dotenv import load_dotenv


load_dotenv()


@dataclass(slots=True)
class AppConfig:
    """Runtime configuration for DocChat Enterprise."""

    # Storage
    base_path: Path = Path.cwd()
    cache_dir: Path = field(default_factory=lambda: Path.cwd() / ".docchat_cache")
    persist_dir: Path = field(default_factory=lambda: Path.cwd() / ".docchat_vectordb")
    memory_dir: Path = field(default_factory=lambda: Path.cwd() / ".docchat_memory")
    audit_log_dir: Path = field(default_factory=lambda: Path.cwd() / ".docchat_audit")

    # Limits
    max_total_upload_mb: int = int(os.getenv("DOCCHAT_MAX_UPLOAD_MB", "5000"))  # 5GB default (aumentado para 1000 docs)
    max_documents_per_batch: int = int(os.getenv("DOCCHAT_MAX_DOCS", "1000"))  # Aumentado a 1000 documentos
    cache_expire_days: int = 30

    # Retrieval
    hybrid_weights: Sequence[float] = (0.45, 0.55)
    bm25_k: int = 50  # Aumentado significativamente para recuperar más documentos
    vector_k: int = 50  # Aumentado significativamente para recuperar más documentos
    max_retrieval_results: int = 100  # Aumentado para análisis de múltiples documentos

    # LLM defaults - Multi-model support
    # Actualizado para usar modelos con context windows grandes (128k tokens)
    relevance_model: str = os.getenv("DOCCHAT_RELEVANCE_MODEL", "gpt-4o")  # gpt-4o tiene 128k context window
    research_model: str = os.getenv("DOCCHAT_RESEARCH_MODEL", "gpt-4o")  # gpt-4o tiene 128k context window
    verification_model: str = os.getenv("DOCCHAT_VERIFICATION_MODEL", "gpt-4o")  # gpt-4o tiene 128k context window
    embedding_model: str = os.getenv("DOCCHAT_EMBEDDING_MODEL", "text-embedding-3-small")  # Cambiado a small: más rápido, calidad similar
    agentic_model: str = os.getenv("DOCCHAT_AGENTIC_MODEL", "gpt-4o")  # gpt-4o tiene 128k context window
    openai_model: str = os.getenv("DOCCHAT_OPENAI_MODEL", "gpt-4o")  # Modelo por defecto para OpenAI
    anthropic_model: str = os.getenv("DOCCHAT_ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")  # Modelo por defecto para Anthropic
    temperature: float = float(os.getenv("DOCCHAT_TEMPERATURE", "0.15"))
    
    # Speed/Quality Modes
    speed_mode: str = os.getenv("DOCCHAT_SPEED_MODE", "balanced")  # "fast", "balanced", "quality"
    # Fast mode: usa modelos más rápidos, menos tokens
    # Balanced: balance entre velocidad y calidad (default)
    # Quality: máxima calidad, más lento
    
    # API Keys
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "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")
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    
    # Groq Settings (Enterprise - Velocidad Extrema)
    use_groq: bool = os.getenv("DOCCHAT_USE_GROQ", "false").lower() == "true"
    groq_model: str = os.getenv("DOCCHAT_GROQ_MODEL", "llama-3.3-70b-versatile")  # Llama 3.3 70B en Groq
    groq_base_url: str = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
    
    # PostgreSQL Settings (Memoria de Largo Plazo)
    postgresql_enabled: bool = os.getenv("DOCCHAT_POSTGRESQL_ENABLED", "false").lower() == "true"
    postgresql_url: str = os.getenv("DATABASE_URL", "")  # Formato: postgresql://user:pass@host:port/db
    postgresql_pool_size: int = int(os.getenv("DOCCHAT_POSTGRESQL_POOL_SIZE", "10"))
    
    # n8n Integration Settings
    n8n_webhook_url: str = os.getenv("N8N_WEBHOOK_URL", "")  # URL del webhook de n8n para recibir eventos
    n8n_enabled: bool = os.getenv("DOCCHAT_N8N_ENABLED", "false").lower() == "true"
    
    # Chatbot Personalization (Business AI Omnicanal)
    chatbot_tone: str = os.getenv("DOCCHAT_CHATBOT_TONE", "friendly")  # friendly, professional, casual, formal, enthusiastic
    chatbot_personality: str = os.getenv("DOCCHAT_CHATBOT_PERSONALITY", "")  # Descripción libre de personalidad
    chatbot_custom_instructions: str = os.getenv("DOCCHAT_CHATBOT_CUSTOM_INSTRUCTIONS", "")  # Instrucciones personalizadas adicionales
    
    # RAG Configuration
    chatbot_rag_enabled: bool = os.getenv("DOCCHAT_CHATBOT_RAG_ENABLED", "false").lower() == "true"
    chatbot_documents_dir: str = os.getenv("DOCCHAT_CHATBOT_DOCUMENTS_DIR", "")  # Directorio de documentos para RAG
    
    # Lead Scoring Configuration
    chatbot_lead_scoring_enabled: bool = os.getenv("DOCCHAT_CHATBOT_LEAD_SCORING_ENABLED", "false").lower() == "true"
    chatbot_lead_questions: str = os.getenv("DOCCHAT_CHATBOT_LEAD_QUESTIONS", "")  # JSON con preguntas de calificación
    chatbot_lead_hot_threshold: int = int(os.getenv("DOCCHAT_CHATBOT_LEAD_HOT_THRESHOLD", "7"))  # Score mínimo para "Lead Caliente"
    
    # Handoff Configuration
    chatbot_handoff_keywords: str = os.getenv("DOCCHAT_CHATBOT_HANDOFF_KEYWORDS", "queja,fraude,hablar con humano,supervisor")  # Palabras clave para handoff
    chatbot_handoff_sentiment_threshold: float = float(os.getenv("DOCCHAT_CHATBOT_HANDOFF_SENTIMENT", "0.7"))  # Threshold de frustración
    
    # Language Configuration
    chatbot_default_language: str = os.getenv("DOCCHAT_CHATBOT_DEFAULT_LANGUAGE", "es")
    chatbot_multilingual_enabled: bool = os.getenv("DOCCHAT_CHATBOT_MULTILINGUAL", "false").lower() == "true"
    
    # Objection Handling
    chatbot_objection_responses: str = os.getenv("DOCCHAT_CHATBOT_OBJECTION_RESPONSES", "")  # JSON con respuestas a objeciones comunes

    # Agentic AI Settings
    enable_autonomous_agents: bool = os.getenv("DOCCHAT_ENABLE_AGENTS", "true").lower() == "true"
    max_agent_iterations: int = 10
    agent_timeout_seconds: int = 300
    
    # Document Processing Timeout
    document_timeout_seconds: int = int(os.getenv("DOCCHAT_DOC_TIMEOUT", "60"))  # 1 minuto por defecto (optimizado)

    # Memory & Context
    enable_memory: bool = os.getenv("DOCCHAT_ENABLE_MEMORY", "true").lower() == "true"
    memory_retention_days: int = 365
    context_window_size: int = 200000  # Actualizado a 200k tokens (máximo entre OpenAI 128k y Claude 200k)

    # Integrations
    enable_slack: bool = os.getenv("DOCCHAT_ENABLE_SLACK", "false").lower() == "true"
    enable_teams: bool = os.getenv("DOCCHAT_ENABLE_TEAMS", "false").lower() == "true"
    enable_webhooks: bool = os.getenv("DOCCHAT_ENABLE_WEBHOOKS", "true").lower() == "true"
    slack_webhook_url: str = os.getenv("SLACK_WEBHOOK_URL", "")
    teams_webhook_url: str = os.getenv("TEAMS_WEBHOOK_URL", "")
    
    # OAuth Credentials for Integrations
    google_client_id: str = os.getenv("GOOGLE_CLIENT_ID", "")
    google_client_secret: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    microsoft_client_id: str = os.getenv("MICROSOFT_CLIENT_ID", "")
    microsoft_client_secret: str = os.getenv("MICROSOFT_CLIENT_SECRET", "")
    slack_client_id: str = os.getenv("SLACK_CLIENT_ID", "")
    slack_client_secret: str = os.getenv("SLACK_CLIENT_SECRET", "")
    salesforce_client_id: str = os.getenv("SALESFORCE_CLIENT_ID", "")
    salesforce_client_secret: str = os.getenv("SALESFORCE_CLIENT_SECRET", "")
    salesforce_instance_url: str = os.getenv("SALESFORCE_INSTANCE_URL", "")
    jira_client_id: str = os.getenv("JIRA_CLIENT_ID", "")
    jira_client_secret: str = os.getenv("JIRA_CLIENT_SECRET", "")
    jira_url: str = os.getenv("JIRA_URL", "")
    github_client_id: str = os.getenv("GITHUB_CLIENT_ID", "")
    github_client_secret: str = os.getenv("GITHUB_CLIENT_SECRET", "")
    notion_client_id: str = os.getenv("NOTION_CLIENT_ID", "")
    notion_client_secret: str = os.getenv("NOTION_CLIENT_SECRET", "")
    zendesk_client_id: str = os.getenv("ZENDESK_CLIENT_ID", "")
    zendesk_client_secret: str = os.getenv("ZENDESK_CLIENT_SECRET", "")
    zendesk_url: str = os.getenv("ZENDESK_URL", "")
    servicenow_client_id: str = os.getenv("SERVICENOW_CLIENT_ID", "")
    servicenow_client_secret: str = os.getenv("SERVICENOW_CLIENT_SECRET", "")
    servicenow_instance_url: str = os.getenv("SERVICENOW_INSTANCE_URL", "")
    oauth_redirect_url: str = os.getenv("OAUTH_REDIRECT_URL", "http://localhost:7860/oauth/callback")

    # Database connections
    postgres_url: str = os.getenv("POSTGRES_URL", "")
    mongodb_url: str = os.getenv("MONGODB_URL", "")
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379")

    # Confluent/Kafka Streaming (Real-Time Data Streaming)
    enable_confluent_streaming: bool = os.getenv("ENABLE_CONFLUENT_STREAMING", "false").lower() == "true"
    confluent_bootstrap_servers: str = os.getenv("CONFLUENT_BOOTSTRAP_SERVERS", "")
    confluent_api_key: str = os.getenv("CONFLUENT_API_KEY", "")
    confluent_api_secret: str = os.getenv("CONFLUENT_API_SECRET", "")
    confluent_schema_registry_url: str = os.getenv("CONFLUENT_SCHEMA_REGISTRY_URL", "")
    # Kafka legacy (para compatibilidad)
    kafka_bootstrap_servers: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "")

    # Security
    enable_audit_logs: bool = os.getenv("DOCCHAT_ENABLE_AUDIT", "true").lower() == "true"
    encryption_key: str = os.getenv("DOCCHAT_ENCRYPTION_KEY", "")

    # Advanced Features
    enable_table_analysis: bool = True
    enable_visual_analysis: bool = True
    enable_comparative_analysis: bool = True
    parallel_processing: bool = True
    max_workers: int = int(os.getenv("DOCCHAT_MAX_WORKERS", "16"))  # Aumentado a 16 para 1000 documentos

    # Misc
    headers_to_split_on: Sequence[tuple[str, str]] = (
        ("#", "Heading 1"),
        ("##", "Heading 2"),
        ("###", "Heading 3"),
        ("####", "Heading 4"),
    )


def load_config() -> AppConfig:
    config = AppConfig()
    config.cache_dir.mkdir(exist_ok=True, parents=True)
    config.persist_dir.mkdir(exist_ok=True, parents=True)
    config.memory_dir.mkdir(exist_ok=True, parents=True)
    config.audit_log_dir.mkdir(exist_ok=True, parents=True)
    return config

