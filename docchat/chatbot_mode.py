"""
Modo Chatbot: Permite a empresas conectar sus chatbots existentes por API
y usar RAG con su data privada para responder consultas de usuarios.
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from langchain_core.documents import Document
from langchain_openai import ChatOpenAI
from langchain_core.retrievers import BaseRetriever
from langchain_community.vectorstores import Chroma

from .config import AppConfig
from .document_processor import DocumentProcessor
from .retriever_builder import RetrieverBuilder
from .cache.embedding_cache import CachedOpenAIEmbeddings


@dataclass
class ChatbotConnection:
    """Conexión de un chatbot externo."""
    chatbot_id: str
    chatbot_name: str
    company_name: str
    api_key: str
    webhook_url: Optional[str] = None
    created_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%d %H:%M:%S"))
    status: str = "active"
    documents_count: int = 0
    chunks_count: int = 0


@dataclass
class RAGResponse:
    """Respuesta del RAG optimizado."""
    answer: str
    sources: List[str]
    confidence: float
    chunks_used: int
    reranked: bool
    metadata: Dict[str, Any] = field(default_factory=dict)


class ChatbotMode:
    """
    Modo Chatbot: Permite a empresas conectar chatbots externos
    y usar RAG con su data privada.
    
    Características:
    - Chunking inteligente (300-500 tokens con overlap)
    - Reranking avanzado para mejor precisión
    - Prompt interno para evitar alucinaciones
    - Base vectorizada por chatbot
    - API para consultas desde chatbots externos
    """
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.document_processor = DocumentProcessor(config)
        self.retriever_builder = RetrieverBuilder(config)
        
        # Directorio para datos de chatbots
        self.data_dir = Path(config.memory_dir) / "chatbot_data"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Archivos de datos
        self.connections_file = self.data_dir / "chatbot_connections.json"
        self.vector_stores: Dict[str, Any] = {}  # Vector stores por chatbot_id
        self.retrievers: Dict[str, BaseRetriever] = {}  # Retrievers por chatbot_id
        
        # LLM para generación de respuestas
        if not config.openai_api_key:
            raise ValueError("OPENAI_API_KEY requerida para Chatbot Mode")
        
        self.llm = ChatOpenAI(
            model=config.research_model or "gpt-4o",
            temperature=0.2,  # Baja temperatura para respuestas más precisas
            api_key=config.openai_api_key,
            max_tokens=2000
        )
        
        # Cargar conexiones existentes
        self.connections: Dict[str, ChatbotConnection] = self._load_connections()
    
    def _load_connections(self) -> Dict[str, ChatbotConnection]:
        """Carga conexiones de chatbots desde archivo."""
        try:
            if self.connections_file.exists():
                with open(self.connections_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return {
                        chatbot_id: ChatbotConnection(**conn_data)
                        for chatbot_id, conn_data in data.items()
                    }
            return {}
        except Exception as e:
            print(f"Error cargando conexiones: {e}")
            return {}
    
    def _save_connections(self):
        """Guarda conexiones de chatbots."""
        try:
            data = {
                chatbot_id: {
                    "chatbot_id": conn.chatbot_id,
                    "chatbot_name": conn.chatbot_name,
                    "company_name": conn.company_name,
                    "api_key": conn.api_key,
                    "webhook_url": conn.webhook_url,
                    "created_at": conn.created_at,
                    "status": conn.status,
                    "documents_count": conn.documents_count,
                    "chunks_count": conn.chunks_count
                }
                for chatbot_id, conn in self.connections.items()
            }
            with open(self.connections_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error guardando conexiones: {e}")
    
    def register_chatbot(
        self,
        chatbot_name: str,
        company_name: str,
        api_key: Optional[str] = None
    ) -> ChatbotConnection:
        """
        Registra un nuevo chatbot.
        
        Returns:
            ChatbotConnection con chatbot_id y api_key generados
        """
        chatbot_id = str(uuid.uuid4())
        
        if not api_key:
            api_key = str(uuid.uuid4()).replace("-", "")[:32]
        
        connection = ChatbotConnection(
            chatbot_id=chatbot_id,
            chatbot_name=chatbot_name,
            company_name=company_name,
            api_key=api_key
        )
        
        self.connections[chatbot_id] = connection
        self._save_connections()
        
        print(f"✅ Chatbot '{chatbot_name}' registrado con ID: {chatbot_id}")
        return connection
    
    def upload_chatbot_data(
        self,
        chatbot_id: str,
        files: List[Any]
    ) -> Dict[str, Any]:
        """
        Sube y procesa data para un chatbot específico.
        Crea base vectorizada optimizada para RAG.
        """
        if chatbot_id not in self.connections:
            raise ValueError(f"Chatbot ID '{chatbot_id}' no encontrado")
        
        connection = self.connections[chatbot_id]
        
        print(f"\n{'='*60}")
        print(f"📄 PROCESANDO DATA PARA CHATBOT: {connection.chatbot_name}")
        print(f"{'='*60}\n")
        
        # Procesar documentos con chunking optimizado
        documents = self.document_processor.process(files)
        
        if not documents:
            raise ValueError("No se pudieron procesar los documentos")
        
        # Crear base vectorizada específica para este chatbot
        vector_store_dir = self.data_dir / chatbot_id / "vectorstore"
        vector_store_dir.mkdir(parents=True, exist_ok=True)
        
        # Construir embeddings con caché
        embeddings = CachedOpenAIEmbeddings(
            config=self.config,
            model=self.config.embedding_model,
            api_key=self.config.openai_api_key
        )
        
        # Crear vector store
        vector_store = Chroma.from_documents(
            documents=documents,
            embedding=embeddings,
            persist_directory=str(vector_store_dir)
        )
        
        # Crear retriever híbrido usando RetrieverBuilder
        # Esto crea un HybridRetriever optimizado (BM25 + Vector Search)
        hybrid_retriever = self.retriever_builder.build_hybrid_retriever(documents)
        
        # Guardar vector store y retriever
        self.vector_stores[chatbot_id] = vector_store
        self.retrievers[chatbot_id] = hybrid_retriever
        
        # Actualizar conexión
        connection.documents_count = len(files)
        connection.chunks_count = len(documents)
        self._save_connections()
        
        print(f"✅ Base vectorizada creada: {len(documents)} chunks")
        print(f"✅ Chatbot '{connection.chatbot_name}' listo para consultas\n")
        
        return {
            "chatbot_id": chatbot_id,
            "documents_processed": len(files),
            "chunks_created": len(documents),
            "vector_store_path": str(vector_store_dir)
        }
    
    def query_chatbot(
        self,
        chatbot_id: str,
        user_question: str,
        use_reranking: bool = True,
        max_chunks: int = 5
    ) -> RAGResponse:
        """
        Consulta el RAG del chatbot con optimizaciones avanzadas.
        
        Características:
        - Retrieval híbrido (BM25 + Vector)
        - Reranking para mejor precisión
        - Prompt interno para evitar alucinaciones
        - Respuesta basada solo en documentos
        """
        if chatbot_id not in self.connections:
            raise ValueError(f"Chatbot ID '{chatbot_id}' no encontrado")
        
        if chatbot_id not in self.retrievers:
            raise ValueError(f"Chatbot '{chatbot_id}' no tiene data procesada")
        
        connection = self.connections[chatbot_id]
        retriever = self.retrievers[chatbot_id]
        
        print(f"🔍 Consultando chatbot '{connection.chatbot_name}'...")
        print(f"   Pregunta: {user_question[:100]}...")
        
        # 1. Retrieval: Obtener chunks relevantes
        retrieved_docs = retriever.invoke(user_question)
        
        if not retrieved_docs:
            return RAGResponse(
                answer="No encontré información relevante en la base de conocimiento para responder tu pregunta.",
                sources=[],
                confidence=0.0,
                chunks_used=0,
                reranked=False,
                metadata={"error": "No documents retrieved"}
            )
        
        # 2. Reranking (opcional pero recomendado)
        if use_reranking and len(retrieved_docs) > max_chunks:
            retrieved_docs = self._rerank_documents(user_question, retrieved_docs, top_k=max_chunks)
        
        # 3. Construir contexto con chunks relevantes
        context_chunks = retrieved_docs[:max_chunks]
        context = self._build_context(context_chunks)
        
        # 4. Generar respuesta con prompt interno optimizado
        answer = self._generate_answer_with_internal_prompt(
            user_question=user_question,
            context=context,
            company_name=connection.company_name
        )
        
        # 5. Extraer fuentes
        sources = list(set([
            doc.metadata.get("source", "Unknown")
            for doc in context_chunks
        ]))
        
        # 6. Calcular confianza (basado en similitud y número de chunks)
        confidence = min(1.0, len(context_chunks) / max_chunks)
        
        print(f"✅ Respuesta generada usando {len(context_chunks)} chunks\n")
        
        return RAGResponse(
            answer=answer,
            sources=sources,
            confidence=confidence,
            chunks_used=len(context_chunks),
            reranked=use_reranking,
            metadata={
                "chatbot_name": connection.chatbot_name,
                "company_name": connection.company_name
            }
        )
    
    def _rerank_documents(
        self,
        question: str,
        documents: List[Document],
        top_k: int = 5
    ) -> List[Document]:
        """
        Reranking avanzado usando LLM para mejorar precisión.
        Evalúa relevancia semántica de cada chunk.
        """
        if len(documents) <= top_k:
            return documents
        
        print(f"   🔄 Reranking {len(documents)} documentos...")
        
        # Usar LLM para evaluar relevancia
        scored_docs = []
        
        for doc in documents:
            relevance_prompt = f"""Evalúa la relevancia de este documento para responder la pregunta.
            
