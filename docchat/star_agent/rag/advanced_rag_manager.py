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
    BM25_AVAILABLE = True
except ImportError:
    BM25_AVAILABLE = False

try:
    # Intentar usar la nueva versión de langchain-chroma
    from langchain_chroma import Chroma
except ImportError:
    # Fallback a la versión antigua
    try:
        from langchain_community.vectorstores import Chroma
    except ImportError:
        Chroma = None

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
        """Inicializa los índices separados para cada intención (lazy initialization)."""
        for intent in IntentType:
            intent_key = intent.value
            store_dir = self.base_dir / intent_key
            
            try:
                # Intentar cargar índice existente solo si existe el directorio y Chroma está disponible
                if store_dir.exists() and CHROMADB_AVAILABLE and Chroma is not None:
                    try:
                        vector_store = Chroma(
                            persist_directory=str(store_dir),
                            embedding_function=self.embeddings,
                        )
                        count = vector_store._collection.count()
                        
                        if count > 0:
                            # Hay documentos existentes - OPTIMIZACIÓN: no reconstruir desde cero
                            # Usar el vector store existente directamente (ya tiene embeddings en ChromaDB)
                            print(f"ℹ️ Índice {intent_key} existe con {count} documentos - cargando directamente (sin reconstruir embeddings)")
                            
                            # Usar el vector retriever directamente (ya tiene embeddings)
                            # Esto es MUCHO más rápido que reconstruir todo el hybrid retriever
                            try:
                                self.stores[intent_key] = vector_store.as_retriever(
                                    search_kwargs={"k": self.k}
                                )
                                
                                # Cargar documentos solo para referencia (sin crear embeddings)
                                # Esto es rápido porque solo lee texto desde ChromaDB
                                try:
                                    all_docs = vector_store.get(include=['documents', 'metadatas'], limit=1000)  # Limitar a 1000 para no cargar todo
                                    documents_list = []
                                    
                                    if all_docs and 'documents' in all_docs:
                                        from langchain_core.documents import Document
                                        docs_data = all_docs['documents']
                                        metadatas = all_docs.get('metadatas', [])
                                        
                                        for idx, doc_text in enumerate(docs_data):
                                            metadata = metadatas[idx] if idx < len(metadatas) else {}
                                            documents_list.append(Document(page_content=doc_text, metadata=metadata))
                                    
                                    # Guardar documentos para referencia (BM25 se construirá lazy cuando se use)
                                    self.documents_by_intent[intent_key] = documents_list
                                    print(f"✅ Índice {intent_key} cargado: {len(documents_list)} documentos (solo Vector Search - BM25 lazy si se necesita)")
                                except Exception as load_error:
                                    print(f"⚠️ Error cargando metadatos para {intent_key}: {load_error}")
                                    # Continuar con solo vector retriever
                                
                                continue  # Saltar al siguiente intent
                                
                            except Exception as vector_error:
                                print(f"⚠️ Error creando vector retriever para {intent_key}: {vector_error}")
                                # Continuar sin inicializar este store, se creará lazy cuando se agreguen documentos
                        else:
                            # Store existe pero está vacío, crear retriever placeholder
                            self.stores[intent_key] = vector_store.as_retriever(
                                search_kwargs={"k": self.k}
                            )
                            print(f"ℹ️ Índice {intent_key} inicializado (vacío)")
                    except Exception as chroma_error:
                        print(f"⚠️ Error accediendo a ChromaDB para {intent_key}: {chroma_error}")
                        # Continuar sin inicializar este store, se creará lazy cuando se agreguen documentos
                
                # Si no existe el directorio o no hay ChromaDB, no crear nada (lazy initialization)
                # El store se creará cuando se agreguen documentos por primera vez
                if intent_key not in self.stores:
                    print(f"ℹ️ Índice {intent_key} se inicializará lazy cuando se agreguen documentos")
                    
            except Exception as e:
                print(f"⚠️ Error inicializando índice {intent_key}: {e}")
                # No hacer traceback completo para evitar spam, solo continuar
                # El store se inicializará lazy cuando se necesite
    
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
        errors = []
        for intent_key, docs in docs_by_intent.items():
            if not docs:
                continue
            
            # Agregar a lista de documentos
            self.documents_by_intent[intent_key].extend(docs)
            
            # Reconstruir índice
            try:
                self._rebuild_store(intent_key, self.documents_by_intent[intent_key])
            except Exception as e:
                error_msg = str(e)
                errors.append(f"Error indexando documentos en {intent_key}: {error_msg}")
                # Continuar con otros índices aunque uno falle
        
        # Si hubo errores, lanzar excepción con todos los errores
        if errors:
            raise Exception("; ".join(errors))
    
    def _rebuild_store(self, intent_key: str, documents: List[Document]):
        """Reconstruye el índice para una intención específica."""
        if not documents:
            return
        
        store_dir = self.base_dir / intent_key
        
        # Construir hybrid retriever (propagar error si falla)
        self.stores[intent_key] = build_hybrid_retriever(
            documents=documents,
            embeddings=self.embeddings,
            persist_directory=store_dir,
            k=self.k,
            weights=(0.4, 0.6),
        )
    
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
            
            # Re-ranking de resultados (según especificaciones)
            # Ordenar por relevancia y limitar contexto
            docs = self._rerank_results(docs, query)
            
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
    
    def _rerank_results(self, docs: List[Document], query: str) -> List[Document]:
        """
        Re-rankear resultados según especificaciones.
        
        Implementa:
        - Scoring de relevancia basado en keywords
        - Ordenamiento por score
        - Limitación de contexto
        
        Args:
            docs: Lista de documentos recuperados
            query: Consulta original
            
        Returns:
            Lista de documentos re-rankeados
        """
        if not docs:
            return []
        
        # Scoring simple basado en keywords
        query_words = set(query.lower().split())
        scored_docs = []
        
        for doc in docs:
            content = doc.page_content.lower() if hasattr(doc, 'page_content') else str(doc).lower()
            content_words = set(content.split())
            
            # Calcular score: intersección de palabras
            intersection = query_words.intersection(content_words)
            score = len(intersection) / max(len(query_words), 1)
            
            # Bonus si el query está al inicio del documento
            if content.startswith(query.lower()[:20]):
                score += 0.2
            
            scored_docs.append((score, doc))
        
        # Ordenar por score (mayor a menor)
        scored_docs.sort(key=lambda x: x[0], reverse=True)
        
        # Retornar solo documentos (sin scores)
        return [doc for _, doc in scored_docs]

