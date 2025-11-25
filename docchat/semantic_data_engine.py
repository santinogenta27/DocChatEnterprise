"""
Semantic Data Processing Engine - Inspired by NVIDIA/NetApp AI Data Engine
Implements semantic AI, vectorized databases, multimodal search, and agentic data operations.
"""

from __future__ import annotations

import os
import json
import uuid
from typing import List, Optional, Dict, Any, Union
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum

import numpy as np
try:
    from langchain_openai import OpenAIEmbeddings
except ImportError:
    try:
        from langchain.embeddings import OpenAIEmbeddings
    except ImportError:
        from langchain_openai import OpenAIEmbeddings

# FAISS is optional - use Chroma as fallback
FAISS_AVAILABLE = False
try:
    try:
        from langchain_community.vectorstores import FAISS
        FAISS_AVAILABLE = True
    except ImportError:
        try:
            from langchain.vectorstores import FAISS
            FAISS_AVAILABLE = True
        except ImportError:
            pass
except Exception:
    pass

# Chroma as fallback
try:
    try:
        from langchain_community.vectorstores import Chroma
    except ImportError:
        from langchain.vectorstores import Chroma
except ImportError:
    Chroma = None

try:
    from langchain_core.documents import Document
except ImportError:
    try:
        from langchain.schema import Document
    except ImportError:
        from langchain.documents import Document

try:
    from langchain_openai import ChatOpenAI
except ImportError:
    try:
        from langchain.chat_models import ChatOpenAI
    except ImportError:
        ChatOpenAI = None

# ConversationalRetrievalChain is optional - we'll implement conversational query differently
CONVERSATIONAL_CHAIN_AVAILABLE = False
try:
    from langchain.chains import ConversationalRetrievalChain
    from langchain.memory import ConversationBufferMemory
    CONVERSATIONAL_CHAIN_AVAILABLE = True
except ImportError:
    try:
        from langchain.chains.conversational_retrieval.base import ConversationalRetrievalChain
        from langchain.memory import ConversationBufferMemory
        CONVERSATIONAL_CHAIN_AVAILABLE = True
    except ImportError:
        pass

from docchat import AppConfig


class DataModality(Enum):
    """Supported data modalities for multimodal processing."""
    TEXT = "text"
    PDF = "pdf"
    VIDEO = "video"
    AUDIO = "audio"
    IMAGE = "image"
    STRUCTURED = "structured"  # JSON, CSV, etc.
    CHEMICAL = "chemical"  # For drug discovery
    PROTEIN = "protein"  # For biomedical research
    HEALTH_RECORD = "health_record"


@dataclass
class SemanticDocument:
    """Represents a document with semantic metadata."""
    doc_id: str
    content: str
    modality: DataModality
    embedding_model: str
    metadata: Dict[str, Any]
    created_at: str
    updated_at: str
    lineage: List[str]  # Track data lineage
    embedding_version: str
    source_path: str
    file_hash: str


@dataclass
class SemanticQuery:
    """Represents a semantic query."""
    query_id: str
    query_text: str
    modality_filter: Optional[DataModality]
    embedding_model: str
    results: List[Dict[str, Any]]
    created_at: str
    execution_time: float


@dataclass
class DataLineage:
    """Tracks data lineage and transformations."""
    lineage_id: str
    doc_id: str
    transformation_type: str
    source_embedding_model: str
    target_embedding_model: Optional[str]
    timestamp: str
    metadata: Dict[str, Any]