Pregunta: {question}

Documento:
{doc.page_content[:500]}

Responde SOLO con un número del 0 al 10, donde:
- 10 = Muy relevante, responde directamente la pregunta
- 5 = Parcialmente relevante
- 0 = No relevante

Número:"""
            
            try:
                response = self.llm.invoke(relevance_prompt).content.strip()
                # Extraer número
                import re
                score_match = re.search(r'\d+', response)
                score = float(score_match.group(0)) if score_match else 5.0
                scored_docs.append((score, doc))
            except Exception:
                scored_docs.append((5.0, doc))  # Score por defecto
        
        # Ordenar por score y retornar top_k
        scored_docs.sort(key=lambda x: x[0], reverse=True)
        return [doc for _, doc in scored_docs[:top_k]]
    
    def _build_context(self, documents: List[Document]) -> str:
        """Construye contexto a partir de documentos."""
        context_parts = []
        
        for idx, doc in enumerate(documents, 1):
            source = doc.metadata.get("source", "Documento")
            content = doc.page_content[:800]  # Limitar tamaño por chunk
            context_parts.append(f"[Documento {idx} - {Path(source).name}]\n{content}")
        
        return "\n\n---\n\n".join(context_parts)
    
    def _generate_answer_with_internal_prompt(
        self,
        user_question: str,
        context: str,
        company_name: str
    ) -> str:
        """
        Genera respuesta usando prompt interno optimizado.
        Este prompt fuerza al LLM a usar solo la información de los documentos
        y evitar alucinaciones.
        """
        internal_prompt = f"""Eres un asistente de {company_name}. Tu tarea es responder preguntas de usuarios usando ÚNICAMENTE la información proporcionada en los documentos de la empresa.

