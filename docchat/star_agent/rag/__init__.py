"""RAG avanzado para STAR AGENT.

Sistema multi-agente RAG con:
- Docling para procesamiento de PDFs complejos
- Hybrid Retrieval (BM25 + Vector Search)
- Scope Checking
- Research Agent optimizado
- Advanced RAG Manager con índices separados
"""

from .rag_manager import RAGManager
from .document_processor import DocumentProcessor
from .hybrid_retriever import HybridRetriever, build_hybrid_retriever
from .research_agent import ResearchAgent
from .scope_checker import ScopeChecker
from .advanced_rag_manager import AdvancedRAGManager, IntentType as RAGIntentType

__all__ = [
    "RAGManager",
    "DocumentProcessor",
    "HybridRetriever",
    "build_hybrid_retriever",
    "ResearchAgent",
    "ScopeChecker",
    "AdvancedRAGManager",
    "RAGIntentType",
]
