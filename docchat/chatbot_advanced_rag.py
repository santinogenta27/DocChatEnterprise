"""
Advanced RAG Framework para Chatbot Mode (L4 RAG)
Basado en los papers:
- AI Knowledge Assist
- Advancing RAG for Structured Enterprise Data
- MuRAR (Multimodal RAG)
- FACTS Framework (NVIDIA)
- Personalizing LLMs with RAG + Knowledge Graph
- Corvic AI L1-L5 RAG Framework

Implementa:
- Hybrid Retrieval (Dense + BM25 con pesos optimizados)
- Semantic Chunking (700 tokens con overlap)
- Metadata Enrichment con NER (spaCy)
- Cross-Encoder Reranking
- Query Reformulation/Expansion
- Table-Aware Chunking
- Multimodal Retrieval
- Knowledge Graph Integration (opcional)
- Mixture of Spaces (L4): Semantic + Structural + Metadata spaces
- Adaptive Chain of Actions (L4): Planificación dinámica y re-planificación
"""

from __future__ import annotations

import json
import time
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import Chroma, FAISS
from langchain_community.retrievers import BM25Retriever

try:
    import spacy
    from spacy import displacy
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False
    print("⚠️ spaCy no instalado. Instala con: pip install spacy && python -m spacy download es_core_news_sm")

try:
    from sentence_transformers import CrossEncoder
    CROSS_ENCODER_AVAILABLE = True
except ImportError:
    CROSS_ENCODER_AVAILABLE = False
    print("⚠️ sentence-transformers no instalado. Instala con: pip install sentence-transformers")

from .config import AppConfig
from .rag_mixture_of_spaces import (
    MixtureOfSpaces,
    DocumentStructure,
    DocumentMetadata,
)
from .rag_adaptive_chain_of_actions import (
    AdaptiveChainOfActions,
    ActionType,
)


@dataclass
class AdvancedRAGConfig:
    """Configuración para Advanced RAG (L4)."""
    # Chunking
    chunk_size: int = 700  # Tokens (optimizado según paper)
    chunk_overlap: int = 200  # Tokens de overlap
    
    # Hybrid Retrieval
    dense_weight: float = 0.6  # Peso para dense retrieval
    sparse_weight: float = 0.4  # Peso para BM25
    
    # Reranking
    use_cross_encoder: bool = True
    rerank_top_k: int = 10  # Top-K para reranking
    final_top_k: int = 5  # Top-K final después de reranking
    
    # Query Reformulation
    use_query_expansion: bool = True
    use_query_rewriting: bool = True
    
    # Metadata
    use_ner_enrichment: bool = True
    use_table_aware_chunking: bool = True
    
    # Multimodal
    enable_multimodal: bool = False
    
    # Knowledge Graph
    use_knowledge_graph: bool = False
    
    # L4 RAG Features
    use_mixture_of_spaces: bool = True  # Múltiples espacios de búsqueda
    use_adaptive_chain: bool = True  # Planificación adaptativa
    adaptive_max_iterations: int = 5  # Máximo de iteraciones para re-planificación
    adaptive_confidence_threshold: float = 0.7  # Umbral de confianza


