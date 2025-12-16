"""
Advanced RAG Engine - Motor RAG avanzado
Soporta múltiples bases vectoriales, retrievers híbridos, y re-ranking
Basado en: Advanced RAG with Vector Databases and Retrievers
"""

from __future__ import annotations

import json
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

try:
    from langchain_community.vectorstores import Chroma, FAISS
    from langchain_community.embeddings import OpenAIEmbeddings
    from langchain_core.retrievers import BaseRetriever
    from langchain.retrievers import ContextualCompressionRetriever
    from langchain.retrievers.document_compressors import LLMChainExtractor
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False
    print("⚠️ LangChain RAG no disponible. Instala con: pip install langchain-community")

try:
    import chromadb
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False


@dataclass
class VectorDatabaseConfig:
    """Configuración de base de datos vectorial"""
    db_type: str  # "chroma", "faiss", "pinecone"
    name: str
    embedding_model: str = "text-embedding-3-small"
    persist_directory: Optional[str] = None
    collection_name: Optional[str] = None


class VectorDatabaseManager:
    """
    Gestor de múltiples bases de datos vectoriales
    Soporta Chroma, FAISS, y Pinecone
    """
    
    def __init__(self, config: Any):
        self.config = config
        self.databases: Dict[str, Any] = {}
        self.embeddings = None
        self._initialize_embeddings()
    
    def _initialize_embeddings(self):
        """Inicializa embeddings"""
        if not RAG_AVAILABLE:
            return
        
        api_key = getattr(self.config, 'openai_api_key', None)
        if api_key:
            self.embeddings = OpenAIEmbeddings(
                model="text-embedding-3-small",
                openai_api_key=api_key
            )
    
    def create_database(self, db_config: VectorDatabaseConfig) -> str:
        """Crea una nueva base de datos vectorial"""
        if db_config.db_type == "chroma":
            return self._create_chroma_db(db_config)
        elif db_config.db_type == "faiss":
            return self._create_faiss_db(db_config)
        elif db_config.db_type == "pinecone":
            return self._create_pinecone_db(db_config)
        else:
            raise ValueError(f"Tipo de base de datos no soportado: {db_config.db_type}")
    
    def _create_chroma_db(self, db_config: VectorDatabaseConfig) -> str:
        """Crea base de datos Chroma"""
        if not CHROMA_AVAILABLE or not self.embeddings:
            raise ImportError("Chroma y embeddings requeridos")
        
        persist_dir = db_config.persist_directory or (
            Path(self.config.memory_dir) / "vector_dbs" / db_config.name
            if self.config.memory_dir else Path("data/vector_dbs") / db_config.name
        )
        
        vectorstore = Chroma(
            collection_name=db_config.collection_name or db_config.name,
            embedding_function=self.embeddings,
            persist_directory=str(persist_dir)
        )
        
        self.databases[db_config.name] = {
            "type": "chroma",
            "vectorstore": vectorstore,
            "config": db_config
        }
        
        return db_config.name
    
    def _create_faiss_db(self, db_config: VectorDatabaseConfig) -> str:
        """Crea base de datos FAISS"""
        if not FAISS_AVAILABLE or not self.embeddings:
            raise ImportError("FAISS y embeddings requeridos")
        
        persist_dir = db_config.persist_directory or (
            Path(self.config.memory_dir) / "vector_dbs" / db_config.name
            if self.config.memory_dir else Path("data/vector_dbs") / db_config.name
        )
        persist_dir.mkdir(parents=True, exist_ok=True)
        
        # FAISS se crea cuando se agregan documentos
        # Por ahora, solo guardamos la configuración
        self.databases[db_config.name] = {
            "type": "faiss",
            "vectorstore": None,  # Se creará al agregar documentos
            "config": db_config,
            "persist_dir": persist_dir
        }
        
        return db_config.name
    
    def _create_pinecone_db(self, db_config: VectorDatabaseConfig) -> str:
        """Crea base de datos Pinecone"""
        # Implementación futura
        raise NotImplementedError("Pinecone será implementado próximamente")
    
    def get_retriever(
        self,
        db_name: str,
        retriever_type: str = "semantic",
        top_k: int = 5,
        search_type: str = "similarity"
    ) -> Optional[Any]:
        """
        Obtiene un retriever de una base de datos
        
        Args:
            db_name: Nombre de la base de datos
            retriever_type: "semantic", "keyword", "hybrid"
            top_k: Número de documentos a retornar
            search_type: "similarity", "mmr"
        """
        if db_name not in self.databases:
            return None
        
        db_info = self.databases[db_name]
        vectorstore = db_info["vectorstore"]
        
        if not vectorstore:
            # Si es FAISS y no existe, crear uno vacío
            if db_info["type"] == "faiss" and self.embeddings:
                try:
                    from langchain_community.vectorstores import FAISS
                    from langchain_core.documents import Document
                    # Crear vectorstore vacío
                    vectorstore = FAISS.from_documents([Document(page_content="")], self.embeddings)
                    db_info["vectorstore"] = vectorstore
                except Exception as e:
                    print(f"⚠️ Error creando FAISS vacío: {e}")
                    return None
            else:
                return None
        
        if retriever_type == "semantic":
            return vectorstore.as_retriever(
                search_type=search_type,
                search_kwargs={"k": top_k}
            )
        elif retriever_type == "keyword":
            # Keyword retriever (BM25) - implementación futura
            return vectorstore.as_retriever(
                search_type=search_type,
                search_kwargs={"k": top_k}
            )
        elif retriever_type == "hybrid":
            return self._create_hybrid_retriever(vectorstore, top_k)
        else:
            return vectorstore.as_retriever(
                search_type=search_type,
                search_kwargs={"k": top_k}
            )
    
    def _create_hybrid_retriever(self, vectorstore: Any, top_k: int) -> Any:
        """Crea retriever híbrido (semantic + keyword)"""
        # Por ahora, retorna semantic retriever
        # En el futuro, combinará semantic y BM25
        return vectorstore.as_retriever(
            search_type="similarity",
            search_kwargs={"k": top_k}
        )
    
    def add_documents(self, db_name: str, documents: List[Any], metadatas: Optional[List[Dict]] = None):
        """Agrega documentos a una base de datos"""
        if db_name not in self.databases:
            raise ValueError(f"Base de datos {db_name} no encontrada")
        
        db_info = self.databases[db_name]
        
        if db_info["type"] == "chroma":
            vectorstore = db_info["vectorstore"]
            if metadatas:
                vectorstore.add_documents(documents, metadatas=metadatas)
            else:
                vectorstore.add_documents(documents)
        elif db_info["type"] == "faiss":
            # Crear o cargar FAISS
            if db_info["vectorstore"] is None:
                from langchain_community.vectorstores import FAISS
                db_info["vectorstore"] = FAISS.from_documents(
                    documents,
                    self.embeddings
                )
            else:
                db_info["vectorstore"].add_documents(documents)
            
            # Guardar
            persist_path = db_info["persist_dir"] / f"{db_name}.faiss"
            db_info["vectorstore"].save_local(str(db_info["persist_dir"]))
        else:
            raise ValueError(f"Tipo de base de datos no soportado para agregar documentos: {db_info['type']}")