INSTRUCCIONES CRÍTICAS:
1. Usa SOLO la información de los documentos proporcionados para responder
2. NO inventes información que no esté en los documentos
3. Si la información no está en los documentos, di claramente: "No tengo información sobre esto en la base de conocimiento de {company_name}"
4. Sé preciso y específico
5. Cita las fuentes cuando sea relevante
6. Si la pregunta es ambigua, pide clarificación

DOCUMENTOS DE LA EMPRESA:
{context}

PREGUNTA DEL USUARIO:
{user_question}

RESPUESTA (usa solo información de los documentos):"""
        
        try:
            response = self.llm.invoke(internal_prompt).content.strip()
            
            # Verificar que la respuesta no sea genérica o vacía
            if not response or len(response) < 20:
                return "No pude generar una respuesta adecuada con la información disponible."
            
            return response
        
        except Exception as e:
            print(f"Error generando respuesta: {e}")
            return f"Error al generar respuesta: {str(e)}"
    
    def get_chatbot_info(self, chatbot_id: str) -> Dict[str, Any]:
        """Obtiene información de un chatbot."""
        if chatbot_id not in self.connections:
            raise ValueError(f"Chatbot ID '{chatbot_id}' no encontrado")
        
        connection = self.connections[chatbot_id]
        return {
            "chatbot_id": connection.chatbot_id,
            "chatbot_name": connection.chatbot_name,
            "company_name": connection.company_name,
            "status": connection.status,
            "documents_count": connection.documents_count,
            "chunks_count": connection.chunks_count,
            "created_at": connection.created_at,
            "api_key": connection.api_key  # Para uso interno
        }
    
    def list_chatbots(self) -> List[Dict[str, Any]]:
        """Lista todos los chatbots registrados."""
        return [
            {
                "chatbot_id": conn.chatbot_id,
                "chatbot_name": conn.chatbot_name,
                "company_name": conn.company_name,
                "status": conn.status,
                "documents_count": conn.documents_count,
                "chunks_count": conn.chunks_count
            }
            for conn in self.connections.values()
        ]

