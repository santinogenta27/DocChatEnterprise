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
    relevance_model: str = os.getenv("DOCCHAT_RELEVANCE_MODEL", "gpt-4o-mini")
    research_model: str = os.getenv("DOCCHAT_RESEARCH_MODEL", "gpt-4o")
    verification_model: str = os.getenv("DOCCHAT_VERIFICATION_MODEL", "gpt-4o-mini")
    embedding_model: str = os.getenv("DOCCHAT_EMBEDDING_MODEL", "text-embedding-3-large")
    agentic_model: str = os.getenv("DOCCHAT_AGENTIC_MODEL", "gpt-4o")
    temperature: float = float(os.getenv("DOCCHAT_TEMPERATURE", "0.15"))
    
    # API Keys
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")

    # Agentic AI Settings
    enable_autonomous_agents: bool = os.getenv("DOCCHAT_ENABLE_AGENTS", "true").lower() == "true"
    max_agent_iterations: int = 10
    agent_timeout_seconds: int = 300
    
    # Document Processing Timeout
    document_timeout_seconds: int = int(os.getenv("DOCCHAT_DOC_TIMEOUT", "60"))  # 1 minuto por defecto (optimizado)

    # Memory & Context
    enable_memory: bool = os.getenv("DOCCHAT_ENABLE_MEMORY", "true").lower() == "true"
    memory_retention_days: int = 365
    context_window_size: int = 10000

    # Integrations
    enable_slack: bool = os.getenv("DOCCHAT_ENABLE_SLACK", "false").lower() == "true"
    enable_teams: bool = os.getenv("DOCCHAT_ENABLE_TEAMS", "false").lower() == "true"
    enable_webhooks: bool = os.getenv("DOCCHAT_ENABLE_WEBHOOKS", "true").lower() == "true"
    slack_webhook_url: str = os.getenv("SLACK_WEBHOOK_URL", "")
    teams_webhook_url: str = os.getenv("TEAMS_WEBHOOK_URL", "")

    # Database connections
    postgres_url: str = os.getenv("POSTGRES_URL", "")
    mongodb_url: str = os.getenv("MONGODB_URL", "")
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379")

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