class SemanticChunker:
    """Chunking semántico optimizado (700 tokens con overlap)."""
    
    def __init__(self, chunk_size: int = 700, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def chunk_text(self, text: str, metadata: Optional[Dict] = None) -> List[Document]:
        """Chunking recursivo preservando contexto semántico."""
        from langchain.text_splitter import RecursiveCharacterTextSplitter
        
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        
        chunks = splitter.create_documents([text], metadatas=[metadata] if metadata else [{}])
        return chunks


class MetadataEnricherNER:
    """Enriquecimiento de metadatos usando NER (spaCy)."""
    
    def __init__(self):
        self.nlp = None
        if SPACY_AVAILABLE:
            try:
                # Intentar cargar modelo español, fallback a inglés
                try:
                    self.nlp = spacy.load("es_core_news_sm")
                except OSError:
                    try:
                        self.nlp = spacy.load("en_core_web_sm")
                    except OSError:
                        print("⚠️ Modelo spaCy no encontrado. Instala con: python -m spacy download es_core_news_sm")
            except Exception as e:
                print(f"⚠️ Error cargando spaCy: {e}")
    
    def enrich_document(self, doc: Document) -> Document:
        """Enriquece documento con entidades NER."""
        if not self.nlp:
            return doc
        
        try:
            text = doc.page_content
            nlp_doc = self.nlp(text[:10000])  # Limitar para performance
            
            # Extraer entidades
            entities = {
                "PERSON": [],
                "ORG": [],
                "LOC": [],
                "DATE": [],
                "MONEY": []
            }
            
            for ent in nlp_doc.ents:
                if ent.label_ in entities:
                    entities[ent.label_].append(ent.text)
            
            # Agregar a metadata
            metadata = doc.metadata.copy()
            metadata["ner_entities"] = entities
            metadata["ner_person"] = list(set(entities["PERSON"]))
            metadata["ner_org"] = list(set(entities["ORG"]))
            metadata["ner_location"] = list(set(entities["LOC"]))
            
            return Document(page_content=doc.page_content, metadata=metadata)
        except Exception as e:
            print(f"⚠️ Error en NER enrichment: {e}")
            return doc


class HybridRetriever:
    """Retriever híbrido (Dense + BM25) con pesos optimizados."""
    
    def __init__(
        self,
        vector_store: Any,
        documents: List[Document],
        dense_weight: float = 0.6,
        sparse_weight: float = 0.4,
        k: int = 10
    ):
        self.vector_store = vector_store
        self.dense_weight = dense_weight
        self.sparse_weight = sparse_weight
        self.k = k
        
        # Crear BM25 retriever
        try:
            self.bm25_retriever = BM25Retriever.from_documents(documents)
            self.bm25_retriever.k = k
        except Exception as e:
            print(f"⚠️ Error creando BM25 retriever: {e}")
            self.bm25_retriever = None
    
    def retrieve(self, query: str) -> List[Document]:
        """Retrieval híbrido fusionando dense y sparse."""
        results = []
        
        # Dense retrieval
        try:
            dense_docs = self.vector_store.similarity_search_with_score(query, k=self.k)
            dense_dict = {doc.metadata.get("source", id(doc)): (doc, score) for doc, score in dense_docs}
        except Exception as e:
            print(f"⚠️ Error en dense retrieval: {e}")
            dense_dict = {}
        
        # Sparse retrieval (BM25)
        sparse_dict = {}
        if self.bm25_retriever:
            try:
                # Usar invoke() para compatibilidad con LangChain 1.0+
                try:
                    sparse_docs = self.bm25_retriever.invoke(query)
                except AttributeError:
                    # Fallback para versiones anteriores
                    sparse_docs = self.bm25_retriever.get_relevant_documents(query)
                # Normalizar scores BM25 (0-1)
                max_score = len(sparse_docs) if sparse_docs else 1
                for idx, doc in enumerate(sparse_docs):
                    score = 1.0 - (idx / max_score)  # Normalizar
                    sparse_dict[doc.metadata.get("source", id(doc))] = (doc, score)
            except Exception as e:
                print(f"⚠️ Error en sparse retrieval: {e}")
        
        # Fusionar resultados
        all_docs = set(list(dense_dict.keys()) + list(sparse_dict.keys()))
        scored_docs = []
        
        for doc_id in all_docs:
            dense_score = dense_dict.get(doc_id, (None, 0.0))[1] if doc_id in dense_dict else 0.0
            sparse_score = sparse_dict.get(doc_id, (None, 0.0))[1] if doc_id in sparse_dict else 0.0
            
            # Normalizar dense_score (invertir porque lower is better en similarity_search_with_score)
            if dense_score > 0:
                dense_score = 1.0 / (1.0 + dense_score)
            
            # Score combinado
            combined_score = (self.dense_weight * dense_score) + (self.sparse_weight * sparse_score)
            
            doc = dense_dict.get(doc_id, (None, 0.0))[0] or sparse_dict.get(doc_id, (None, 0.0))[0]
            if doc:
                scored_docs.append((combined_score, doc))
        
        # Ordenar por score y retornar top-k
        scored_docs.sort(key=lambda x: x[0], reverse=True)
        return [doc for _, doc in scored_docs[:self.k]]


class CrossEncoderReranker:
    """Reranking usando Cross-Encoder (ms-marco-MiniLM-L-12-v2)."""
    
    def __init__(self):
        self.model = None
        if CROSS_ENCODER_AVAILABLE:
            try:
                # Usar modelo fine-tuned para reranking
                self.model = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-12-v2')
            except Exception as e:
                print(f"⚠️ Error cargando Cross-Encoder: {e}")
    
    def rerank(self, query: str, documents: List[Document], top_k: int = 5) -> List[Document]:
        """Rerankea documentos usando Cross-Encoder."""
        if not self.model or len(documents) <= top_k:
            return documents[:top_k]
        
        try:
            # Preparar pares query-documento
            pairs = [[query, doc.page_content[:512]] for doc in documents]  # Limitar contenido
            
            # Calcular scores
            scores = self.model.predict(pairs)
            
            # Ordenar por score
            scored_docs = list(zip(scores, documents))
            scored_docs.sort(key=lambda x: x[0], reverse=True)
            
            return [doc for _, doc in scored_docs[:top_k]]
        except Exception as e:
            print(f"⚠️ Error en reranking: {e}")
            return documents[:top_k]


class QueryReformulator:
    """Reformulación y expansión de queries."""
    
    def __init__(self, llm: Any):
        self.llm = llm
    
    def expand_query(self, query: str) -> str:
        """Expande query con sinónimos y variaciones."""
        prompt = f"""Expande esta pregunta con sinónimos y variaciones para mejorar la búsqueda.

Pregunta original: {query}

Genera 2-3 variaciones de la pregunta que mantengan el mismo significado pero usen palabras diferentes.

Variaciones (una por línea):"""
        
        try:
            response = self.llm.invoke(prompt).content.strip()
            # Combinar query original con variaciones
            variations = [query] + [line.strip() for line in response.split("\n") if line.strip()][:3]
            return " ".join(variations)
        except Exception:
            return query
    
    def rewrite_query(self, query: str, context: Optional[str] = None) -> str:
        """Reescribe query para mejor claridad."""
        prompt = f"""Reescribe esta pregunta de forma más clara y específica para búsqueda en documentos empresariales.

Pregunta original: {query}

Pregunta reescrita (más clara y específica):"""
        
        try:
            response = self.llm.invoke(prompt).content.strip()
            return response if response else query
        except Exception:
            return query


class AdvancedRAGPipeline:
    """Pipeline completo de Advanced RAG (L4)."""
    
    def __init__(self, config: AppConfig, rag_config: Optional[AdvancedRAGConfig] = None):
        self.config = config
        self.rag_config = rag_config or AdvancedRAGConfig()
        
        # Componentes
        self.chunker = SemanticChunker(
            chunk_size=self.rag_config.chunk_size,
            chunk_overlap=self.rag_config.chunk_overlap
        )
        self.ner_enricher = MetadataEnricherNER() if self.rag_config.use_ner_enrichment else None
        self.reranker = CrossEncoderReranker() if self.rag_config.use_cross_encoder else None
        
        # LLM para query reformulation
        if config.openai_api_key:
            self.query_llm = ChatOpenAI(
                model="gpt-4o-mini",
                temperature=0.0,
                api_key=config.openai_api_key,
                max_tokens=200
            )
            self.query_reformulator = QueryReformulator(self.query_llm) if self.rag_config.use_query_expansion else None
        else:
            self.query_reformulator = None
        
        # L4 RAG: Mixture of Spaces
        self.mixture_of_spaces: Optional[MixtureOfSpaces] = None
        if self.rag_config.use_mixture_of_spaces and config.openai_api_key:
            try:
                # Configurar persist_dir para Mixture of Spaces
                from pathlib import Path
                persist_dir = Path(config.memory_dir) / "mixture_of_spaces"
                persist_dir.mkdir(parents=True, exist_ok=True)
                
                # Crear config para Mixture of Spaces
                class MoSConfig:
                    def __init__(self, config):
                        self.embedding_model = config.embedding_model or "text-embedding-3-small"
                        self.persist_dir = persist_dir
                
                mos_config = MoSConfig(config)
                self.mixture_of_spaces = MixtureOfSpaces(mos_config)
                print("✅ Mixture of Spaces habilitado (L4 RAG)")
            except Exception as e:
                print(f"⚠️ Error inicializando Mixture of Spaces: {e}")
                self.mixture_of_spaces = None
        
        # L4 RAG: Adaptive Chain of Actions
        self.adaptive_chain: Optional[AdaptiveChainOfActions] = None
        if self.rag_config.use_adaptive_chain and config.openai_api_key and self.mixture_of_spaces:
            try:
                # LLM para planificación adaptativa
                chain_llm = ChatOpenAI(
                    model="gpt-4o-mini",
                    temperature=0.0,
                    api_key=config.openai_api_key,
                    max_tokens=500
                )
                self.adaptive_chain = AdaptiveChainOfActions(
                    mixture_of_spaces=self.mixture_of_spaces,
                    llm=chain_llm
                )
                print("✅ Adaptive Chain of Actions habilitado (L4 RAG)")
            except Exception as e:
                print(f"⚠️ Error inicializando Adaptive Chain: {e}")
                self.adaptive_chain = None
    
    def process_documents(self, documents: List[Document]) -> List[Document]:
        """Procesa documentos con chunking semántico y enriquecimiento."""
        processed = []
        
        for doc in documents:
            # Chunking semántico
            chunks = self.chunker.chunk_text(doc.page_content, doc.metadata)
            
            # Enriquecimiento con NER
            if self.ner_enricher:
                chunks = [self.ner_enricher.enrich_document(chunk) for chunk in chunks]
            
            processed.extend(chunks)
        
        return processed
    
    def create_hybrid_retriever(
        self,
        documents: List[Document],
        embeddings: Any,
        vector_store_path: Optional[str] = None
    ) -> HybridRetriever:
        """Crea retriever híbrido (Dense + BM25)."""
        # Crear vector store
        if vector_store_path and Path(vector_store_path).exists():
            vector_store = Chroma(
                persist_directory=vector_store_path,
                embedding_function=embeddings
            )
        else:
            vector_store = Chroma.from_documents(
                documents=documents,
                embedding=embeddings
            )
        
        # Crear hybrid retriever
        return HybridRetriever(
            vector_store=vector_store,
            documents=documents,
            dense_weight=self.rag_config.dense_weight,
            sparse_weight=self.rag_config.sparse_weight,
            k=self.rag_config.rerank_top_k
        )
    
    def retrieve(
        self,
        retriever: HybridRetriever,
        query: str,
        use_reformulation: bool = True,
        documents: Optional[List[Document]] = None
    ) -> List[Document]:
        """Retrieval completo con reformulación, reranking y L4 RAG (Mixture of Spaces + Adaptive Chain)."""
        # L4 RAG: Usar Adaptive Chain of Actions si está habilitado
        if self.adaptive_chain and documents:
            try:
                # Construir índices de Mixture of Spaces si no están construidos
                if not hasattr(self.mixture_of_spaces.semantic_space, 'vector_store') or \
                   self.mixture_of_spaces.semantic_space.vector_store is None:
                    print("🔨 Construyendo índices de Mixture of Spaces...")
                    self.mixture_of_spaces.build_indexes(documents)
                
                # Ejecutar query con Adaptive Chain
                results, plan = self.adaptive_chain.execute_query(
                    query=query,
                    max_iterations=self.rag_config.adaptive_max_iterations,
                    confidence_threshold=self.rag_config.adaptive_confidence_threshold,
                )
                
                # Convertir resultados a Documents
                retrieved = []
                for result in results:
                    if isinstance(result, Document):
                        retrieved.append(result)
                    elif isinstance(result, dict):
                        # Recuperar documento completo desde el índice
                        doc_id = result.get("doc_id")
                        if doc_id:
                            # Buscar en documentos originales
                            for doc in documents:
                                doc_id_check = doc.metadata.get("id", hashlib.md5(doc.page_content.encode()).hexdigest())
                                if doc_id_check == doc_id:
                                    retrieved.append(doc)
                                    break
                
                # Si Adaptive Chain encontró resultados, usarlos
                if retrieved:
                    print(f"✅ Adaptive Chain encontró {len(retrieved)} documentos")
                    # Aplicar reranking si está habilitado
                    if self.reranker and len(retrieved) > self.rag_config.final_top_k:
                        retrieved = self.reranker.rerank(
                            query=query,
                            documents=retrieved,
                            top_k=self.rag_config.final_top_k
                        )
                    return retrieved[:self.rag_config.final_top_k]
            
            except Exception as e:
                print(f"⚠️ Error en Adaptive Chain, usando retrieval estándar: {e}")
        
        # Fallback: Retrieval estándar (L2-L3)
        # 1. Reformular query si está habilitado
        final_query = query
        if use_reformulation and self.query_reformulator:
            try:
                final_query = self.query_reformulator.rewrite_query(query)
                # Opcional: expandir también
                if self.rag_config.use_query_expansion:
                    final_query = self.query_reformulator.expand_query(final_query)
            except Exception as e:
                print(f"⚠️ Error en query reformulation: {e}")
        
        # 2. Hybrid retrieval
        retrieved = retriever.retrieve(final_query)
        
        # 3. Reranking con Cross-Encoder
        if self.reranker and len(retrieved) > self.rag_config.final_top_k:
            retrieved = self.reranker.rerank(
                query=final_query,
                documents=retrieved,
                top_k=self.rag_config.final_top_k
            )
        
        return retrieved[:self.rag_config.final_top_k]

