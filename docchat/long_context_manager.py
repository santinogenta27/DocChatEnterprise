"""
Long Context Manager - Maneja context windows masivos (millones de tokens)
Basado en las ideas de Eric Schmidt sobre memoria a corto plazo masiva
"""

from __future__ import annotations

import time
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json
from collections import deque

from langchain_core.documents import Document
from langchain_core.language_models import BaseLanguageModel
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

from .config import AppConfig


class MemoryTier(str, Enum):
    """Niveles de memoria según recency y relevancia."""
    SHORT_TERM = "short_term"  # En el prompt del LLM (200k-1M tokens)
    MID_TERM = "mid_term"  # Vector DB (embeddings)
    LONG_TERM = "long_term"  # Cold storage (S3, archivos completos)


@dataclass
class ContextChunk:
    """Chunk de contexto con metadata."""
    content: str
    tokens: int
    recency_score: float  # 0-1, más reciente = más alto
    relevance_score: float  # 0-1, más relevante = más alto
    trust_score: float  # 0-1, confiabilidad
    certainty_score: float  # 0-1, certeza de la información
    source: str
    timestamp: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    chunk_id: str = field(default="")
    
    def __post_init__(self):
        if not self.chunk_id:
            self.chunk_id = hashlib.md5(
                f"{self.content}{self.timestamp}".encode()
            ).hexdigest()
    
    def get_priority_score(self) -> float:
        """Calcula score de prioridad para incluir en prompt."""
        # Combinación ponderada de todos los scores
        return (
            self.recency_score * 0.3 +
            self.relevance_score * 0.4 +
            self.trust_score * 0.15 +
            self.certainty_score * 0.15
        )


@dataclass
class WorkingSet:
    """Set de trabajo para una sesión."""
    session_id: str
    short_term_chunks: deque = field(default_factory=deque)  # Para prompt LLM
    total_tokens: int = 0
    max_tokens: int = 1_000_000  # 1M tokens por defecto
    last_updated: float = field(default_factory=time.time)
    
    def add_chunk(self, chunk: ContextChunk):
        """Agrega un chunk al working set."""
        # Si excede el límite, remover los menos prioritarios
        while (self.total_tokens + chunk.tokens > self.max_tokens and 
               len(self.short_term_chunks) > 0):
            removed = self.short_term_chunks.popleft()
            self.total_tokens -= removed.tokens
        
        self.short_term_chunks.append(chunk)
        self.total_tokens += chunk.tokens
        self.last_updated = time.time()
    
    def get_prompt_content(self, max_tokens: Optional[int] = None) -> str:
        """Obtiene contenido para el prompt, ordenado por prioridad."""
        chunks = list(self.short_term_chunks)
        chunks.sort(key=lambda c: c.get_priority_score(), reverse=True)
        
        if max_tokens:
            selected = []
            current_tokens = 0
            for chunk in chunks:
                if current_tokens + chunk.tokens <= max_tokens:
                    selected.append(chunk)
                    current_tokens += chunk.tokens
                else:
                    break
            chunks = selected
        
        return "\n\n".join([c.content for c in chunks])


