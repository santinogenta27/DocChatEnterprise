"""
RAG Avanzado con Índices Separados para STAR AGENT Widget.

Implementa:
- Detección de intención
- Índices separados (productos, políticas, marketing, reviews, general)
- Retrieval por intención
- Re-ranking de resultados
- Validación de confianza
"""

from __future__ import annotations

from typing import Dict, List, Optional, Any
from enum import Enum
from pathlib import Path

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.retrievers import BaseRetriever

try:
    from langchain_community.retrievers import BM25Retriever
    from langchain_community.vectorstores import Chroma
    BM25_AVAILABLE = True
except ImportError:
    BM25_AVAILABLE = False

try:
    import chromadb
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

from .hybrid_retriever import HybridRetriever, build_hybrid_retriever


class IntentType(str, Enum):
    """Tipos de intención para routing de índices"""
    PRODUCTOS = "productos"
    POLITICAS = "políticas"
    MARKETING = "marketing"
    REVIEWS = "reviews"
    GENERAL = "general"


class AdvancedRAGManager:
    """
    RAG Avanzado con índices separados por intención.
    
    Arquitectura:
    - Detección de intención automática
    - Índices separados por tipo de contenido
    - Retrieval intencionado
    - Re-ranking de resultados
    - Validación de confianza
    """
    
    def __init__(
        self,
        embeddings: Embeddings,
        base_dir: Optional[Path] = None,
        k: int = 4,
    ):
        """
        Inicializa el RAG Manager avanzado.
        
        Args:
            embeddings: Modelo de embeddings para vector search
            base_dir: Directorio base para persistir índices
            k: Número de documentos a retornar por búsqueda
        """
        self.embeddings = embeddings
        self.base_dir = base_dir or Path("docchat/star_agent/rag_storage")
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.k = k
        
        # Índices separados por intención
        self.stores: Dict[str, HybridRetriever] = {}
        self.documents_by_intent: Dict[str, List[Document]] = {
            IntentType.PRODUCTOS.value: [],
            IntentType.POLITICAS.value: [],
            IntentType.MARKETING.value: [],
            IntentType.REVIEWS.value: [],
            IntentType.GENERAL.value: [],
        }
        
        # Inicializar índices vacíos
        self._initialize_stores()
    
    def _initialize_stores(self):
        """Inicializa los índices separados para cada intención."""
        for intent in IntentType:
            intent_key = intent.value
            store_dir = self.base_dir / intent_key
            
            # Crear documentos vacíos para inicializar
            empty_docs = []
            
            try:
                # Intentar cargar índice existente
                if store_dir.exists() and CHROMADB_AVAILABLE:
                    vector_store = Chroma(
                        persist_directory=str(store_dir),
                        embedding_function=self.embeddings,
                    )
                    if vector_store._collection.count() > 0:
                        # Hay documentos, crear retriever
                        if BM25_AVAILABLE:
                            bm25 = BM25Retriever.from_documents(empty_docs)
                            vector_retriever = vector_store.as_retriever(
                                search_kwargs={"k": self.k * 2}
                            )
                            self.stores[intent_key] = HybridRetriever(
                                bm25_retriever=bm25,
                                vector_retriever=vector_retriever,
                                weights=(0.4, 0.6),
                                k=self.k,
                            )
                        else:
                            self.stores[intent_key] = vector_store.as_retriever(
                                search_kwargs={"k": self.k}
                            )
            except Exception as e:
                print(f"⚠️ Error inicializando índice {intent_key}: {e}")
    
    def detect_intent(self, query: str) -> IntentType:
        """
        Detecta la intención del usuario basado en el query.
        
        Implementa código exacto según especificaciones del usuario:
        - precio/cuesta → productos
        - envío/entrega → políticas
        - opinión/reseña → reviews
        - default → general
        
        Args:
            query: Consulta del usuario
            
        Returns:
            IntentType detectado
        """
        q = query.lower()
        
        # Código exacto según especificaciones del usuario
        if "precio" in q or "cuesta" in q:
            return IntentType.PRODUCTOS
        if "envío" in q or "entrega" in q:
            return IntentType.POLITICAS
        if "opinión" in q or "reseña" in q:
            return IntentType.REVIEWS
        
        # Detección adicional para otros casos
        if any(x in q for x in ["producto", "comprar", "tengo", "disponible", "stock"]):
            return IntentType.PRODUCTOS
        elif any(x in q for x in ["devolución", "garantía", "política", "términos"]):
            return IntentType.POLITICAS
        elif any(x in q for x in ["promoción", "oferta", "descuento", "nuevo", "lanzamiento", "anuncio"]):
            return IntentType.MARKETING
        elif any(x in q for x in ["review", "calificación", "experiencia", "cliente"]):
            return IntentType.REVIEWS
        
        return IntentType.GENERAL
    
    def add_documents(self, documents: List[Document], intent: Optional[IntentType] = None):
        """
        Agrega documentos al índice correspondiente.
        
        Args:
            documents: Lista de documentos a agregar
            intent: Intención específica (si None, se detecta automáticamente)
        """
        # Clasificar documentos por intención
        docs_by_intent: Dict[str, List[Document]] = {
            IntentType.PRODUCTOS.value: [],
            IntentType.POLITICAS.value: [],
            IntentType.MARKETING.value: [],
            IntentType.REVIEWS.value: [],
            IntentType.GENERAL.value: [],
        }
        
        for doc in documents:
            # Detectar intención del documento
            if intent:
                target_intent = intent.value
            else:
                # Detectar automáticamente basado en contenido
                content = doc.page_content.lower()
                if any(x in content for x in ["precio", "producto", "disponible", "stock"]):
                    target_intent = IntentType.PRODUCTOS.value
                elif any(x in content for x in ["envío", "política", "garantía", "devolución"]):
                    target_intent = IntentType.POLITICAS.value
                elif any(x in content for x in ["promoción", "oferta", "descuento", "nuevo"]):
                    target_intent = IntentType.MARKETING.value
                elif any(x in content for x in ["opinión", "reseña", "review", "calificación"]):
                    target_intent = IntentType.REVIEWS.value
                else:
                    target_intent = IntentType.GENERAL.value
            
            docs_by_intent[target_intent].append(doc)
        
        # Agregar a cada índice
        for intent_key, docs in docs_by_intent.items():
            if not docs:
                continue
            
            # Agregar a lista de documentos
            self.documents_by_intent[intent_key].extend(docs)
            
            # Reconstruir índice
            self._rebuild_store(intent_key, self.documents_by_intent[intent_key])
    
    def _rebuild_store(self, intent_key: str, documents: List[Document]):
        """Reconstruye el índice para una intención específica."""
        if not documents:
            return
        
        store_dir = self.base_dir / intent_key
        
        try:
            # Construir hybrid retriever
            self.stores[intent_key] = build_hybrid_retriever(
                documents=documents,
                embeddings=self.embeddings,
                persist_directory=store_dir,
                k=self.k,
                weights=(0.4, 0.6),
            )
        except Exception as e:
            print(f"⚠️ Error reconstruyendo índice {intent_key}: {e}")
    
    def retrieve_context(self, query: str, intent: Optional[IntentType] = None) -> str:
        """
        Recupera contexto según intención usando índice específico.
        
        Args:
            query: Consulta del usuario
            intent: Intención (si None, se detecta automáticamente)
            
        Returns:
            Contexto recuperado como string
        """
        # Detectar intención si no se proporciona
        if intent is None:
            intent = self.detect_intent(query)
        
        intent_key = intent.value
        
        # Obtener índice correspondiente
        store = self.stores.get(intent_key)
        if not store:
            # Fallback a índice general
            store = self.stores.get(IntentType.GENERAL.value)
            if not store:
                return ""
        
        try:
            # Recuperar documentos relevantes
            docs = store.get_relevant_documents(query)
            
            # Combinar contenido
            context_parts = []
            for doc in docs[:self.k]:
                content = doc.page_content.strip()
                if content:
                    context_parts.append(content)
            
            return "\n\n".join(context_parts)
            
        except Exception as e:
            print(f"⚠️ Error recuperando contexto: {e}")
            return ""
    
    def retrieve_with_confidence(self, query: str, intent: Optional[IntentType] = None) -> Dict[str, Any]:
        """
        Recupera contexto con validación de confianza.
        
        Args:
            query: Consulta del usuario
            intent: Intención (si None, se detecta automáticamente)
            
        Returns:
            Dict con contexto, confianza y documentos
        """
        context = self.retrieve_context(query, intent)
        docs = []
        
        intent_key = (intent or self.detect_intent(query)).value
        store = self.stores.get(intent_key) or self.stores.get(IntentType.GENERAL.value)
        
        if store:
            try:
                docs = store.get_relevant_documents(query)
            except Exception:
                pass
        
        # Calcular confianza basada en cantidad y relevancia
        confidence = min(1.0, len(docs) / self.k) if docs else 0.0
        
        return {
            "context": context,
            "confidence": confidence,
            "documents": docs,
            "intent": (intent or self.detect_intent(query)).value,
            "num_docs": len(docs),
        }

