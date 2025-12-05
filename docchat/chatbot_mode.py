"""
Modo Chatbot: Permite a empresas conectar sus chatbots existentes por API
y usar RAG con su data privada para responder consultas de usuarios.
"""

from __future__ import annotations

import json
import time
import uuid
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from functools import lru_cache

from langchain_core.documents import Document
from langchain_openai import ChatOpenAI
from langchain_core.retrievers import BaseRetriever
from langchain_community.vectorstores import Chroma

from .config import AppConfig
from .document_processor import DocumentProcessor
from .retriever_builder import RetrieverBuilder
from .cache.embedding_cache import CachedOpenAIEmbeddings
from .pdf_converter import convert_to_pdf, TEXT_EXTENSIONS
from .chatbot_advanced_rag import (
    AdvancedRAGPipeline,
    AdvancedRAGConfig,
    HybridRetriever
)


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
    
    def __init__(self, config: AppConfig, use_advanced_rag: bool = True):
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
        self.hybrid_retrievers: Dict[str, HybridRetriever] = {}  # Advanced hybrid retrievers
        self.processed_documents: Dict[str, List[Document]] = {}  # Documentos procesados por chatbot_id (para L4 RAG)
        
        # Advanced RAG Pipeline
        self.use_advanced_rag = use_advanced_rag
        if use_advanced_rag:
            rag_config = AdvancedRAGConfig(
                chunk_size=700,  # Optimizado según paper
                chunk_overlap=200,
                dense_weight=0.6,
                sparse_weight=0.4,
                use_cross_encoder=True,
                use_ner_enrichment=True,
                use_query_expansion=True,
                use_query_rewriting=True
            )
            self.advanced_rag = AdvancedRAGPipeline(config, rag_config)
            print("✅ Advanced RAG Pipeline habilitado (Hybrid Retrieval + Cross-Encoder Reranking + NER)")
        else:
            self.advanced_rag = None
        
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
        
        # Caché de respuestas (simple en memoria, puede mejorarse con Redis)
        self.response_cache: Dict[str, Tuple[RAGResponse, float]] = {}
        self.cache_ttl = 3600  # 1 hora
        
        # LLM para relevancia previa (decidir si necesita RAG)
        self.relevance_llm = ChatOpenAI(
            model="gpt-4o-mini",  # Modelo más barato para relevancia
            temperature=0.0,
            api_key=config.openai_api_key,
            max_tokens=50
        )
    
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
        
        # Si es posible, convertir formatos de texto / multiformato a PDF intermedio
        processed_files: List[Any] = []
        tmp_dirs: List[Path] = []
        for f in files:
            try:
                # f puede ser ruta (str) o file-like con atributo name
                path = Path(f) if isinstance(f, (str, Path)) else Path(getattr(f, "name", ""))
                ext = path.suffix.lower()
                if ext in TEXT_EXTENSIONS:
                    tmp_dir = Path(self.data_dir) / f"_tmp_pdf_{chatbot_id}"
                    if tmp_dir not in tmp_dirs:
                        tmp_dir.mkdir(parents=True, exist_ok=True)
                        tmp_dirs.append(tmp_dir)
                    pdf_path = tmp_dir / (path.stem + ".pdf")
                    convert_to_pdf(path, pdf_path)
                    processed_files.append(str(pdf_path))
                else:
                    processed_files.append(f)
            except Exception:
                # Si algo falla, usar el archivo original
                processed_files.append(f)

        # Procesar documentos (PDFs + originales)
        raw_documents = self.document_processor.process(processed_files)
        
        if not raw_documents:
            raise ValueError("No se pudieron procesar los documentos")
        
        # Usar Advanced RAG Pipeline si está habilitado
        if self.use_advanced_rag and self.advanced_rag:
            print("🔄 Procesando con Advanced RAG Pipeline...")
            # Procesar con chunking semántico y enriquecimiento NER
            documents = self.advanced_rag.process_documents(raw_documents)
            print(f"✅ Chunking semántico completado: {len(documents)} chunks (700 tokens con overlap)")
        else:
            # Fallback a procesamiento estándar
            documents = raw_documents
            try:
                from .metadata_enricher import MetadataEnricher
                enricher = MetadataEnricher(use_llm=False)
                documents = enricher.enrich_documents_batch(documents, use_advanced=False)
                print(f"✅ Metadatos enriquecidos: keywords, entidades, frases representativas")
            except Exception as e:
                print(f"⚠️ Enriquecimiento de metadatos no disponible: {e}")
        
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
        
        # Crear retriever (Advanced o estándar)
        if self.use_advanced_rag and self.advanced_rag:
            # Advanced Hybrid Retriever con pesos optimizados
            hybrid_retriever = self.advanced_rag.create_hybrid_retriever(
                documents=documents,
                embeddings=embeddings,
                vector_store_path=str(vector_store_dir)
            )
            self.hybrid_retrievers[chatbot_id] = hybrid_retriever
            print("✅ Advanced Hybrid Retriever creado (Dense 0.6 + BM25 0.4)")
        else:
            # Retriever estándar
            hybrid_retriever = self.retriever_builder.build_hybrid_retriever(documents)
            self.retrievers[chatbot_id] = hybrid_retriever
        
        # Guardar vector store
        self.vector_stores[chatbot_id] = vector_store
        
        # Guardar documentos procesados (necesario para L4 RAG)
        self.processed_documents[chatbot_id] = documents
        
        # L4 RAG: Construir índices de Mixture of Spaces si está habilitado
        if self.use_advanced_rag and self.advanced_rag and \
           self.advanced_rag.rag_config.use_mixture_of_spaces and \
           self.advanced_rag.mixture_of_spaces:
            try:
                print("🔨 Construyendo índices de Mixture of Spaces (L4 RAG)...")
                self.advanced_rag.mixture_of_spaces.build_indexes(documents)
                print("✅ Mixture of Spaces construido (Semantic + Structural + Metadata)")
            except Exception as e:
                print(f"⚠️ Error construyendo Mixture of Spaces: {e}")
        
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
    
    def needs_rag(self, chatbot_id: str, user_question: str) -> bool:
        """
        Determina si la pregunta necesita consultar documentos privados.
        
        Preguntas que NO necesitan RAG:
        - Saludos (hola, buenos días)
        - Preguntas generales (qué hora es, cómo estás)
        - Preguntas fuera de contexto de la empresa
        
        Preguntas que SÍ necesitan RAG:
        - Sobre políticas, términos, productos de la empresa
        - Información específica de la empresa
        - Consultas técnicas relacionadas con la empresa
        """
        if chatbot_id not in self.connections:
            return True  # Por defecto, usar RAG si hay error
        
        connection = self.connections[chatbot_id]
        
        # Preguntas simples que no necesitan RAG
        simple_questions = [
            "hola", "buenos días", "buenas tardes", "buenas noches",
            "gracias", "de nada", "adiós", "hasta luego",
            "qué hora es", "cómo estás", "qué tal"
        ]
        
        question_lower = user_question.lower().strip()
        
        # Si es pregunta simple, no necesita RAG
        if any(simple in question_lower for simple in simple_questions):
            return False
        
        # Usar LLM para determinar relevancia
        try:
            prompt = f"""Evalúa si esta pregunta necesita consultar documentos privados de {connection.company_name}.

Pregunta: {user_question}

Responde SOLO con "SÍ" o "NO":
- "SÍ" si la pregunta es sobre información específica de {connection.company_name} (políticas, productos, términos, procedimientos, etc.)
- "NO" si es un saludo, pregunta general, o no relacionada con {connection.company_name}

Respuesta:"""
            
            response = self.relevance_llm.invoke(prompt).content.strip().upper()
            return "SÍ" in response or "SI" in response
        except Exception:
            return True  # Por defecto, usar RAG si hay error
    
    def _get_cache_key(self, chatbot_id: str, question: str) -> str:
        """Genera clave de caché para una pregunta."""
        key_string = f"{chatbot_id}:{question.lower().strip()}"
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _get_cached_response(self, cache_key: str) -> Optional[RAGResponse]:
        """Obtiene respuesta del caché si existe y no expiró."""
        if cache_key in self.response_cache:
            response, timestamp = self.response_cache[cache_key]
            if time.time() - timestamp < self.cache_ttl:
                return response
            else:
                del self.response_cache[cache_key]
        return None
    
    def _cache_response(self, cache_key: str, response: RAGResponse):
        """Guarda respuesta en caché."""
        self.response_cache[cache_key] = (response, time.time())
        # Limpiar caché viejo (mantener solo últimos 1000)
        if len(self.response_cache) > 1000:
            oldest_key = min(self.response_cache.keys(), key=lambda k: self.response_cache[k][1])
            del self.response_cache[oldest_key]
    
    def query_chatbot(
        self,
        chatbot_id: str,
        user_question: str,
        use_reranking: bool = True,
        max_chunks: int = 5,
        use_cache: bool = True
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
        
        # Verificar caché primero
        if use_cache:
            cache_key = self._get_cache_key(chatbot_id, user_question)
            cached_response = self._get_cached_response(cache_key)
            if cached_response:
                print(f"✅ Respuesta desde caché para '{connection.chatbot_name}'")
                return cached_response
        
        print(f"🔍 Consultando chatbot '{connection.chatbot_name}'...")
        print(f"   Pregunta: {user_question[:100]}...")
        
        # 1. Retrieval: Obtener chunks relevantes (Advanced o estándar)
        if self.use_advanced_rag and chatbot_id in self.hybrid_retrievers:
            # Advanced RAG con L4: Mixture of Spaces + Adaptive Chain of Actions
            documents_for_l4 = self.processed_documents.get(chatbot_id, [])
            retrieved_docs = self.advanced_rag.retrieve(
                retriever=self.hybrid_retrievers[chatbot_id],
                query=user_question,
                use_reformulation=True,
                documents=documents_for_l4 if documents_for_l4 else None
            )
            used_reranking = True
            # Detectar si se usó L4 RAG
            if self.advanced_rag.adaptive_chain and documents_for_l4:
                print(f"   ✅ L4 RAG: Mixture of Spaces + Adaptive Chain of Actions")
            else:
                print(f"   ✅ Advanced RAG: Query reformulation + Hybrid Retrieval + Cross-Encoder Reranking")
        else:
            # Retrieval estándar
            retrieved_docs = retriever.invoke(user_question)
            used_reranking = False
            
            # Reranking manual si está habilitado
            if use_reranking and len(retrieved_docs) > max_chunks:
                retrieved_docs = self._rerank_documents(user_question, retrieved_docs, top_k=max_chunks)
                used_reranking = True
        
        if not retrieved_docs:
            return RAGResponse(
                answer="No encontré información relevante en la base de conocimiento para responder tu pregunta.",
                sources=[],
                confidence=0.0,
                chunks_used=0,
                reranked=used_reranking,
                metadata={"error": "No documents retrieved"}
            )
        
        # 2. Construir contexto con chunks relevantes
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
        
        # Determinar si se usó reranking
        final_reranked = used_reranking if 'used_reranking' in locals() else use_reranking
        
        response = RAGResponse(
            answer=answer,
            sources=sources,
            confidence=confidence,
            chunks_used=len(context_chunks),
            reranked=final_reranked,
            metadata={
                "chatbot_name": connection.chatbot_name,
                "company_name": connection.company_name,
                "cached": False,
                "advanced_rag": self.use_advanced_rag
            }
        )
        
        # Guardar en caché
        if use_cache:
            cache_key = self._get_cache_key(chatbot_id, user_question)
            self._cache_response(cache_key, response)
        
        return response
    
    def query_chatbot_stream(
        self,
        chatbot_id: str,
        user_question: str,
        use_reranking: bool = True,
        max_chunks: int = 5
    ):
        """
        Consulta el RAG y genera respuesta en streaming (palabra por palabra).
        
        Yields:
            Fragmentos de la respuesta mientras se genera
        """
        if chatbot_id not in self.connections:
            yield "Error: Chatbot no encontrado"
            return
        
        if chatbot_id not in self.retrievers:
            yield "Error: Chatbot no tiene data procesada"
            return
        
        connection = self.connections[chatbot_id]
        retriever = self.retrievers[chatbot_id]
        
        # 1. Retrieval: Obtener chunks relevantes
        retrieved_docs = retriever.invoke(user_question)
        
        if not retrieved_docs:
            yield "No encontré información relevante en la base de conocimiento."
            return
        
        # 2. Reranking (opcional)
        if use_reranking and len(retrieved_docs) > max_chunks:
            retrieved_docs = self._rerank_documents(user_question, retrieved_docs, top_k=max_chunks)
        
        # 3. Construir contexto
        context_chunks = retrieved_docs[:max_chunks]
        context = self._build_context(context_chunks)
        
        # 4. Generar respuesta con streaming
        internal_prompt = f"""Eres un asistente de {connection.company_name}. Tu tarea es responder preguntas de usuarios usando ÚNICAMENTE la información proporcionada en los documentos de la empresa.

INSTRUCCIONES CRÍTICAS:
1. Usa SOLO la información de los documentos proporcionados para responder
2. NO inventes información que no esté en los documentos
3. Si la información no está en los documentos, di claramente: "No tengo información sobre esto en la base de conocimiento de {connection.company_name}"
4. Sé preciso y específico
5. Cita las fuentes cuando sea relevante

DOCUMENTOS DE LA EMPRESA:
{context}

PREGUNTA DEL USUARIO:
{user_question}

RESPUESTA (usa solo información de los documentos):"""
        
        try:
            # Generar con streaming usando LangChain
            for chunk in self.llm.stream(internal_prompt):
                if hasattr(chunk, 'content') and chunk.content:
                    yield chunk.content
                elif isinstance(chunk, str):
                    yield chunk
        except Exception as e:
            yield f"Error generando respuesta: {str(e)}"
    
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