class HybridRetriever:
    """
    Retriever híbrido que combina múltiples estrategias
    - Semantic search (embeddings)
    - Keyword search (BM25)
    - Re-ranking
    """
    
    def __init__(self, retrievers: List[Any], weights: Optional[List[float]] = None):
        self.retrievers = retrievers
        self.weights = weights or [1.0 / len(retrievers)] * len(retrievers)
    
    def get_relevant_documents(self, query: str, top_k: int = 5) -> List[Any]:
        """Obtiene documentos relevantes usando estrategia híbrida"""
        all_docs = []
        doc_scores = {}
        
        # Obtener documentos de cada retriever
        for retriever, weight in zip(self.retrievers, self.weights):
            docs = retriever.get_relevant_documents(query)
            for doc in docs:
                doc_id = doc.page_content[:50]  # ID simple
                if doc_id not in doc_scores:
                    doc_scores[doc_id] = {"doc": doc, "score": 0.0}
                doc_scores[doc_id]["score"] += weight
        
        # Ordenar por score
        sorted_docs = sorted(
            doc_scores.values(),
            key=lambda x: x["score"],
            reverse=True
        )
        
        return [item["doc"] for item in sorted_docs[:top_k]]


class AdvancedRAGEngine:
    """
    Motor RAG avanzado con múltiples bases vectoriales,
    retrievers híbridos, y re-ranking
    """
    
    def __init__(self, config: Any):
        self.config = config
        self.db_manager = VectorDatabaseManager(config)
        self.retrievers: Dict[str, Any] = {}
    
    def setup_rag(
        self,
        db_configs: List[VectorDatabaseConfig],
        retriever_type: str = "hybrid",
        top_k: int = 5,
        rerank_enabled: bool = False
    ) -> str:
        """
        Configura RAG con múltiples bases de datos
        
        Returns:
            rag_id: ID de la configuración RAG
        """
        # Crear bases de datos
        db_names = []
        for db_config in db_configs:
            db_name = self.db_manager.create_database(db_config)
            db_names.append(db_name)
        
        # Crear retrievers
        retrievers = []
        for db_name in db_names:
            retriever = self.db_manager.get_retriever(
                db_name,
                retriever_type=retriever_type,
                top_k=top_k
            )
            if retriever:
                retrievers.append(retriever)
        
        # Crear retriever híbrido si hay múltiples
        if len(retrievers) > 1:
            hybrid_retriever = HybridRetriever(retrievers)
            rag_id = f"rag_{len(self.retrievers)}"
            self.retrievers[rag_id] = hybrid_retriever
        elif len(retrievers) == 1:
            rag_id = f"rag_{len(self.retrievers)}"
            self.retrievers[rag_id] = retrievers[0]
        else:
            raise ValueError("No se pudieron crear retrievers")
        
        return rag_id
    
    def retrieve(self, rag_id: str, query: str, top_k: int = 5) -> List[Any]:
        """Recupera documentos relevantes"""
        if rag_id not in self.retrievers:
            raise ValueError(f"RAG {rag_id} no encontrado")
        
        retriever = self.retrievers[rag_id]
        
        # Si es HybridRetriever, usar su método
        if hasattr(retriever, 'get_relevant_documents'):
            try:
                # Intentar con top_k
                return retriever.get_relevant_documents(query, top_k=top_k)
            except TypeError:
                # Si no acepta top_k, usar sin parámetro
                docs = retriever.get_relevant_documents(query)
                return docs[:top_k] if len(docs) > top_k else docs
        elif hasattr(retriever, 'invoke'):
            # LangChain 0.2+ usa invoke
            docs = retriever.invoke(query)
            return docs[:top_k] if len(docs) > top_k else docs
        else:
            # Si es retriever de LangChain estándar
            docs = retriever.get_relevant_documents(query)
            return docs[:top_k] if len(docs) > top_k else docs
    
    def add_documents_to_db(self, db_name: str, documents: List[Any], metadatas: Optional[List[Dict]] = None):
        """Agrega documentos a una base de datos"""
        self.db_manager.add_documents(db_name, documents, metadatas)
