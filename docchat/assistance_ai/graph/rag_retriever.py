"""RAG Retriever - Recuperación contextual optimizada."""

from typing import List, Dict, Any, Optional
from pathlib import Path
import pickle


class RAGRetriever:
    """Retriever optimizado para customer service."""
    
    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = storage_dir or Path("docchat/assistance_ai/rag_storage")
        self.chunks = None
        self.vector_store = None
        self._load_retriever()
    
    def _load_retriever(self):
        """Carga el retriever desde el almacenamiento."""
        try:
            metadata_path = self.storage_dir / "retriever_metadata.pkl"
            if not metadata_path.exists():
                return
            
            with open(metadata_path, "rb") as f:
                metadata = pickle.load(f)
            
            persist_dir = metadata.get("persist_dir")
            if persist_dir and Path(persist_dir).exists():
                try:
                    from langchain_chroma import Chroma
                    from langchain_openai import OpenAIEmbeddings
                    import os
                    
                    api_key = os.getenv("OPENAI_API_KEY")
                    if api_key:
                        embeddings = OpenAIEmbeddings(
                            model="text-embedding-3-small",
                            openai_api_key=api_key
                        )
                        self.vector_store = Chroma(
                            persist_directory=str(persist_dir),
                            embedding_function=embeddings
                        )
                        print(f"✅ RAG Retriever cargado desde {persist_dir}")
                except Exception as e:
                    print(f"⚠️ Error cargando vector store: {e}")
        except Exception as e:
            print(f"⚠️ Error inicializando RAG Retriever: {e}")
    
    def retrieve(self, query: str, intent: str, top_k: int = 5, min_similarity: float = 0.75) -> List[Dict[str, Any]]:
        """Recupera documentos relevantes según la intención.
        
        Args:
            query: Consulta del usuario
            intent: Intención clasificada (para optimizar retrieval)
            top_k: Número de documentos a recuperar
            min_similarity: Similaridad mínima
        
        Returns:
            Lista de documentos con metadata
        """
        if not self.vector_store:
            return []
        
        try:
            # Optimizar query según intención
            optimized_query = self._optimize_query_for_intent(query, intent)
            
            # Retrieval semántico
            docs = self.vector_store.similarity_search_with_score(
                optimized_query,
                k=top_k
            )
            
            # Filtrar por min_similarity y formatear
            results = []
            for doc, score in docs:
                # Invertir score (Chroma devuelve distancia, menor es mejor)
                similarity = 1.0 - min(score, 1.0)
                
                if similarity >= min_similarity:
                    results.append({
                        "content": doc.page_content,
                        "metadata": doc.metadata,
                        "similarity": similarity,
                        "source": doc.metadata.get("source", "unknown")
                    })
            
            return results
        except Exception as e:
            print(f"⚠️ Error en retrieval: {e}")
            return []
    
    def _optimize_query_for_intent(self, query: str, intent: str) -> str:
        """Optimiza la query según la intención para mejorar retrieval."""
        intent_prefixes = {
            "consulta_productos": "producto información características",
            "soporte_tecnico": "problema error solución troubleshooting",
            "tracking_envio": "envío pedido estado seguimiento",
            "devolucion_reclamo": "devolución reembolso política reclamo",
            "compra_asistencia": "compra checkout carrito proceso",
        }
        
        prefix = intent_prefixes.get(intent, "")
        if prefix:
            return f"{prefix} {query}"
        return query