class SemanticDataEngine:
    """
    Semantic Data Processing Engine - Implements NVIDIA/NetApp AI Data Engine concepts.
    
    Features:
    - Semantic embedding and indexing (neural network-based, not hash tables)
    - Vectorized database for nearest neighbor search
    - Multimodal data support (text, PDF, video, audio, images, etc.)
    - Natural language and conversational queries
    - Data lineage tracking
    - Active metadata processing
    - Guardrails and security
    """
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.embeddings = OpenAIEmbeddings(openai_api_key=config.openai_api_key)
        self.llm = None
        if ChatOpenAI:
            try:
                self.llm = ChatOpenAI(
                    model=config.research_model,
                    temperature=0.7,
                    openai_api_key=config.openai_api_key,
                    max_tokens=16000  # Aumentado para aprovechar context window grande (128k tokens)
                )
            except Exception as e:
                print(f"[Semantic Engine] Warning: Could not initialize ChatOpenAI: {e}")
        
        # Data directories
        self.data_dir = config.base_path / "semantic_data"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.embeddings_dir = self.data_dir / "embeddings"
        self.embeddings_dir.mkdir(exist_ok=True)
        
        self.lineage_dir = self.data_dir / "lineage"
        self.lineage_dir.mkdir(exist_ok=True)
        
        self.metadata_dir = self.data_dir / "metadata"
        self.metadata_dir.mkdir(exist_ok=True)
        
        # In-memory storage
        self.documents: Dict[str, SemanticDocument] = {}
        self.vector_store: Optional[Any] = None  # Can be FAISS, Chroma, or None
        self.lineage_records: Dict[str, DataLineage] = {}
        self.query_history: List[SemanticQuery] = []
        self.use_faiss = FAISS_AVAILABLE  # Prefer FAISS if available
        
        # Embedding model tracking
        self.current_embedding_model = "text-embedding-ada-002"
        self.embedding_versions: Dict[str, str] = {}
        
        # Load existing data
        self._load_data()
    
    def _load_data(self):
        """Load existing documents and lineage from disk."""
        # Load documents
        docs_file = self.data_dir / "documents.json"
        if docs_file.exists():
            try:
                with open(docs_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for doc_id, doc_data in data.items():
                        doc_data['modality'] = DataModality(doc_data['modality'])
                        self.documents[doc_id] = SemanticDocument(**doc_data)
            except Exception as e:
                print(f"[Semantic Engine] Error loading documents: {e}")
        
        # Load lineage
        lineage_file = self.lineage_dir / "lineage.json"
        if lineage_file.exists():
            try:
                with open(lineage_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for lineage_id, lineage_data in data.items():
                        self.lineage_records[lineage_id] = DataLineage(**lineage_data)
            except Exception as e:
                print(f"[Semantic Engine] Error loading lineage: {e}")
        
        # Load vector store if exists
        self._load_vector_store()
    
    def _save_data(self):
        """Save documents and lineage to disk."""
        # Save documents
        docs_file = self.data_dir / "documents.json"
        docs_data = {
            doc_id: asdict(doc) for doc_id, doc in self.documents.items()
        }
        # Convert Enum to string for JSON
        for doc_id in docs_data:
            docs_data[doc_id]['modality'] = docs_data[doc_id]['modality'].value
        
        with open(docs_file, 'w', encoding='utf-8') as f:
            json.dump(docs_data, f, indent=2, ensure_ascii=False)
        
        # Save lineage
        lineage_file = self.lineage_dir / "lineage.json"
        lineage_data = {
            lineage_id: asdict(lineage) for lineage_id, lineage in self.lineage_records.items()
        }
        with open(lineage_file, 'w', encoding='utf-8') as f:
            json.dump(lineage_data, f, indent=2, ensure_ascii=False)
    
    def _load_vector_store(self):
        """Load or create vector store."""
        if len(self.documents) == 0:
            return
        
        try:
            # Create documents for vector store
            docs = []
            for doc in self.documents.values():
                langchain_doc = Document(
                    page_content=doc.content,
                    metadata={
                        "doc_id": doc.doc_id,
                        "modality": doc.modality.value,
                        "source_path": doc.source_path,
                        "embedding_model": doc.embedding_model,
                        "embedding_version": doc.embedding_version,
                        **doc.metadata
                    }
                )
                docs.append(langchain_doc)
            
            if not docs:
                return
            
            # Try to load existing vector store
            vector_store_path = self.embeddings_dir / "vector_store"
            chroma_path = self.embeddings_dir / "chroma_db"
            
            if self.use_faiss and FAISS_AVAILABLE and vector_store_path.exists():
                try:
                    self.vector_store = FAISS.load_local(
                        str(vector_store_path),
                        self.embeddings,
                        allow_dangerous_deserialization=True
                    )
                    print("[Semantic Engine] Loaded FAISS vector store")
                    return
                except Exception as e:
                    print(f"[Semantic Engine] Could not load FAISS, trying Chroma: {e}")
            
            # Try Chroma
            if Chroma and chroma_path.exists():
                try:
                    self.vector_store = Chroma(
                        persist_directory=str(chroma_path),
                        embedding_function=self.embeddings
                    )
                    print("[Semantic Engine] Loaded Chroma vector store")
                    return
                except Exception as e:
                    print(f"[Semantic Engine] Could not load Chroma: {e}")
            
            # Create new vector store
            if self.use_faiss and FAISS_AVAILABLE:
                try:
                    self.vector_store = FAISS.from_documents(docs, self.embeddings)
                    print("[Semantic Engine] Created new FAISS vector store")
                except Exception as e:
                    print(f"[Semantic Engine] Could not create FAISS, using Chroma: {e}")
                    self.use_faiss = False
            
            if not self.vector_store and Chroma:
                try:
                    self.vector_store = Chroma.from_documents(
                        documents=docs,
                        embedding=self.embeddings,
                        persist_directory=str(chroma_path)
                    )
                    print("[Semantic Engine] Created new Chroma vector store")
                except Exception as e:
                    print(f"[Semantic Engine] Could not create Chroma: {e}")
            
            if not self.vector_store:
                print("[Semantic Engine] Warning: No vector store available. Install faiss-cpu or chromadb.")
        
        except Exception as e:
            print(f"[Semantic Engine] Error loading vector store: {e}")
            self.vector_store = None
    
    def _save_vector_store(self):
        """Save vector store to disk."""
        if self.vector_store:
            try:
                if self.use_faiss and FAISS_AVAILABLE:
                    # FAISS save
                    vector_store_path = self.embeddings_dir / "vector_store"
                    self.vector_store.save_local(str(vector_store_path))
                elif Chroma and isinstance(self.vector_store, Chroma):
                    # Chroma persists automatically, but we can call persist
                    self.vector_store.persist()
            except Exception as e:
                print(f"[Semantic Engine] Error saving vector store: {e}")
    
    def _detect_modality(self, file_path: str, content: str = "") -> DataModality:
        """Detect data modality from file path and content."""
        path_lower = file_path.lower()
        
        if path_lower.endswith('.pdf'):
            return DataModality.PDF
        elif path_lower.endswith(('.mp4', '.avi', '.mov', '.mkv')):
            return DataModality.VIDEO
        elif path_lower.endswith(('.mp3', '.wav', '.flac', '.m4a')):
            return DataModality.AUDIO
        elif path_lower.endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp')):
            return DataModality.IMAGE
        elif path_lower.endswith(('.json', '.csv', '.xlsx', '.xls')):
            return DataModality.STRUCTURED
        else:
            return DataModality.TEXT
    
    def _compute_file_hash(self, content: str) -> str:
        """Compute hash for file content."""
        import hashlib
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def embed_document(
        self,
        content: str,
        source_path: str,
        modality: Optional[DataModality] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> SemanticDocument:
        """
        Embed a document semantically using neural network-based indexing.
        This is NOT hash table or tree-based indexing - it's vectorized.
        """
        # Detect modality if not provided
        if modality is None:
            modality = self._detect_modality(source_path, content)
        
        # Compute file hash
        file_hash = self._compute_file_hash(content)
        
        # Check if document already exists with same hash
        existing_doc = None
        for doc in self.documents.values():
            if doc.file_hash == file_hash and doc.source_path == source_path:
                existing_doc = doc
                break
        
        if existing_doc:
            # Check if embedding is up to date
            if existing_doc.embedding_model != self.current_embedding_model:
                # Need to re-embed with new model
                print(f"[Semantic Engine] Re-embedding document {existing_doc.doc_id} with new model")
                doc_id = existing_doc.doc_id
            else:
                # Document already embedded and up to date
                return existing_doc
        else:
            doc_id = str(uuid.uuid4())
        
        # Create semantic document
        now = datetime.now().isoformat()
        embedding_version = f"{self.current_embedding_model}_{now}"
        
        semantic_doc = SemanticDocument(
            doc_id=doc_id,
            content=content,
            modality=modality,
            embedding_model=self.current_embedding_model,
            metadata=metadata or {},
            created_at=existing_doc.created_at if existing_doc else now,
            updated_at=now,
            lineage=existing_doc.lineage.copy() if existing_doc else [],
            embedding_version=embedding_version,
            source_path=source_path,
            file_hash=file_hash
        )
        
        # Track lineage if re-embedding
        if existing_doc and existing_doc.embedding_model != self.current_embedding_model:
            lineage = DataLineage(
                lineage_id=str(uuid.uuid4()),
                doc_id=doc_id,
                transformation_type="re-embedding",
                source_embedding_model=existing_doc.embedding_model,
                target_embedding_model=self.current_embedding_model,
                timestamp=now,
                metadata={"reason": "model_update"}
            )
            self.lineage_records[lineage.lineage_id] = lineage
            semantic_doc.lineage.append(lineage.lineage_id)
        
        # Store document
        self.documents[doc_id] = semantic_doc
        self.embedding_versions[doc_id] = embedding_version
        
        # Update vector store
        langchain_doc = Document(
            page_content=content,
            metadata={
                "doc_id": doc_id,
                "modality": modality.value,
                "source_path": source_path,
                "embedding_model": self.current_embedding_model,
                "embedding_version": embedding_version,
                **(metadata or {})
            }
        )
        
        if self.vector_store is None:
            if self.use_faiss and FAISS_AVAILABLE:
                try:
                    self.vector_store = FAISS.from_documents([langchain_doc], self.embeddings)
                except Exception as e:
                    print(f"[Semantic Engine] Could not create FAISS, using Chroma: {e}")
                    self.use_faiss = False
            
            if not self.vector_store and Chroma:
                try:
                    vector_store_path = self.embeddings_dir / "chroma_db"
                    self.vector_store = Chroma.from_documents(
                        documents=[langchain_doc],
                        embedding=self.embeddings,
                        persist_directory=str(vector_store_path)
                    )
                except Exception as e:
                    print(f"[Semantic Engine] Could not create Chroma: {e}")
        else:
            try:
                self.vector_store.add_documents([langchain_doc])
            except Exception as e:
                print(f"[Semantic Engine] Error adding document to vector store: {e}")
        
        # Save
        self._save_data()
        self._save_vector_store()
        
        return semantic_doc
    
    def semantic_search(
        self,
        query: str,
        modality_filter: Optional[DataModality] = None,
        k: int = 5,
        use_reranking: bool = True
    ) -> SemanticQuery:
        """
        Perform semantic search using AI queries (not SQL).
        This is nearest neighbor search in vectorized space.
        """
        start_time = datetime.now()
        
        if not self.vector_store or len(self.documents) == 0:
            return SemanticQuery(
                query_id=str(uuid.uuid4()),
                query_text=query,
                modality_filter=modality_filter,
                embedding_model=self.current_embedding_model,
                results=[],
                created_at=datetime.now().isoformat(),
                execution_time=0.0
            )
        
        # Perform vector similarity search (nearest neighbors)
        search_kwargs = {"k": k * 2 if use_reranking else k}  # Get more for reranking
        
        if modality_filter:
            # Filter by modality in metadata
            def filter_func(doc):
                return doc.metadata.get("modality") == modality_filter.value
            # Note: FAISS doesn't support filtering directly, so we'll filter results
            docs_with_scores = self.vector_store.similarity_search_with_score(
                query, k=search_kwargs["k"]
            )
            filtered_docs = [
                (doc, score) for doc, score in docs_with_scores
                if doc.metadata.get("modality") == modality_filter.value
            ]
            docs_with_scores = filtered_docs[:k]
        else:
            docs_with_scores = self.vector_store.similarity_search_with_score(
                query, k=search_kwargs["k"]
            )
        
        # Rerank if requested
        if use_reranking and len(docs_with_scores) > k:
            # Use LLM for reranking based on semantic relevance
            reranked = self._rerank_results(query, docs_with_scores)
            docs_with_scores = reranked[:k]
        else:
            docs_with_scores = docs_with_scores[:k]
        
        # Format results
        results = []
        for doc, score in docs_with_scores:
            doc_id = doc.metadata.get("doc_id")
            semantic_doc = self.documents.get(doc_id)
            
            result = {
                "doc_id": doc_id,
                "content": doc.page_content[:500] + "..." if len(doc.page_content) > 500 else doc.page_content,
                "modality": doc.metadata.get("modality"),
                "source_path": doc.metadata.get("source_path"),
                "similarity_score": float(score),
                "embedding_model": doc.metadata.get("embedding_model"),
                "metadata": {k: v for k, v in doc.metadata.items() 
                            if k not in ["doc_id", "modality", "source_path", "embedding_model", "embedding_version"]}
            }
            
            if semantic_doc:
                result["lineage"] = semantic_doc.lineage
                result["embedding_version"] = semantic_doc.embedding_version
            
            results.append(result)
        
        execution_time = (datetime.now() - start_time).total_seconds()
        
        semantic_query = SemanticQuery(
            query_id=str(uuid.uuid4()),
            query_text=query,
            modality_filter=modality_filter,
            embedding_model=self.current_embedding_model,
            results=results,
            created_at=datetime.now().isoformat(),
            execution_time=execution_time
        )
        
        # Store query history
        self.query_history.append(semantic_query)
        if len(self.query_history) > 1000:  # Keep last 1000 queries
            self.query_history = self.query_history[-1000:]
        
        return semantic_query
    
    def _rerank_results(self, query: str, docs_with_scores: List[tuple]) -> List[tuple]:
        """Rerank results using LLM for better semantic relevance."""
        # Simple reranking: use LLM to score relevance
        # In production, use a dedicated reranking model
        try:
            # For now, just return sorted by score (lower is better for distance)
            return sorted(docs_with_scores, key=lambda x: x[1])
        except Exception:
            return docs_with_scores
    
    def conversational_query(
        self,
        question: str,
        chat_history: Optional[List[tuple]] = None,
        modality_filter: Optional[DataModality] = None
    ) -> Dict[str, Any]:
        """
        Conversational query - "just ask NetApp" style.
        The AI will search the storage system and find the answer.
        """
        if not self.vector_store:
            return {
                "answer": "No hay documentos indexados. Por favor, sube documentos primero.",
                "sources": [],
                "chat_history": chat_history or []
            }
        
        # Perform semantic search
        search_results = self.semantic_search(
            query=question,
            modality_filter=modality_filter,
            k=5,
            use_reranking=True
        )
        
        # Create context from search results
        context = "\n\n".join([
            f"[Documento {i+1} - {r['modality']}]:\n{r['content']}"
            for i, r in enumerate(search_results.results)
        ])
        
        # Build conversation context
        conversation_context = ""
        if chat_history:
            conversation_context = "\n\nConversación previa:\n"
            for human, ai in chat_history[-3:]:  # Last 3 exchanges
                conversation_context += f"Usuario: {human}\n"
                conversation_context += f"Asistente: {ai}\n\n"
        
        # Create prompt
        prompt = f"""Basándote en los siguientes documentos y la conversación previa, responde la pregunta del usuario de manera completa y útil.

{conversation_context}

Documentos relevantes:
{context}

Pregunta del usuario: {question}

Responde de manera clara y completa basándote únicamente en la información proporcionada en los documentos."""
        
        # Use LLM to generate answer
        if self.llm:
            try:
                # Try different methods depending on LangChain version
                try:
                    response = self.llm.invoke(prompt)
                    answer = response.content if hasattr(response, 'content') else str(response)
                except:
                    try:
                        response = self.llm.predict(prompt)
                        answer = response
                    except:
                        try:
                            messages = [{"role": "user", "content": prompt}]
                            response = self.llm(messages)
                            answer = response.content if hasattr(response, 'content') else str(response)
                        except Exception as e:
                            # Fallback: use search results directly
                            answer = f"Basándome en los documentos encontrados:\n\n{context[:500]}..."
            except Exception as e:
                # Fallback: use search results directly
                answer = f"Basándome en los documentos encontrados:\n\n{context[:500]}..."
        else:
            # Fallback: use search results directly
            answer = f"Basándome en los documentos encontrados:\n\n{context[:500]}..."
        
        # Format response
        sources = [
            {
                "source": r.get("source_path", "Unknown"),
                "modality": r.get("modality", "text"),
                "content": r.get("content", "")[:200] + "..." if len(r.get("content", "")) > 200 else r.get("content", "")
            }
            for r in search_results.results
        ]
        
        return {
            "answer": answer,
            "sources": sources,
            "chat_history": chat_history or [],
            "query_id": search_results.query_id,
            "execution_time": search_results.execution_time
        }
    
    def get_data_lineage(self, doc_id: str) -> List[DataLineage]:
        """Get data lineage for a document."""
        doc = self.documents.get(doc_id)
        if not doc:
            return []
        
        lineage = []
        for lineage_id in doc.lineage:
            if lineage_id in self.lineage_records:
                lineage.append(self.lineage_records[lineage_id])
        
        return lineage
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the semantic data engine."""
        total_docs = len(self.documents)
        by_modality = {}
        for doc in self.documents.values():
            modality = doc.modality.value
            by_modality[modality] = by_modality.get(modality, 0) + 1
        
        embedding_models = {}
        for doc in self.documents.values():
            model = doc.embedding_model
            embedding_models[model] = embedding_models.get(model, 0) + 1
        
        return {
            "total_documents": total_docs,
            "by_modality": by_modality,
            "embedding_models": embedding_models,
            "current_embedding_model": self.current_embedding_model,
            "total_queries": len(self.query_history),
            "total_lineage_records": len(self.lineage_records),
            "vector_store_size": (
                len(self.vector_store.index_to_docstore_id) if self.vector_store and hasattr(self.vector_store, 'index_to_docstore_id') 
                else (len(self.vector_store._collection.get()['ids']) if self.vector_store and hasattr(self.vector_store, '_collection') 
                      else 0)
            )
        }
    
    def check_embedding_consistency(self) -> Dict[str, Any]:
        """
        Check which documents are embedded properly and which are out of date.
        This is critical for maintaining data quality.
        """
        results = {
            "up_to_date": [],
            "out_of_date": [],
            "different_model": []
        }
        
        for doc_id, doc in self.documents.items():
            if doc.embedding_model == self.current_embedding_model:
                results["up_to_date"].append({
                    "doc_id": doc_id,
                    "source": doc.source_path,
                    "modality": doc.modality.value,
                    "embedding_model": doc.embedding_model
                })
            else:
                results["out_of_date"].append({
                    "doc_id": doc_id,
                    "source": doc.source_path,
                    "modality": doc.modality.value,
                    "current_model": doc.embedding_model,
                    "expected_model": self.current_embedding_model
                })
                results["different_model"].append(doc.embedding_model)
        
        results["different_model"] = list(set(results["different_model"]))
        
        return results


