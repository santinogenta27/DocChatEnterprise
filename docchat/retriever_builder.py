from __future__ import annotations

import os
import uuid
from collections import defaultdict
from pathlib import Path
from typing import Iterable, List, Sequence

from langchain_community.retrievers import BM25Retriever
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_openai import OpenAIEmbeddings
from pydantic import ConfigDict

from .config import AppConfig


class HybridRetriever(BaseRetriever):
    """Combines BM25 and vector search with weighted scoring."""

    # Pydantic v2 configuration
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    def __init__(
        self,
        bm25_retriever: BM25Retriever,
        vector_retriever: BaseRetriever,
        weights: Sequence[float] = (0.45, 0.55),
        **kwargs,
    ):
        # Call super first to initialize BaseRetriever
        super().__init__(**kwargs)
        # Store retrievers in __dict__ directly to bypass Pydantic
        self.__dict__["bm25_retriever"] = bm25_retriever
        self.__dict__["vector_retriever"] = vector_retriever
        self.__dict__["weights"] = weights

    def __getattr__(self, name: str):
        """Access stored attributes from __dict__."""
        if name in self.__dict__:
            return self.__dict__[name]
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    def _get_relevant_documents(self, query: str) -> List[Document]:
        """Retrieve and combine documents from both retrievers."""
        # Get results from both retrievers (compatible with LangChain 1.0+)
        try:
            bm25_docs = self.bm25_retriever.invoke(query)
            vector_docs = self.vector_retriever.invoke(query)
        except AttributeError:
            # Fallback for older versions
            bm25_docs = self.bm25_retriever.get_relevant_documents(query)
            vector_docs = self.vector_retriever.get_relevant_documents(query)

        # Score documents by position and retriever
        doc_scores: dict[str, float] = defaultdict(float)
        doc_map: dict[str, Document] = {}

        # Score BM25 results (higher score for earlier positions)
        bm25_weight = self.weights[0]
        for idx, doc in enumerate(bm25_docs):
            doc_id = id(doc)  # Use object id as unique identifier
            doc_map[doc_id] = doc
            # Inverse rank scoring: first doc gets highest score
            score = bm25_weight * (1.0 / (idx + 1))
            doc_scores[doc_id] += score

        # Score vector results
        vector_weight = self.weights[1]
        for idx, doc in enumerate(vector_docs):
            doc_id = id(doc)
            doc_map[doc_id] = doc
            score = vector_weight * (1.0 / (idx + 1))
            doc_scores[doc_id] += score

        # Sort by combined score and return unique documents
        sorted_docs = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)
        result = []
        seen_content = set()

        for doc_id, _score in sorted_docs:
            doc = doc_map[doc_id]
            # Deduplicate by content
            content_hash = hash(doc.page_content)
            if content_hash not in seen_content:
                seen_content.add(content_hash)
                result.append(doc)

        return result


class RetrieverBuilder:
    """Creates hybrid retrievers (BM25 + vector search)."""

    def __init__(self, config: AppConfig):
        self.config = config
        # Pass API key explicitly to avoid issues
        api_key = config.openai_api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY must be set in config or environment")
        # Optimizar embeddings para evitar rate limits
        self.embeddings = OpenAIEmbeddings(
            model=config.embedding_model, 
            api_key=api_key,
            chunk_size=100,  # Procesar en lotes más pequeños
            max_retries=5,  # Más reintentos
            request_timeout=120  # Timeout más largo
        )

    def build_hybrid_retriever(self, docs: Iterable[Document]) -> HybridRetriever:
        docs = list(docs)
        if not docs:
            raise ValueError("No hay documentos procesados para indexar.")

        # Para grandes volúmenes, mostrar progreso
        total_docs = len(docs)
        if total_docs > 1000:
            print(f"Generando embeddings para {total_docs} chunks... Esto puede tardar varios minutos.")
            print("El sistema maneja rate limits automáticamente, por favor espera...")

        namespace = uuid.uuid4().hex
        persist_dir = Path(self.config.persist_dir) / namespace
        
        # Chroma.from_documents genera embeddings automáticamente
        # Con muchos documentos, esto puede tardar pero funciona correctamente
        vector_store = Chroma.from_documents(
            documents=docs,
            embedding=self.embeddings,
            persist_directory=str(persist_dir),
        )
        # Chroma 0.4.x+ persists automatically, no need to call persist()

        vector_retriever = vector_store.as_retriever(search_kwargs={"k": self.config.vector_k})
        bm25 = BM25Retriever.from_documents(docs)
        bm25.k = self.config.bm25_k

        hybrid = HybridRetriever(
            bm25_retriever=bm25,
            vector_retriever=vector_retriever,
            weights=self.config.hybrid_weights,
        )
        return hybrid

