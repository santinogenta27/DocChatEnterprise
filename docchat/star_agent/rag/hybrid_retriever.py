"""Hybrid Retriever (BM25 + Vector Search) para STAR AGENT.

Combina bÃºsqueda por keywords (BM25) y semÃ¡ntica (vector) para mejor precisiÃ³n.
"""

from __future__ import annotations

from typing import List, Optional, Any
from pathlib import Path

try:
    from langchain_community.retrievers import BM25Retriever
    from langchain_community.vectorstores import Chroma
    from langchain_core.retrievers import BaseRetriever
    from langchain_core.documents import Document
    from langchain_core.embeddings import Embeddings
    BM25_AVAILABLE = True
except ImportError:
    BM25_AVAILABLE = False
    BM25Retriever = None
    BaseRetriever = None

try:
    import chromadb
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False


class HybridRetriever(BaseRetriever):
    """Retriever hÃ­brido que combina BM25 y Vector Search."""
    
    def __init__(
        self,
        bm25_retriever: BM25Retriever,
        vector_retriever: BaseRetriever,
        weights: tuple[float, float] = (0.4, 0.6),
        k: int = 5,
    ):
        """Inicializa el Hybrid Retriever.
        
        Args:
            bm25_retriever: Retriever BM25 (keywords)
            vector_retriever: Retriever vectorial (semÃ¡ntico)
            weights: Pesos para BM25 y Vector (default: 40% BM25, 60% Vector)
            k: NÃºmero de documentos a retornar
        """
        super().__init__()
        # Establecer atributos directamente
        self._bm25_retriever = bm25_retriever
        self._vector_retriever = vector_retriever
        self._bm25_weight = weights[0]
        self._vector_weight = weights[1]
        self._k = k
    
    @property
    def bm25_retriever(self):
        return self._bm25_retriever
    
    @property
    def vector_retriever(self):
        return self._vector_retriever
    
    @property
    def bm25_weight(self):
        return self._bm25_weight
    
    @property
    def vector_weight(self):
        return self._vector_weight
    
    @property
    def k(self):
        return self._k
    
    def get_relevant_documents(self, query: str, k: Optional[int] = None) -> List[Document]:
        """Método público para obtener documentos relevantes (compatibilidad con código legacy)."""
        return self._get_relevant_documents(query, k=k)
    
    def invoke(self, input: str, config: Optional[Any] = None, **kwargs) -> List[Document]:
        """Método invoke (nuevo estándar de LangChain)."""
        k = kwargs.get('k') or self._k
        return self._get_relevant_documents(input, k=k)
    
    def _get_relevant_documents(self, query: str, *, k: Optional[int] = None) -> List[Document]:
        """Obtiene documentos relevantes usando ambos retrievers.
        
        Args:
            query: Consulta del usuario
            k: NÃºmero de documentos a retornar (opcional, usa self.k si no se proporciona)
            
        Returns:
            Lista de documentos relevantes (combinados y rankeados)
        """
        k = k or self._k
        
        # Obtener resultados de ambos retrievers (usar invoke que es el método estándar en LangChain)
        # invoke es el método estándar en versiones recientes de LangChain
        if hasattr(self._bm25_retriever, 'invoke'):
            bm25_docs = self._bm25_retriever.invoke(query)
        else:
            bm25_docs = self._bm25_retriever.get_relevant_documents(query)
        
        if hasattr(self._vector_retriever, 'invoke'):
            vector_docs = self._vector_retriever.invoke(query)
        else:
            vector_docs = self._vector_retriever.get_relevant_documents(query)
        
        # Combinar y rankear documentos
        combined_docs = self._combine_and_rank(bm25_docs, vector_docs, query)
        
        # Retornar top-k
        return combined_docs[:k]
    
    def _combine_and_rank(
        self,
        bm25_docs: List[Document],
        vector_docs: List[Document],
        query: str
    ) -> List[Document]:
        """Combina y rankea documentos de ambos retrievers.
        
        Args:
            bm25_docs: Documentos de BM25
            vector_docs: Documentos de Vector Search
            query: Consulta original
            
        Returns:
            Lista de documentos rankeados
        """
        # Crear diccionario de scores
        doc_scores = {}
        
        # Asignar scores de BM25
        for i, doc in enumerate(bm25_docs):
            # Score inverso de posiciÃ³n (primer documento = mayor score)
            score = (len(bm25_docs) - i) / len(bm25_docs) if bm25_docs else 0
            doc_id = self._get_doc_id(doc)
            doc_scores[doc_id] = doc_scores.get(doc_id, 0) + score * self._bm25_weight
        
        # Asignar scores de Vector Search
        for i, doc in enumerate(vector_docs):
            score = (len(vector_docs) - i) / len(vector_docs) if vector_docs else 0
            doc_id = self._get_doc_id(doc)
            doc_scores[doc_id] = doc_scores.get(doc_id, 0) + score * self._vector_weight
        
        # Crear diccionario de documentos Ãºnicos
        unique_docs = {}
        for doc in bm25_docs + vector_docs:
            doc_id = self._get_doc_id(doc)
            if doc_id not in unique_docs:
                unique_docs[doc_id] = doc
        
        # Ordenar por score
        ranked_docs = sorted(
            unique_docs.items(),
            key=lambda x: doc_scores.get(x[0], 0),
            reverse=True
        )
        
        return [doc for _, doc in ranked_docs]
    
    def _get_doc_id(self, doc: Document) -> str:
        """Obtiene ID Ãºnico para un documento.
        
        Args:
            doc: Documento
            
        Returns:
            ID Ãºnico basado en contenido
        """
        import hashlib
        content = doc.page_content
        source = doc.metadata.get("source", "")
        return hashlib.sha256((content + source).encode()).hexdigest()[:16]


