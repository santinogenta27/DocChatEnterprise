"""RAG Manager - Gestiona todo el sistema RAG avanzado para STAR AGENT.

Integra el sistema completo Multi-Agente DocChat:
- ðŸ” Relevance Checker: Verifica si la pregunta es relevante a los documentos
- ðŸ”¬ Research Agent: Genera respuestas iniciales basadas en documentos recuperados
- âœ… Verification Agent: Verifica que las respuestas estÃ©n soportadas (anti-hallucinaciÃ³n)
- ðŸ”„ Self-Correction Mechanism: Re-ejecuta research si hay contradicciones o claims sin soporte
- ðŸ”€ Hybrid Retriever: Combina BM25 (bÃºsqueda lÃ©xica) + Vector Search (bÃºsqueda semÃ¡ntica)
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
            app_config: ConfiguraciÃ³n de la app (para embeddings)
            documents_dir: Directorio donde se guardan los documentos procesados
        """
        self.llm = llm
        self.app_config = app_config
        self.documents_dir = documents_dir or Path("docchat/star_agent/documents")
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
        
        # Inicializar document processor (solo si Docling estÃ¡ disponible)
        try:
            self.document_processor = DocumentProcessor(
                cache_dir=self.documents_dir / "cache"
            )
        except ImportError:
            print("âš ï¸ Docling no disponible. Instala con: pip install docling")
            self.document_processor = None
        
        # Inicializar sistema multi-agente si estÃ¡ disponible
        if AGENT_WORKFLOW_AVAILABLE and app_config:
            try:
                self.retriever_builder = RetrieverBuilder(config=app_config)
                self.agent_workflow = AgentWorkflow(config=app_config, provider="openai")
                print("âœ… Sistema Multi-Agente DocChat inicializado (modo Alien)")
            except Exception as e:
                print(f"âš ï¸ Error inicializando sistema multi-agente: {e}")
                self.agent_workflow = None
    
    def _initialize_embeddings(self):
        """Inicializa embeddings para vector search."""
        if not OPENAI_EMBEDDINGS_AVAILABLE:
            print("âš ï¸ OpenAIEmbeddings no disponible")
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
                print(f"âœ… Embeddings inicializados: {model}")
            else:
                print("âš ï¸ No hay OpenAI API key configurada para embeddings")
        except Exception as e:
            print(f"âš ï¸ Error inicializando embeddings: {e}")
    
    def process_documents(self, files: List[Any]) -> bool:
        """Procesa documentos y crea el retriever (usando sistema optimizado como Alien Mode).
        
        Args:
            files: Lista de archivos (paths o objetos de Gradio)
            
        Returns:
            True si se procesaron correctamente
        """
        if not self.document_processor:
            print("âš ï¸ DocumentProcessor no disponible (Docling no instalado)")
            return False
        
        if not self.embeddings:
            print("âš ï¸ Embeddings no disponibles")
            return False
        
        try:
            # Procesar documentos (PyPDF2 primero para velocidad, como Alien Mode)
            chunks = self.document_processor.process(files)
            
            if not chunks:
                print("âš ï¸ No se generaron chunks de los documentos")
                return False
            
            print(f"âœ… Procesados {len(chunks)} chunks de documentos")
            
            # Guardar todos los documentos para el sistema multi-agente
            self.all_documents = chunks
            
            # Crear directorio para ChromaDB
            chroma_dir = self.documents_dir / "chroma_db"
            chroma_dir.mkdir(parents=True, exist_ok=True)
            
            # Usar RetrieverBuilder del sistema DocChat si estÃ¡ disponible (mejor optimizado)
            if self.retriever_builder:
                try:
                    self.retriever = self.retriever_builder.build_hybrid_retriever(chunks)
                    print("âœ… Hybrid Retriever creado con sistema DocChat (modo Alien)")
                except Exception as e:
                    print(f"âš ï¸ Error con RetrieverBuilder, usando mÃ©todo bÃ¡sico: {e}")
                    # Fallback a mÃ©todo bÃ¡sico
                    self.retriever = build_hybrid_retriever(
                        documents=chunks,
                        embeddings=self.embeddings,
                        persist_directory=chroma_dir,
                        k=5,
                        weights=(0.4, 0.6),  # 40% BM25, 60% Vector
                    )
                    print("âœ… Hybrid Retriever creado exitosamente (mÃ©todo bÃ¡sico)")
            else:
                # MÃ©todo bÃ¡sico como fallback
                self.retriever = build_hybrid_retriever(
                    documents=chunks,
                    embeddings=self.embeddings,
                    persist_directory=chroma_dir,
                    k=5,
                    weights=(0.4, 0.6),  # 40% BM25, 60% Vector
                )
                print("âœ… Hybrid Retriever creado exitosamente")
            
            return True
            
        except Exception as e:
            print(f"âŒ Error procesando documentos: {e}")
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
            verification: Si hacer verification (siempre True con multi-agente para anti-hallucinaciÃ³n)
            
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
        
        # Usar sistema multi-agente completo si estÃ¡ disponible (modo Alien)
        if self.agent_workflow and verification:
            try:
                print("ðŸš€ Usando sistema Multi-Agente DocChat (modo Alien)...")
                
                # Ejecutar workflow completo: Relevance Checker â†’ Research Agent â†’ Verification Agent â†’ Self-Correction
                result = self.agent_workflow.full_pipeline(
                    question=question,
                    retriever=self.retriever,
                    all_documents=self.all_documents,  # Pasar todos los documentos para anÃ¡lisis completo
                )
                
                answer = result.get("answer", "")
                scope_status = result.get("relevance_label", "CAN_ANSWER")
                context_used = result.get("context_used", "")
                
                # Si no hay respuesta, intentar con mÃ©todo bÃ¡sico
                if not answer:
                    print("âš ï¸ Sistema multi-agente no generÃ³ respuesta, usando mÃ©todo bÃ¡sico...")
                    return self._query_basic(question, scope_checking)
                
                return {
                    "answer": answer,
                    "scope_status": scope_status,
                    "context_used": context_used,
                    "documents_count": len(result.get("context_docs", [])),
                    "verification_passed": result.get("verification", {}).get("supported", False) if result.get("verification") else True,
                }
                
            except Exception as e:
                print(f"âš ï¸ Error en sistema multi-agente: {e}")
                import traceback
                traceback.print_exc()
                print("âš ï¸ Usando mÃ©todo bÃ¡sico como fallback...")
                return self._query_basic(question, scope_checking)
        else:
            # MÃ©todo bÃ¡sico como fallback
            return self._query_basic(question, scope_checking)
    
    def _query_basic(
        self,
        question: str,
        scope_checking: bool = True,
    ) -> Dict[str, Any]:
        """MÃ©todo bÃ¡sico de consulta (fallback si el sistema multi-agente no estÃ¡ disponible)."""
        try:
            # 1. Recuperar documentos relevantes
            try:
                # Intentar con parÃ¡metro k
                relevant_docs = self.retriever.get_relevant_documents(question, k=5)
            except TypeError:
                # Si no acepta k, usar mÃ©todo estÃ¡ndar
                relevant_docs = self.retriever.get_relevant_documents(question)[:5]
            
            if not relevant_docs:
                return {
                    "answer": "No encontrÃ© documentos relevantes para responder tu pregunta.",
                    "scope_status": "NO_MATCH",
                    "context_used": "",
                }
            
            # 2. Generar respuesta bÃ¡sica con LLM
            from langchain_core.prompts import ChatPromptTemplate
            
            context = "\n\n".join([doc.page_content[:1000] for doc in relevant_docs[:5]])  # Limitar contexto
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", "Eres un asistente que responde preguntas basÃ¡ndose ÃšNICAMENTE en el contexto proporcionado. Si la informaciÃ³n no estÃ¡ en el contexto, di que no tienes esa informaciÃ³n."),
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
            print(f"âš ï¸ Error en query bÃ¡sico: {e}")
            import traceback
            traceback.print_exc()
            return {
                "answer": "",
                "scope_status": "ERROR",
                "context_used": "",
                "error": str(e),
            }