class LongContextManager:
    """
    Gestiona context windows masivos usando arquitectura híbrida:
    - Short-term: LLM prompt (hasta 1M tokens)
    - Mid-term: Vector DB (embeddings)
    - Long-term: Cold storage
    """
    
    def __init__(
        self,
        config: AppConfig,
        llm: Optional[BaseLanguageModel] = None,
        max_short_term_tokens: int = 1_000_000
    ):
        self.config = config
        self.llm = llm
        self.max_short_term_tokens = max_short_term_tokens
        
        # Working sets por sesión
        self.working_sets: Dict[str, WorkingSet] = {}
        
        # Cache de compresiones
        self.compression_cache: Dict[str, str] = {}
        
        # Estadísticas
        self.stats = {
            "total_chunks_processed": 0,
            "total_tokens_managed": 0,
            "compressions_performed": 0,
            "cache_hits": 0
        }
    
    def get_or_create_working_set(self, session_id: str) -> WorkingSet:
        """Obtiene o crea un working set para una sesión."""
        if session_id not in self.working_sets:
            self.working_sets[session_id] = WorkingSet(
                session_id=session_id,
                max_tokens=self.max_short_term_tokens
            )
        return self.working_sets[session_id]
    
    def add_document(
        self,
        session_id: str,
        document: Document,
        recency_score: float = 1.0,
        relevance_score: float = 1.0,
        trust_score: float = 1.0,
        certainty_score: float = 1.0
    ) -> str:
        """
        Agrega un documento al context window.
        
        Si el documento es muy grande, puede comprimirlo o chunkearlo.
        """
        working_set = self.get_or_create_working_set(session_id)
        
        # Estimar tokens (aproximado: 1 token ≈ 4 caracteres)
        estimated_tokens = len(document.page_content) // 4
        
        # Si es muy grande, comprimir o chunkear
        if estimated_tokens > 100_000:  # > 100k tokens
            # Intentar comprimir
            compressed = self._compress_content(
                document.page_content,
                target_tokens=50_000
            )
            content = compressed
            estimated_tokens = len(compressed) // 4
        else:
            content = document.page_content
        
        chunk = ContextChunk(
            content=content,
            tokens=estimated_tokens,
            recency_score=recency_score,
            relevance_score=relevance_score,
            trust_score=trust_score,
            certainty_score=certainty_score,
            source=document.metadata.get("source", "unknown"),
            timestamp=time.time(),
            metadata=document.metadata
        )
        
        working_set.add_chunk(chunk)
        self.stats["total_chunks_processed"] += 1
        self.stats["total_tokens_managed"] += estimated_tokens
        
        return chunk.chunk_id
    
    def add_text(
        self,
        session_id: str,
        text: str,
        source: str = "user_input",
        recency_score: float = 1.0,
        relevance_score: float = 1.0
    ) -> str:
        """Agrega texto directo al context window."""
        document = Document(page_content=text, metadata={"source": source})
        return self.add_document(
            session_id,
            document,
            recency_score=recency_score,
            relevance_score=relevance_score
        )
    
    def get_context_for_prompt(
        self,
        session_id: str,
        max_tokens: Optional[int] = None,
        include_metadata: bool = False
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Obtiene el contexto optimizado para el prompt del LLM.
        
        Returns:
            (context_text, metadata_dict)
        """
        working_set = self.get_or_create_working_set(session_id)
        
        # Si no se especifica max_tokens, usar el límite del working set
        if max_tokens is None:
            max_tokens = working_set.max_tokens
        
        context_text = working_set.get_prompt_content(max_tokens=max_tokens)
        
        metadata = {
            "total_chunks": len(working_set.short_term_chunks),
            "total_tokens": working_set.total_tokens,
            "max_tokens": max_tokens,
            "session_id": session_id,
            "last_updated": working_set.last_updated
        }
        
        if include_metadata:
            metadata["chunks"] = [
                {
                    "chunk_id": c.chunk_id,
                    "source": c.source,
                    "tokens": c.tokens,
                    "priority_score": c.get_priority_score(),
                    "recency": c.recency_score,
                    "relevance": c.relevance_score
                }
                for c in list(working_set.short_term_chunks)
            ]
        
        return context_text, metadata
    
    def _compress_content(
        self,
        content: str,
        target_tokens: int = 50_000
    ) -> str:
        """
        Comprime contenido usando summarization.
        
        En producción, usaría un modelo de summarization dedicado.
        Por ahora, usa una estrategia simple.
        """
        # Check cache
        content_hash = hashlib.md5(content.encode()).hexdigest()
        if content_hash in self.compression_cache:
            self.stats["cache_hits"] += 1
            return self.compression_cache[content_hash]
        
        # Estrategia simple: tomar primeros y últimos párrafos + resumen
        # En producción, usar LLM para generar resumen semántico
        paragraphs = content.split("\n\n")
        if len(paragraphs) <= 10:
            # Ya es pequeño
            compressed = content
        else:
            # Tomar primeros 3, últimos 3, y un resumen del medio
            first = "\n\n".join(paragraphs[:3])
            last = "\n\n".join(paragraphs[-3:])
            middle_summary = f"[... {len(paragraphs) - 6} párrafos omitidos ...]"
            compressed = f"{first}\n\n{middle_summary}\n\n{last}"
        
        # Asegurar que no exceda target_tokens
        current_tokens = len(compressed) // 4
        if current_tokens > target_tokens:
            # Truncar si es necesario (en producción, usar mejor compresión)
            max_chars = target_tokens * 4
            compressed = compressed[:max_chars] + "... [truncado]"
        
        self.compression_cache[content_hash] = compressed
        self.stats["compressions_performed"] += 1
        
        return compressed
    
    def update_recency_scores(self, session_id: str, decay_factor: float = 0.95):
        """
        Actualiza scores de recency aplicando decay.
        
        Los chunks más antiguos pierden relevancia con el tiempo.
        """
        working_set = self.get_or_create_working_set(session_id)
        current_time = time.time()
        
        for chunk in working_set.short_term_chunks:
            age_hours = (current_time - chunk.timestamp) / 3600
            # Decay exponencial: cada hora, el score se multiplica por decay_factor
            chunk.recency_score *= (decay_factor ** age_hours)
    
    def clear_session(self, session_id: str):
        """Limpia el working set de una sesión."""
        if session_id in self.working_sets:
            del self.working_sets[session_id]
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del manager."""
        return {
            **self.stats,
            "active_sessions": len(self.working_sets),
            "total_working_sets_tokens": sum(
                ws.total_tokens for ws in self.working_sets.values()
            )
        }