def build_hybrid_retriever(
    documents: List[Document],
    embeddings: Embeddings,
    persist_directory: Optional[Path] = None,
    k: int = 5,
    weights: tuple[float, float] = (0.4, 0.6),
) -> HybridRetriever:
    """Construye un Hybrid Retriever desde documentos.
    
    Args:
        documents: Lista de documentos para indexar
        embeddings: Modelo de embeddings para vector search
        persist_directory: Directorio para persistir ChromaDB (opcional)
        k: NÃºmero de documentos a retornar
        weights: Pesos para BM25 y Vector (default: 40% BM25, 60% Vector)
        
    Returns:
        HybridRetriever configurado
    """
    if not BM25_AVAILABLE:
        raise ImportError(
            "BM25Retriever no disponible. Instala langchain-community"
        )
    
    if not CHROMADB_AVAILABLE:
        raise ImportError(
            "ChromaDB no disponible. Instala con: pip install chromadb"
        )
    
    # Crear BM25 retriever (siempre reconstruir con todos los documentos para mantener consistencia)
    # BM25 necesita todos los documentos para funcionar correctamente
    bm25_retriever = BM25Retriever.from_documents(documents)
    bm25_retriever.k = k * 2  # Obtener mÃ¡s resultados para combinar
    
    # Crear Vector Store (ChromaDB) con persistencia
    # Nota: Cuando se reconstruye el índice, se pasan TODOS los documentos (existentes + nuevos)
    # Por lo tanto, siempre recreamos el store completo para evitar duplicados
    if persist_directory:
        persist_dir_str = str(persist_directory)
        
        # Siempre crear store con todos los documentos (reconstrucción completa)
        # Esto asegura que no haya duplicados y que BM25 y Vector estén sincronizados
        vector_store = Chroma.from_documents(
            documents=documents,
            embedding=embeddings,
            persist_directory=persist_dir_str,
        )
    else:
        # Sin persistencia
        vector_store = Chroma.from_documents(
            documents=documents,
            embedding=embeddings,
        )
    
    # Crear Vector Retriever
    vector_retriever = vector_store.as_retriever(
        search_kwargs={"k": k * 2}  # Obtener mÃ¡s resultados para combinar
    )
    
    # Crear Hybrid Retriever
    hybrid_retriever = HybridRetriever(
        bm25_retriever=bm25_retriever,
        vector_retriever=vector_retriever,
        weights=weights,
        k=k,
    )
    
    return hybrid_retriever

