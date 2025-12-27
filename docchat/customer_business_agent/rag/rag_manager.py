"""RAG Manager - Gestiona todo el sistema RAG avanzado para Customer Business Agent.

Integra el sistema completo Multi-Agente DocChat:
- 🔍 Relevance Checker: Verifica si la pregunta es relevante a los documentos
- 🔬 Research Agent: Genera respuestas iniciales basadas en documentos recuperados
- ✅ Verification Agent: Verifica que las respuestas estén soportadas (anti-hallucinación)
- 🔄 Self-Correction Mechanism: Re-ejecuta research si hay contradicciones o claims sin soporte
- 🔀 Hybrid Retriever: Combina BM25 (búsqueda léxica) + Vector Search (búsqueda semántica)
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Dict, Any

from langchain_core.retrievers import BaseRetriever
from langchain_core.language_models import BaseLanguageModel
from langchain_core.embeddings import Embeddings
from langchain_core.documents import Document

try:
    from langchain_openai import OpenAIEmbeddings
    OPENAI_EMBEDDINGS_AVAILABLE = True
except ImportError:
    OPENAI_EMBEDDINGS_AVAILABLE = False
    OpenAIEmbeddings = None

from .document_processor import DocumentProcessor
from .hybrid_retriever import build_hybrid_retriever, HybridRetriever

# Importar sistema multi-agente completo de DocChat
try:
    from ...workflow import AgentWorkflow
    from ...retriever_builder import RetrieverBuilder
    AGENT_WORKFLOW_AVAILABLE = True
except ImportError:
    AGENT_WORKFLOW_AVAILABLE = False
    AgentWorkflow = None
    RetrieverBuilder = None


class RAGManager:
    """Gestiona el sistema RAG completo con Multi-Agente DocChat (modo Alien)."""
    
    def __init__(
        self,
        llm: BaseLanguageModel,
        app_config: Optional[Any] = None,
        documents_dir: Optional[Path] = None,
    ):
        """Inicializa el RAG Manager con sistema multi-agente completo.
        
        Args:
            llm: Modelo de lenguaje para generar respuestas y scope checking
            app_config: Configuración de la app (para embeddings)
            documents_dir: Directorio donde se guardan los documentos procesados
        """
        self.llm = llm
        self.app_config = app_config
        self.documents_dir = documents_dir or Path("docchat/customer_business_agent/documents")
        self.documents_dir.mkdir(parents=True, exist_ok=True)
        
        # Inicializar componentes
        self.document_processor = None
        self.embeddings = None
        self.retriever: Optional[BaseRetriever] = None
        self.all_documents: List[Document] = []  # Todos los documentos procesados
        
        # Sistema multi-agente DocChat (modo Alien)
        self.agent_workflow: Optional[AgentWorkflow] = None
        self.retriever_builder: Optional[RetrieverBuilder] = None
        
        # Inicializar embeddings
        self._initialize_embeddings()
        
        # Inicializar document processor (solo si Docling está disponible)
        try:
            self.document_processor = DocumentProcessor(
                cache_dir=self.documents_dir / "cache"
            )
        except ImportError:
            print("⚠️ Docling no disponible. Instala con: pip install docling")
            self.document_processor = None
        
        # Inicializar sistema multi-agente si está disponible
        if AGENT_WORKFLOW_AVAILABLE and app_config:
            try:
                self.retriever_builder = RetrieverBuilder(config=app_config)
                self.agent_workflow = AgentWorkflow(config=app_config, provider="openai")
                print("✅ Sistema Multi-Agente DocChat inicializado (modo Alien)")
            except Exception as e:
                print(f"⚠️ Error inicializando sistema multi-agente: {e}")
                self.agent_workflow = None
    
    def _initialize_embeddings(self):
        """Inicializa embeddings para vector search."""
        if not OPENAI_EMBEDDINGS_AVAILABLE:
            print("⚠️ OpenAIEmbeddings no disponible")
            return
        
        try:
            # Usar API key de app_config o de entorno
            api_key = None
            model = "text-embedding-3-small"
            
            if self.app_config:
                api_key = getattr(self.app_config, "openai_api_key", None)
                model = getattr(self.app_config, "embedding_model", "text-embedding-3-small")
            
            if not api_key:
                import os
                api_key = os.getenv("OPENAI_API_KEY", "")
            
            if api_key:
                self.embeddings = OpenAIEmbeddings(
                    model=model,
                    openai_api_key=api_key,
                )
                print(f"✅ Embeddings inicializados: {model}")
            else:
                print("⚠️ No hay OpenAI API key configurada para embeddings")
        except Exception as e:
            print(f"⚠️ Error inicializando embeddings: {e}")
    
    def process_documents(self, files: List[Any]) -> bool:
        """Procesa documentos y crea el retriever (usando sistema optimizado como Alien Mode).
        
        Args:
            files: Lista de archivos (paths o objetos de Gradio)
            
        Returns:
            True si se procesaron correctamente
        """
        if not self.document_processor:
            print("⚠️ DocumentProcessor no disponible (Docling no instalado)")
            return False
        
        if not self.embeddings:
            print("⚠️ Embeddings no disponibles")
            return False
        
        try:
            # Procesar documentos (PyPDF2 primero para velocidad, como Alien Mode)
            chunks = self.document_processor.process(files)
            
            if not chunks:
                print("⚠️ No se generaron chunks de los documentos")
                return False
            
            print(f"✅ Procesados {len(chunks)} chunks de documentos")
            
            # Guardar todos los documentos para el sistema multi-agente
            self.all_documents = chunks
            
            # Crear directorio para ChromaDB
            chroma_dir = self.documents_dir / "chroma_db"
            chroma_dir.mkdir(parents=True, exist_ok=True)
            
            # Usar RetrieverBuilder del sistema DocChat si está disponible (mejor optimizado)
            if self.retriever_builder:
                try:
                    self.retriever = self.retriever_builder.build_hybrid_retriever(chunks)
                    print("✅ Hybrid Retriever creado con sistema DocChat (modo Alien)")
                except Exception as e:
                    print(f"⚠️ Error con RetrieverBuilder, usando método básico: {e}")
                    # Fallback a método básico
                    self.retriever = build_hybrid_retriever(
                        documents=chunks,
                        embeddings=self.embeddings,
                        persist_directory=chroma_dir,
                        k=5,
                        weights=(0.4, 0.6),  # 40% BM25, 60% Vector
                    )
                    print("✅ Hybrid Retriever creado exitosamente (método básico)")
            else:
                # Método básico como fallback
                self.retriever = build_hybrid_retriever(
                    documents=chunks,
                    embeddings=self.embeddings,
                    persist_directory=chroma_dir,
                    k=5,
                    weights=(0.4, 0.6),  # 40% BM25, 60% Vector
                )
                print("✅ Hybrid Retriever creado exitosamente")
            
            return True
            
        except Exception as e:
            print(f"❌ Error procesando documentos: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def query(
        self,
        question: str,
        scope_checking: bool = True,
        verification: bool = True,  # Activado por defecto para usar sistema completo
    ) -> Dict[str, Any]:
        """Consulta el RAG con una pregunta usando el sistema multi-agente completo (modo Alien).
        
        Args:
            question: Pregunta del usuario
            scope_checking: Si hacer scope checking primero (siempre True con multi-agente)
            verification: Si hacer verification (siempre True con multi-agente para anti-hallucinación)
            
        Returns:
            Dict con 'answer', 'scope_status', 'context_used'
        """
        if not self.retriever:
            return {
                "answer": "",
                "scope_status": "NO_RETRIEVER",
                "context_used": "",
                "error": "No hay retriever inicializado. Procesa documentos primero.",
            }
        
        # Usar sistema multi-agente completo si está disponible (modo Alien)
        if self.agent_workflow and verification:
            try:
                print("🚀 Usando sistema Multi-Agente DocChat (modo Alien)...")
                
                # Ejecutar workflow completo: Relevance Checker → Research Agent → Verification Agent → Self-Correction
                result = self.agent_workflow.full_pipeline(
                    question=question,
                    retriever=self.retriever,
                    all_documents=self.all_documents,  # Pasar todos los documentos para análisis completo
                )
                
                answer = result.get("answer", "")
                scope_status = result.get("relevance_label", "CAN_ANSWER")
                context_used = result.get("context_used", "")
                
                # Si no hay respuesta, intentar con método básico
                if not answer:
                    print("⚠️ Sistema multi-agente no generó respuesta, usando método básico...")
                    return self._query_basic(question, scope_checking)
                
                return {
                    "answer": answer,
                    "scope_status": scope_status,
                    "context_used": context_used,
                    "documents_count": len(result.get("context_docs", [])),
                    "verification_passed": result.get("verification", {}).get("supported", False) if result.get("verification") else True,
                }
                
            except Exception as e:
                print(f"⚠️ Error en sistema multi-agente: {e}")
                import traceback
                traceback.print_exc()
                print("⚠️ Usando método básico como fallback...")
                return self._query_basic(question, scope_checking)
        else:
            # Método básico como fallback
            return self._query_basic(question, scope_checking)
    
    def _query_basic(
        self,
        question: str,
        scope_checking: bool = True,
    ) -> Dict[str, Any]:
        """Método básico de consulta (fallback si el sistema multi-agente no está disponible)."""
        try:
            # 1. Recuperar documentos relevantes
            try:
                # Intentar con parámetro k
                relevant_docs = self.retriever.get_relevant_documents(question, k=5)
            except TypeError:
                # Si no acepta k, usar método estándar
                relevant_docs = self.retriever.get_relevant_documents(question)[:5]
            
            if not relevant_docs:
                return {
                    "answer": "No encontré documentos relevantes para responder tu pregunta.",
                    "scope_status": "NO_MATCH",
                    "context_used": "",
                }
            
            # 2. Generar respuesta básica con LLM
            from langchain_core.prompts import ChatPromptTemplate
            
            context = "\n\n".join([doc.page_content[:1000] for doc in relevant_docs[:5]])  # Limitar contexto
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", "Eres un asistente que responde preguntas basándose ÚNICAMENTE en el contexto proporcionado. Si la información no está en el contexto, di que no tienes esa información."),
                ("human", "Contexto:\n{context}\n\nPregunta: {question}\n\nRespuesta:")
            ])
            
            chain = prompt | self.llm
            response = chain.invoke({"context": context, "question": question})
            
            answer = response.content if hasattr(response, "content") else str(response)
            
            return {
                "answer": answer,
                "scope_status": "CAN_ANSWER",
                "context_used": context[:500],  # Limitar para mostrar
                "documents_count": len(relevant_docs),
            }
            
        except Exception as e:
            print(f"⚠️ Error en query básico: {e}")
            import traceback
            traceback.print_exc()
            return {
                "answer": "",
                "scope_status": "ERROR",
                "context_used": "",
                "error": str(e),
            }
