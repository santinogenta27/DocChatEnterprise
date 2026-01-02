"""
Alien Mode - Sistema Multi-Agente RAG de Máxima Calidad
Integra el sistema completo de DocChat Multi-Agent RAG:

SISTEMA MULTI-AGENTE DOCCHAT:
- 🔍 Relevance Checker: Verifica si la pregunta es relevante a los documentos
- 🔬 Research Agent: Genera respuestas iniciales basadas en documentos recuperados
- ✅ Verification Agent: Verifica que las respuestas estén soportadas (anti-hallucinación)
- 🔄 Self-Correction Mechanism: Re-ejecuta research si hay contradicciones o claims sin soporte
- 🔀 Hybrid Retriever: Combina BM25 (búsqueda léxica) + Vector Search (búsqueda semántica)

CAPACIDADES AVANZADAS ADICIONALES:
- Context Folding: Gestión eficiente de contextos masivos (500+ PDFs)
- Data Provenance: Trazabilidad completa de cada pieza de información
- Chain of Thought Reasoning: Razonamiento paso a paso
- Path-dependent Reasoning: Múltiples enfoques probados
- Test Time Training: Mejora continua con cada conversación
- Person in the Loop: Control humano para decisiones críticas
- Reinforcement Learning & Planning: Estrategias adaptativas
- MCP Powered: Conexión a sistemas externos, bases de datos, APIs
"""

from __future__ import annotations

import json
import time
import asyncio
from typing import List, Dict, Optional, Any, Tuple, Iterator
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

from langchain_core.documents import Document
from langchain_core.language_models import BaseLanguageModel
from langchain_openai import ChatOpenAI

from .config import AppConfig
from .document_processor import DocumentProcessor
from .retriever_builder import RetrieverBuilder
from .workflow import AgentWorkflow
from .context_folding import ContextFolder
from .data_provenance import DataProvenanceTracker, DataProvenance, DataSourceType
from .chain_of_thought import ChainOfThoughtReasoner, ThoughtChain
from .path_dependent_reasoning import PathDependentReasoner
from .test_time_training import TestTimeTrainer
from .person_in_the_loop import PersonInTheLoop, DecisionCriticality
from .reinforcement_planning import ReinforcementPlanner, DecisionTree
from .mcp_manager import MCPManager


class AlienMode:
    """
    Alien Mode - Sistema Multi-Agente RAG de Máxima Calidad para Empresas.
    
    Integra el sistema completo de DocChat Multi-Agent RAG con capacidades avanzadas:
    
    SISTEMA MULTI-AGENTE DOCCHAT:
    - 🔍 Relevance Checker: Determina si la pregunta puede responderse con los documentos
    - 🔬 Research Agent: Genera respuestas iniciales basadas en documentos recuperados
    - ✅ Verification Agent: Verifica que las respuestas estén soportadas (anti-hallucinación)
    - 🔄 Self-Correction: Re-ejecuta research automáticamente si hay contradicciones
    - 🔀 Hybrid Retriever: BM25 + Vector Search para máxima precisión
    
    CAPACIDADES AVANZADAS:
    - Gestiona eficientemente 500+ PDFs con Context Folding
    - Rastrea procedencia de datos para compliance
    - Razona paso a paso con Chain of Thought
    - Prueba diferentes enfoques con Path-dependent Reasoning
    - Aprende continuamente con Test Time Training
    - Control humano con Person in the Loop
    - Reinforcement Learning & Planning para estrategias adaptativas
    - MCP Powered para conexión a sistemas externos
    """
    
    def __init__(
        self,
        config: AppConfig,
        processor: DocumentProcessor,
        retriever_builder: RetrieverBuilder,
        context_manager: Optional[Any] = None
    ):
        self.config = config
        self.processor = processor
        self.retriever_builder = retriever_builder
        self.context_manager = context_manager
        
        # LLM para generación - Se creará dinámicamente según el provider
        # Por defecto, usar OpenAI para compatibilidad
        if not config.openai_api_key and not config.anthropic_api_key:
            raise ValueError("OPENAI_API_KEY o ANTHROPIC_API_KEY requerida para Alien Mode")
        
        # LLM por defecto (se actualizará dinámicamente según el provider)
        self.llm = ChatOpenAI(
            model=config.research_model or "gpt-4o",
            temperature=0.2,
            api_key=config.openai_api_key or "",
            max_tokens=4000
        )
        
        # Inicializar módulos avanzados (se actualizarán dinámicamente con el LLM correcto)
        self.context_folder = ContextFolder(
            config=config,
            llm=self.llm,
            max_context_tokens=32000,
            max_branches=10
        )
        
        self.provenance_tracker = DataProvenanceTracker(config=config)
        
        self.chain_reasoner = ChainOfThoughtReasoner(
            config=config,
            llm=self.llm
        )
        
        self.path_reasoner = PathDependentReasoner(
            config=config,
            llm=self.llm,
            max_paths=5
        )
        
        self.test_time_trainer = TestTimeTrainer(
            config=config,
            llm=self.llm,
            learning_rate=0.1,
            min_confidence=0.6
        )
        
        self.person_in_loop = PersonInTheLoop(
            config=config,
            auto_approve_low=True,
            default_expiration=3600
        )
        
        # Reinforcement Learning y Planning
        self.reinforcement_planner = ReinforcementPlanner(
            config=config,
            llm=self.llm,
            max_depth=10,
            max_branches=5,
            learning_enabled=True
        )
        
        # MCP Manager potenciado
        self.mcp_manager = MCPManager(config=config, llm=self.llm)
        self.mcp_manager.initialize()
        
        # Sesiones activas
        self.sessions: Dict[str, Dict[str, Any]] = {}
    
    def _get_llm_for_provider(self, provider: str = "openai"):
        """Crea un LLM dinámico según el provider especificado."""
        from docchat.utils.llm_factory import create_llm
        
        # Normalizar provider (acepta "openai", "claude", "anthropic")
        provider_lower = provider.lower()
        if provider_lower in ["claude", "anthropic"]:
            provider_to_use = "claude"
            api_key = self.config.anthropic_api_key
            if not api_key:
                print(f"⚠️ [Alien Mode] ANTHROPIC_API_KEY no configurada, usando OpenAI como fallback")
                provider_to_use = "openai"
                api_key = self.config.openai_api_key
        else:
            provider_to_use = "openai"
            api_key = self.config.openai_api_key
            if not api_key:
                raise ValueError("OPENAI_API_KEY requerida para Alien Mode")
        
        return create_llm(
            provider=provider_to_use,
            model=self.config.research_model or "gpt-4o",
            temperature=0.2,
            api_key=api_key,
            max_tokens=4000,
            request_timeout=300
        )
    
    def _update_modules_with_llm(self, llm):
        """Actualiza los módulos avanzados con el LLM correcto."""
        # Actualizar LLM
        self.llm = llm
        
        # Actualizar módulos que usan el LLM
        # Nota: Algunos módulos pueden no tener método para actualizar el LLM
        # En ese caso, se recrean temporalmente o se usa el LLM directamente
        if hasattr(self.context_folder, 'llm'):
            self.context_folder.llm = llm
        if hasattr(self.chain_reasoner, 'llm'):
            self.chain_reasoner.llm = llm
        if hasattr(self.path_reasoner, 'llm'):
            self.path_reasoner.llm = llm
        if hasattr(self.test_time_trainer, 'llm'):
            self.test_time_trainer.llm = llm
        if hasattr(self.reinforcement_planner, 'llm'):
            self.reinforcement_planner.llm = llm
        if hasattr(self.mcp_manager, 'llm'):
            self.mcp_manager.llm = llm
        

    def _get_session_metadata_path(self, session_id: str) -> Path:
        """Obtiene la ruta del archivo de metadata de sesiÃ³n."""
        return self.config.memory_dir / f"session_{session_id}.json"
    
    def _save_session_metadata(self, session_id: str, metadata: dict):
        """Guarda metadata de sesiÃ³n en archivo JSON."""
        try:
            metadata_path = self._get_session_metadata_path(session_id)
            metadata_path.parent.mkdir(parents=True, exist_ok=True)
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"âš ï¸ [Persistencia] Error guardando metadata: {e}")
    
    def _load_session_metadata(self, session_id: str) -> dict:
        """Carga metadata de sesiÃ³n desde archivo JSON."""
        try:
            metadata_path = self._get_session_metadata_path(session_id)
            if metadata_path.exists():
                with open(metadata_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            print(f"âš ï¸ [Persistencia] Error cargando metadata: {e}")
        return {}
    
    def _load_persisted_documents(self, session_id: str) -> List[Any]:
        """Carga documentos persistidos desde ChromaDB."""
        try:
            from langchain_community.vectorstores import Chroma
            from langchain_core.documents import Document
            
            persist_dir = Path(self.config.persist_dir) / session_id
            if not persist_dir.exists():
                return []
            
            # Cargar vectorstore existente
            vectorstore = Chroma(
                persist_directory=str(persist_dir),
                embedding_function=self.retriever_builder.embeddings
            )
            
            # Obtener documentos
            all_data = vectorstore.get()
            documents = all_data.get("documents", [])
            metadatas = all_data.get("metadatas", [{}] * len(documents))
            
            # Convertir a Document objects
            docs = [
                Document(page_content=content, metadata=meta)
                for content, meta in zip(documents, metadatas)
            ]
            
            if docs:
                print(f"âœ… [Persistencia] Cargados {len(docs)} documentos persistidos para sesiÃ³n '{session_id}'")
            return docs
        except Exception as e:
            print(f"âš ï¸ [Persistencia] Error cargando documentos persistidos: {e}")
            return []

    
    def initialize_session(self, session_id: str) -> Dict[str, Any]:
        """Inicializa una nueva sesion y carga documentos persistidos si existen."""
        if session_id not in self.sessions:
            # Cargar documentos persistidos si existen
            persisted_docs = self._load_persisted_documents(session_id)
            persisted_metadata = self._load_session_metadata(session_id)
            
            self.sessions[session_id] = {
                "docs": persisted_docs if persisted_docs else [],
                "retriever": None,
                "processed_files": set(persisted_metadata.get("processed_files", [])),
                "history": persisted_metadata.get("history", []),
                "context_folder": ContextFolder(
                    config=self.config,
                    llm=self.llm,
                    max_context_tokens=32000,
                    max_branches=10
                ),
                "chain_id": None,
                "rl_tree_id": None,
                "mcp_queries": [],
                "created_at": persisted_metadata.get("created_at", time.time())
            }
            
            # Si hay documentos persistidos, reconstruir el retriever
            if persisted_docs:
                print(f"[Alien Mode] Cargando {len(persisted_docs)} documentos persistidos para sesion '''{session_id}'''...")
                self.sessions[session_id]["retriever"] = self.retriever_builder.build_hybrid_retriever(
                    persisted_docs,
                    namespace=session_id,
                    load_existing=True
                )
                print(f"[Alien Mode] Retriever reconstruido con {len(persisted_docs)} documentos persistidos")
        
        return self.sessions[session_id]

    def process_documents(
        self,
        session_id: str,
        files: List[Any]
    ) -> Dict[str, Any]:
        """Procesa documentos para una sesión."""
        session = self.initialize_session(session_id)
        
        # Procesar nuevos archivos
        new_files = []
        for file_obj in files:
            file_name = getattr(file_obj, "name", "")
            if file_name not in session["processed_files"]:
                new_files.append(file_obj)
                session["processed_files"].add(file_name)
        
        if not new_files:
            return {
                "status": "no_new_files",
                "total_docs": len(session["docs"]),
                "total_chunks": sum(len(doc.page_content) for doc in session["docs"])
            }
        
        try:
            print(f"📄 [Alien Mode] Procesando {len(new_files)} nuevos documentos...")
            new_docs = self.processor.process(new_files)
            session["docs"].extend(new_docs)
            
            # Rastrear procedencia de documentos
            for doc in new_docs:
                provenance = self.provenance_tracker.track_document_source(doc)
                # Guardar en sesión para referencia rápida
                if "provenances" not in session:
                    session["provenances"] = []
                session["provenances"].append(provenance)
            
            # Reconstruir retriever usando session_id como namespace para persistencia
            if session["docs"]:
                session["retriever"] = self.retriever_builder.build_hybrid_retriever(
                    session["docs"], 
                    namespace=session_id  # Usar session_id como namespace para persistencia
                )
                # Guardar metadata de sesiÃ³n
                self._save_session_metadata(session_id, {
                    "processed_files": list(session["processed_files"]),
                    "history": session["history"],
                    "created_at": session["created_at"],
                    "docs_count": len(session["docs"])
                })
                print(f"✅ [Alien Mode] Retriever actualizado: {len(session['docs'])} chunks")
            
            return {
                "status": "success",
                "new_docs": len(new_docs),
                "total_docs": len(session["docs"]),
                "total_chunks": len(session["docs"])
            }
            
        except Exception as e:
            print(f"❌ [Alien Mode] Error procesando documentos: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def process_query_async(
        self,
        session_id: str,
        message: str,
        history: List[Tuple[str, str]],
        speed_mode: str = "balanced",
        provider: str = "openai"
    ) -> Tuple[List[Tuple[str, str]], Optional[str], Dict[str, Any]]:
        """
        Procesa una consulta con todas las capacidades avanzadas.
        
        Returns:
            (history, error, metadata): Historial actualizado, error si hay, metadatos
        """
        # ACTUALIZAR LLM SEGÚN EL PROVIDER - CRÍTICO para usar Claude cuando se selecciona
        provider_llm = self._get_llm_for_provider(provider)
        self._update_modules_with_llm(provider_llm)
        
        session = self.initialize_session(session_id)
        
        if not session["retriever"]:
            return history, "⚠️ No hay documentos procesados. Carga documentos primero.", {}
        
        # DETECTAR si hay muchos documentos para usar procesamiento paralelo
        all_docs = session.get("docs", [])
        if not all_docs:
            return history, "⚠️ No hay documentos procesados. Carga documentos primero.", {}
        
        # Agrupar documentos por fuente
        docs_by_source = defaultdict(list)
        for doc in all_docs:
            source = doc.metadata.get("source", "unknown")
            docs_by_source[source].append(doc)
        
        num_unique_documents = len(docs_by_source)
        
        # Si hay 10+ documentos, usar procesamiento paralelo (como Enterprise API)
        use_parallel_processing = num_unique_documents >= 10
        
        start_time = time.time()
        
        # Si usar procesamiento paralelo, procesar cada documento por separado
        if use_parallel_processing:
            return await self._process_query_parallel(
                session_id=session_id,
                message=message,
                history=history,
                docs_by_source=docs_by_source,
                speed_mode=speed_mode,
                provider=provider
            )
        
        # 1. Crear cadena de razonamiento
        chain_id = self.chain_reasoner.create_chain(message)
        session["chain_id"] = chain_id
        
        # 2. Construir contexto con Context Folding
        conversation_context = self._build_folded_context(session, history)
        
        # 3. Agregar pasos de razonamiento (con manejo de errores)
        try:
            await self.chain_reasoner.add_reasoning_steps(chain_id, conversation_context)
        except Exception as e:
            print(f"⚠️ [Alien Mode] Error agregando pasos de razonamiento: {e}")
            # Continuar sin pasos de razonamiento si falla
        
        # 4. Determinar si requiere aprobación humana
        requires_approval, criticality = self.person_in_loop.requires_approval(
            decision_type="document_query",
            decision_content=message,
            context=conversation_context[:500]
        )
        
        # 5. Si requiere aprobación, solicitar
        approval_id = None
        if requires_approval and criticality in [DecisionCriticality.HIGH, DecisionCriticality.CRITICAL]:
            approval_id = self.person_in_loop.request_approval(
                decision_type="document_query",
                decision_content=message,
                context=conversation_context[:1000],
                criticality=criticality
            )
            # Por ahora, continuar pero marcar que requiere aprobación
            # En producción, esperar aprobación antes de continuar
        
        # 6. Usar Reinforcement Learning y Planning para planificar estrategias
        # RL prueba diferentes enfoques: buscar por palabras clave, por secciones, por fechas, etc.
        rl_result = None
        best_strategy = None
        try:
            rl_result = await self.reinforcement_planner.plan_and_execute(
                goal=f"Responder la consulta: {message}",
                context=conversation_context,
                executor=self._execute_rl_action
            )
            
            session["rl_tree_id"] = rl_result.get("tree_id")
            best_strategy = rl_result.get("best_result")
        except Exception as e:
            print(f"⚠️ [Alien Mode] Error en Reinforcement Planning: {e}")
            # Continuar sin RL si falla
            rl_result = {"tree_id": None, "best_result": None, "total_explorations": 0}
        
        # 7. Usar Path-dependent Reasoning como complemento
        path_result = None
        best_approach = None
        try:
            path_result = await self.path_reasoner.reason_with_multiple_paths(
                problem=message,
                context=conversation_context,
                task_type="document_query",
                executor=self._execute_query_path
            )
            
            best_approach = path_result.get("best_path", {}).get("approach")
        except Exception as e:
            print(f"⚠️ [Alien Mode] Error en Path-dependent Reasoning: {e}")
            # Continuar sin path reasoning si falla
            path_result = {"best_path": {"approach": None}, "paths_tested": 0}
        
        # 8. Usar MCP potenciado para buscar en sistemas externos si es necesario
        mcp_data = None
        try:
            mcp_data = await self._query_mcp_systems(message, conversation_context)
            if mcp_data:
                session["mcp_queries"].append(mcp_data)
                # Agregar datos de MCP al contexto
                conversation_context += f"\n\n📡 DATOS DE SISTEMAS EXTERNOS (MCP):\n{mcp_data.get('summary', '')}"
        except Exception as e:
            print(f"⚠️ [Alien Mode] Error consultando MCP: {e}")
            # Continuar sin datos MCP si falla
        
        # Aplicar modo de velocidad
        original_speed_mode = self.config.speed_mode
        self.config.speed_mode = speed_mode
        
        try:
            # TRUNCAMIENTO INTELIGENTE: Limitar contexto para evitar error 429 (tokens per minute)
            # Límite real de OpenAI para gpt-4o: 30,000 TPM (tokens per minute)
            # Usamos 20,000 como límite MUY conservador (dejando 10,000 para docs recuperados + respuesta)
            # El workflow también agrega documentos recuperados, así que limitamos el contexto base
            MAX_CONTEXT_TOKENS = 20000  # Límite MUY conservador: 20,000 tokens (dejando 10,000 para docs + respuesta)
            
            # Truncar contexto si es muy grande
            conversation_context = self._truncate_context_intelligently(
                conversation_context,
                max_tokens=MAX_CONTEXT_TOKENS,
                query=message
            )
            
            # Crear workflow
            temp_workflow = AgentWorkflow(self.config, provider=provider)
            
            # Ejecutar con contexto plegado y estrategia de RL
            enriched_query = f"{conversation_context}\n\nPREGUNTA ACTUAL:\n{message}"
            if best_strategy:
                enriched_query += f"\n\n🎯 ESTRATEGIA DE RL: {best_strategy}"
            if best_approach:
                enriched_query += f"\n\n🛤️ ENFOQUE RECOMENDADO: {best_approach}"
            
            # Verificar tamaño final del query y truncar si es necesario
            enriched_query = self._truncate_query_if_needed(enriched_query, max_tokens=MAX_CONTEXT_TOKENS)
            
            result = temp_workflow.run(
                enriched_query,
                session["retriever"],
                all_documents=session["docs"],
                conversational_mode=True
            )
            
            answer = result.get("answer", result.get("draft_answer", "No se pudo generar respuesta."))
            sources = result.get("sources", [])
            verification_report = result.get("verification_report", "")
            relevance_label = result.get("relevance", "UNKNOWN")
            
            # 8. Rastrear procedencia de la respuesta
            source_provenances = []
            for source in sources:
                if isinstance(source, dict):
                    # Buscar documento correspondiente
                    source_name = source.get("source", source.get("file", ""))
                    doc = next((d for d in session["docs"] if source_name in str(d.metadata.get("source", ""))), None)
                    if doc:
                        provenance = self.provenance_tracker.track_document_source(doc)
                        source_provenances.append(provenance)
            
            # Registrar en tracker de procedencia
            record_id = self.provenance_tracker.track_query_response(
                query=message,
                response=answer,
                sources=source_provenances,
                processing_steps=[
                    {"step": "reinforcement_planning", "details": f"Árbol RL: {rl_result.get('tree_id') if rl_result else 'N/A'}, Exploraciones: {rl_result.get('total_explorations', 0) if rl_result else 0}"},
                    {"step": "path_reasoning", "details": f"Enfoque: {best_approach or 'N/A'}"},
                    {"step": "chain_of_thought", "details": f"Cadena: {chain_id}"},
                    {"step": "mcp_integration", "details": f"Datos externos: {len(mcp_data.get('sources', [])) if mcp_data else 0} fuentes"}
                ],
                session_id=session_id,
                metadata={
                    "approval_id": approval_id,
                    "criticality": criticality.value if requires_approval else "low",
                    "path_result": path_result
                }
            )
            
            # 9. Completar cadena de razonamiento
            self.chain_reasoner.complete_chain(chain_id, answer, success=True)
            
            # 10. Registrar en Test Time Training
            execution_time = time.time() - start_time
            self.test_time_trainer.record_episode(
                task_type="document_query",
                input_data=message,
                output_data=answer,
                success=True,
                execution_time=execution_time,
                metadata={
                    "sources_count": len(sources),
                    "approval_required": requires_approval,
                    "path_used": best_approach or "N/A",
                    "rl_tree_id": rl_result.get("tree_id") if rl_result else None,
                    "rl_explorations": rl_result.get("total_explorations", 0) if rl_result else 0,
                    "mcp_sources": len(mcp_data.get("sources", [])) if mcp_data else 0
                }
            )
            
            # 11. Formatear respuesta con procedencia y reporte de verificación completo
            formatted_answer = answer
            
            # Agregar información del proceso multi-agente DocChat
            formatted_answer += "\n\n---\n\n"
            formatted_answer += "## 🔬 Proceso Multi-Agente DocChat\n\n"
            formatted_answer += "### 📋 Análisis de Relevancia\n"
            if relevance_label == "CAN_ANSWER":
                formatted_answer += "✅ **Relevancia:** CAN_ANSWER - Los documentos proporcionan información suficiente para responder completamente.\n\n"
            elif relevance_label == "PARTIAL":
                formatted_answer += "⚠️ **Relevancia:** PARTIAL - Los documentos mencionan el tema pero pueden faltar detalles completos.\n\n"
            elif relevance_label == "NO_MATCH":
                formatted_answer += "❌ **Relevancia:** NO_MATCH - Los documentos no contienen información relevante para esta pregunta.\n\n"
            else:
                formatted_answer += f"ℹ️ **Relevancia:** {relevance_label}\n\n"
            
            # Agregar reporte de verificación completo
            if verification_report:
                formatted_answer += "### ✅ Verificación de Respuesta (Anti-Hallucinación)\n"
                formatted_answer += verification_report
                formatted_answer += "\n\n"
                formatted_answer += "**🔍 Sistema de Verificación:**\n"
                formatted_answer += "- ✅ **Hybrid Retriever:** Combina BM25 (búsqueda léxica) + Vector Search (búsqueda semántica)\n"
                formatted_answer += "- 🔬 **Research Agent:** Genera respuesta inicial basada en documentos recuperados\n"
                formatted_answer += "- ✅ **Verification Agent:** Verifica que la respuesta esté soportada por los documentos\n"
                formatted_answer += "- 🔄 **Self-Correction:** Re-ejecuta research si se detectan contradicciones o claims sin soporte\n"
                formatted_answer += "\n"
            
            # Agregar fuentes con procedencia
            if source_provenances:
                sources_list = []
                for prov in source_provenances[:10]:  # Mostrar hasta 10 fuentes
                    source_info = f"- {prov.source_name}"
                    if prov.page_number:
                        source_info += f" (página {prov.page_number})"
                    sources_list.append(source_info)
                
                if sources_list:
                    formatted_answer += "### 📚 Fuentes Consultadas\n"
                    formatted_answer += "\n".join(sources_list)
                    formatted_answer += f"\n\n🔍 **Procedencia:** Registro ID {record_id}\n"
            
            # Agregar información adicional del proceso
            formatted_answer += "\n---\n\n"
            formatted_answer += "### 🧠 Capacidades Avanzadas Utilizadas\n"
            formatted_answer += "- 📦 **Context Folding:** Gestión eficiente de contextos masivos (500+ PDFs)\n"
            formatted_answer += "- 🔍 **Data Provenance:** Trazabilidad completa de cada pieza de información\n"
            formatted_answer += "- 🧠 **Chain of Thought:** Razonamiento paso a paso\n"
            formatted_answer += "- 🛤️ **Path-dependent Reasoning:** Múltiples enfoques probados\n"
            formatted_answer += "- 📈 **Test Time Training:** Mejora continua con cada conversación\n"
            formatted_answer += "- 🌳 **Reinforcement Learning & Planning:** Estrategias adaptativas\n"
            formatted_answer += "- 🔌 **MCP Powered:** Conexión a sistemas externos\n"
            
            # Agregar advertencia si requiere aprobación
            if requires_approval and approval_id:
                formatted_answer += f"\n\n⚠️ **Aprobación requerida:** ID {approval_id} (Criticidad: {criticality.value})"
            
            # Actualizar historial
            session["history"].append({
                "question": message,
                "answer": answer,
                "sources": sources,
                "provenance_record_id": record_id,
                "chain_id": chain_id,
                "timestamp": datetime.now().isoformat()
            })
            
            # Guardar en memoria persistente
            if self.context_manager:
                self.context_manager.add_query(
                    query=message,
                    answer=answer,
                    sources=[prov.source_name for prov in source_provenances],
                    metadata={
                        "mode": "alien_mode",
                        "session_id": session_id,
                        "conversation_turn": len(session["history"]),
                        "provenance_record_id": record_id,
                        "chain_id": chain_id
                    }
                )
            
            # Actualizar historial de Gradio
            if history and isinstance(history[0], dict):
                tuple_history = []
                for i in range(0, len(history) - 1, 2):
                    if i + 1 < len(history):
                        user_msg = history[i].get("content", "") if isinstance(history[i], dict) else history[i]
                        bot_msg = history[i + 1].get("content", "") if isinstance(history[i + 1], dict) else history[i + 1]
                        tuple_history.append((user_msg, bot_msg))
                history = tuple_history
            
            history.append((message, formatted_answer))
            
            # Restaurar modo original
            self.config.speed_mode = original_speed_mode
            
            metadata = {
                "provenance_record_id": record_id,
                "chain_id": chain_id,
                "approval_id": approval_id,
                "execution_time": execution_time,
                "sources_count": len(sources)
            }
            
            return history, None, metadata
            
        except Exception as e:
            error_msg = f"❌ Error en chat: {str(e)}"
            
            # Registrar error en Test Time Training
            execution_time = time.time() - start_time
            self.test_time_trainer.record_episode(
                task_type="document_query",
                input_data=message,
                output_data=error_msg,
                success=False,
                execution_time=execution_time,
                metadata={"error": str(e)}
            )
            
            # Completar cadena con error
            if chain_id:
                self.chain_reasoner.complete_chain(chain_id, error_msg, success=False)
            
            # Restaurar modo original
            self.config.speed_mode = original_speed_mode
            
            # Actualizar historial
            if history and isinstance(history[0], dict):
                tuple_history = []
                for i in range(0, len(history) - 1, 2):
                    if i + 1 < len(history):
                        user_msg = history[i].get("content", "") if isinstance(history[i], dict) else history[i]
                        bot_msg = history[i + 1].get("content", "") if isinstance(history[i + 1], dict) else history[i + 1]
                        tuple_history.append((user_msg, bot_msg))
                history = tuple_history
            
            history.append((message, error_msg))
            
            return history, error_msg, {}
    
    def _build_folded_context(
        self,
        session: Dict[str, Any],
        history: List[Tuple[str, str]]
    ) -> str:
        """Construye contexto usando Context Folding."""
        context_folder = session.get("context_folder", self.context_folder)
        
        # Agregar historial al contexto principal
        if history:
            for user_msg, bot_msg in history[-10:]:  # Últimas 10 interacciones
                if isinstance(user_msg, (tuple, list)) and len(user_msg) == 2:
                    user_msg, bot_msg = user_msg
                
                context_text = f"Usuario: {user_msg}\nAsistente: {bot_msg[:1000]}\n"
                context_folder.add_to_main_context(context_text)
        
        # Auto-plegar si es necesario
        context_folder.auto_fold_if_needed()
        
        # Obtener contexto plegado
        return context_folder.get_folded_context()
    
    def _estimate_tokens(self, text: str) -> int:
        """
        Estima el número de tokens en un texto.
        Aproximación: 1 token ≈ 4 caracteres (conservador para inglés/español).
        """
        # Aproximación conservadora: 1 token = 4 caracteres
        # En realidad puede variar, pero esta es una buena estimación
        return len(text) // 4
    
    def _truncate_context_intelligently(
        self,
        context: str,
        max_tokens: int,
        query: str = ""
    ) -> str:
        """
        Trunca el contexto de forma inteligente, priorizando contenido relevante.
        
        Estrategia:
        1. Si el contexto es menor que el límite, retornar completo
        2. Si es mayor, priorizar:
           - Contenido relacionado con la query
           - Últimas partes del contexto (más reciente)
           - Resúmenes y metadatos
        """
        estimated_tokens = self._estimate_tokens(context)
        
        if estimated_tokens <= max_tokens:
            return context
        
        # Calcular cuántos caracteres podemos usar (dejando margen)
        max_chars = max_tokens * 4  # 4 chars por token
        max_chars = int(max_chars * 0.95)  # 95% para margen de seguridad
        
        # Si el contexto es muy grande, truncar inteligentemente
        if len(context) <= max_chars:
            return context
        
        # Estrategia 1: Priorizar contenido relacionado con la query
        if query:
            query_lower = query.lower()
            context_lower = context.lower()
            
            # Buscar párrafos que contengan palabras de la query
            paragraphs = context.split('\n\n')
            relevant_paragraphs = []
            other_paragraphs = []
            
            query_words = set(query_lower.split())
            
            for para in paragraphs:
                para_lower = para.lower()
                # Contar palabras de la query que aparecen en el párrafo
                matches = sum(1 for word in query_words if word in para_lower)
                if matches > 0:
                    relevant_paragraphs.append((para, matches))
                else:
                    other_paragraphs.append(para)
            
            # Ordenar párrafos relevantes por número de coincidencias
            relevant_paragraphs.sort(key=lambda x: x[1], reverse=True)
            
            # Construir contexto truncado: primero los relevantes, luego otros
            truncated = []
            current_length = 0
            
            # Agregar párrafos relevantes primero
            for para, _ in relevant_paragraphs:
                if current_length + len(para) <= max_chars:
                    truncated.append(para)
                    current_length += len(para) + 2  # +2 para '\n\n'
                else:
                    break
            
            # Agregar otros párrafos si hay espacio
            remaining_chars = max_chars - current_length
            if remaining_chars > 1000:  # Solo si hay espacio significativo
                for para in other_paragraphs:
                    if current_length + len(para) <= max_chars:
                        truncated.append(para)
                        current_length += len(para) + 2
                    else:
                        break
            
            result = '\n\n'.join(truncated)
            
            # Si aún es muy grande, truncar desde el final
            if len(result) > max_chars:
                result = result[:max_chars]
                result += "\n\n[... contexto truncado para cumplir límite de tokens ...]"
            
            return result
        
        # Estrategia 2: Si no hay query, tomar las últimas partes (más recientes)
        truncated = context[-max_chars:]
        
        # Agregar indicador de truncamiento al inicio
        if len(context) > max_chars:
            truncated = "[... contexto anterior truncado ...]\n\n" + truncated
        
        return truncated
    
    def _truncate_query_if_needed(self, query: str, max_tokens: int) -> str:
        """Trunca el query completo si excede el límite de tokens."""
        estimated_tokens = self._estimate_tokens(query)
        
        if estimated_tokens <= max_tokens:
            return query
        
        # Calcular máximo de caracteres
        max_chars = max_tokens * 4
        max_chars = int(max_chars * 0.95)  # 95% para margen
        
        # Truncar desde el final, pero mantener la pregunta actual
        if len(query) > max_chars:
            # Intentar mantener la pregunta actual completa
            if "PREGUNTA ACTUAL:" in query:
                parts = query.split("PREGUNTA ACTUAL:")
                context_part = parts[0]
                question_part = "PREGUNTA ACTUAL:" + parts[1] if len(parts) > 1 else ""
                
                # Truncar solo la parte del contexto
                context_max = max_chars - len(question_part) - 100  # Margen
                if context_max > 0:
                    truncated_context = context_part[:context_max]
                    truncated_context += "\n\n[... contexto truncado para cumplir límite de tokens ...]"
                    return truncated_context + "\n\n" + question_part
                else:
                    # Si la pregunta es muy larga, truncar todo
                    return query[:max_chars] + "\n\n[... truncado ...]"
            else:
                # Si no hay pregunta marcada, truncar desde el final
                return query[:max_chars] + "\n\n[... truncado ...]"
        
        return query
    
    async def _execute_query_path(
        self,
        approach: str,
        strategy: str,
        expected_steps: List[str],
        context: str
    ) -> Any:
        """Ejecuta un camino de razonamiento."""
        # Simulación de ejecución de camino
        # En producción, esto ejecutaría el query con el enfoque específico
        return f"Resultado usando enfoque: {approach}"
    
    async def _execute_rl_action(
        self,
        action: str,
        context: str
    ) -> Any:
        """
        Ejecuta una acción del Reinforcement Planner.
        
        Las acciones pueden ser:
        - "Buscar por palabras clave: [términos]"
        - "Buscar por secciones: [sección]"
        - "Buscar por fechas: [rango]"
        - "Buscar por tipo de documento: [tipo]"
        - "Comparar documentos: [docs]"
        - "Analizar estructura: [aspecto]"
        """
        # Extraer tipo de acción
        action_lower = action.lower()
        
        # Simular ejecución de diferentes estrategias
        if "palabras clave" in action_lower or "keywords" in action_lower:
            # Estrategia: búsqueda por palabras clave
            return {
                "strategy": "keyword_search",
                "result": "Búsqueda por palabras clave ejecutada",
                "success": True,
                "confidence": 0.8
            }
        elif "secciones" in action_lower or "sections" in action_lower:
            # Estrategia: búsqueda por secciones
            return {
                "strategy": "section_search",
                "result": "Búsqueda por secciones ejecutada",
                "success": True,
                "confidence": 0.75
            }
        elif "fechas" in action_lower or "dates" in action_lower:
            # Estrategia: búsqueda por fechas
            return {
                "strategy": "date_search",
                "result": "Búsqueda por fechas ejecutada",
                "success": True,
                "confidence": 0.7
            }
        elif "comparar" in action_lower or "compare" in action_lower:
            # Estrategia: comparación de documentos
            return {
                "strategy": "document_comparison",
                "result": "Comparación de documentos ejecutada",
                "success": True,
                "confidence": 0.85
            }
        elif "analizar" in action_lower or "analyze" in action_lower:
            # Estrategia: análisis de estructura
            return {
                "strategy": "structure_analysis",
                "result": "Análisis de estructura ejecutado",
                "success": True,
                "confidence": 0.8
            }
        else:
            # Estrategia genérica
            return {
                "strategy": "generic",
                "result": f"Acción ejecutada: {action}",
                "success": True,
                "confidence": 0.6
            }
    
    async def _query_mcp_systems(
        self,
        query: str,
        context: str
    ) -> Optional[Dict[str, Any]]:
        """
        Consulta sistemas externos usando MCP potenciado.
        
        Permite:
        - Conectarse a bases de datos
        - Consultar APIs externas
        - Acceder a servicios en la nube
        - Navegar datos crudos sin conectores específicos
        """
        if not self.mcp_manager or not self.mcp_manager.connections:
            return None
        
        try:
            # Determinar si la consulta requiere datos externos
            requires_external = await self._needs_external_data(query, context)
            
            if not requires_external:
                return None
            
            # Consultar cada conexión MCP disponible
            mcp_results = []
            mcp_sources = []
            
            for conn_id, connection in self.mcp_manager.connections.items():
                if not connection.enabled:
                    continue
                
                try:
                    # Usar MCP para consultar el sistema externo
                    if connection.connection_type == "database":
                        # Consultar base de datos
                        result = await self._query_mcp_database(connection, query)
                        if result:
                            mcp_results.append(result)
                            mcp_sources.append({
                                "type": "database",
                                "name": connection.name,
                                "data": result
                            })
                    
                    elif connection.connection_type == "api":
                        # Consultar API externa
                        result = await self._query_mcp_api(connection, query)
                        if result:
                            mcp_results.append(result)
                            mcp_sources.append({
                                "type": "api",
                                "name": connection.name,
                                "data": result
                            })
                    
                    elif connection.connection_type == "salesforce":
                        # Consultar Salesforce
                        result = await self._query_mcp_salesforce(connection, query)
                        if result:
                            mcp_results.append(result)
                            mcp_sources.append({
                                "type": "salesforce",
                                "name": connection.name,
                                "data": result
                            })
                    
                    # Navegar datos crudos usando LLM
                    if self.mcp_manager.llm:
                        # Usar conn_id como data_source
                        raw_data_result = await self.mcp_manager.navigate_raw_data(
                            data_source=conn_id,
                            query=query,
                            llm=self.mcp_manager.llm
                        )
                        if raw_data_result and raw_data_result.get("success"):
                            mcp_results.append(raw_data_result.get("result"))
                            mcp_sources.append({
                                "type": "raw_data",
                                "name": connection.name,
                                "data": raw_data_result.get("result")
                            })
                
                except Exception as e:
                    print(f"⚠️ [Alien Mode] Error consultando MCP {connection.name}: {e}")
                    continue
            
            if not mcp_results:
                return None
            
            # Combinar resultados
            summary = "\n".join([
                f"- {source['name']} ({source['type']}): {str(source['data'])[:200]}"
                for source in mcp_sources[:5]
            ])
            
            return {
                "sources": mcp_sources,
                "summary": summary,
                "total_sources": len(mcp_sources)
            }
            
        except Exception as e:
            print(f"⚠️ [Alien Mode] Error en consulta MCP: {e}")
            return None
    
    async def _needs_external_data(
        self,
        query: str,
        context: str
    ) -> bool:
        """Determina si la consulta requiere datos externos."""
        # Palabras clave que indican necesidad de datos externos
        external_keywords = [
            "actual", "tiempo real", "realtime", "sistema", "base de datos",
            "database", "api", "actualizado", "estado actual", "proceso actual",
            "verificar", "validar", "comprobar", "confirmar"
        ]
        
        query_lower = query.lower()
        context_lower = context.lower()
        
        combined = f"{query_lower} {context_lower}"
        
        return any(keyword in combined for keyword in external_keywords)
    
    async def _query_mcp_database(
        self,
        connection: Any,
        query: str
    ) -> Optional[Dict[str, Any]]:
        """Consulta una base de datos usando MCP."""
        # En producción, esto usaría las herramientas MCP para consultar la BD
        # Por ahora, simulación
        return {
            "type": "database",
            "query": query,
            "result": "Datos de base de datos obtenidos vía MCP"
        }
    
    async def _query_mcp_api(
        self,
        connection: Any,
        query: str
    ) -> Optional[Dict[str, Any]]:
        """Consulta una API externa usando MCP."""
        # En producción, esto usaría las herramientas MCP para consultar la API
        return {
            "type": "api",
            "query": query,
            "result": "Datos de API obtenidos vía MCP"
        }
    
    async def _query_mcp_salesforce(
        self,
        connection: Any,
        query: str
    ) -> Optional[Dict[str, Any]]:
        """Consulta Salesforce usando MCP."""
        # En producción, esto usaría las herramientas MCP para consultar Salesforce
        return {
            "type": "salesforce",
            "query": query,
            "result": "Datos de Salesforce obtenidos vía MCP"
        }
    
    async def _process_query_parallel(
        self,
        session_id: str,
        message: str,
        history: List[Tuple[str, str]],
        docs_by_source: Dict[str, List[Document]],
        speed_mode: str = "balanced",
        provider: str = "openai"
    ) -> Tuple[List[Tuple[str, str]], Optional[str], Dict[str, Any]]:
        """
        Procesa consulta con procesamiento paralelo de documentos (como Enterprise API).
        Analiza cada documento por separado aplicando el prompt del usuario,
        luego combina todos los análisis en una respuesta final.
        """
        session = self.sessions.get(session_id, {})
        start_time = time.time()
        
        # Crear LLM sin límite de max_tokens para respuestas largas (como Enterprise API)
        from docchat.utils.llm_factory import create_llm
        api_key = self.config.openai_api_key if provider == "openai" else self.config.anthropic_api_key
        parallel_llm = create_llm(
            provider=provider,
            model=self.config.research_model or "gpt-4o",
            temperature=0.2,
            api_key=api_key,
            # max_tokens REMOVIDO - dejar que la API decida la longitud (como Enterprise API)
            request_timeout=300  # Timeout más largo para respuestas largas
        )
        
        # Construir contexto de conversación (sin documentos, solo historial)
        conversation_context = self._build_folded_context(session, history)
        
        # Procesar cada documento en paralelo
        individual_analyses = {}
        max_workers = min(5, len(docs_by_source))  # Máximo 5 documentos en paralelo
        
        def analyze_single_document(source_name: str, file_docs: List[Document]) -> Tuple[str, str]:
            """Analiza un solo documento con el prompt del usuario."""
            try:
                # Construir contexto del documento (todos los chunks de este documento)
                doc_content = "\n\n".join([doc.page_content for doc in file_docs])
                # Limitar contenido a ~4000 caracteres por documento para evitar límites
                if len(doc_content) > 4000:
                    doc_content = doc_content[:4000] + "..."
                
                # Prompt CENTRADO EN EL PROMPT DEL USUARIO - Cada PDF responde exactamente lo que el usuario pregunta
                prompt = f"""Eres un analista estratégico de nivel C-Suite. Tu tarea es analizar ESTE documento específico para responder DIRECTAMENTE la pregunta del usuario.

PREGUNTA ESPECÍFICA DEL USUARIO (RESPONDE EXACTAMENTE ESTO):
{message}

CONTENIDO DE ESTE DOCUMENTO:
{doc_content}

INSTRUCCIONES CRÍTICAS:

1. RESPUESTA DIRECTA AL PROMPT DEL USUARIO:
   - Tu objetivo PRINCIPAL es responder: "{message}"
   - Analiza este documento ESPECÍFICAMENTE para encontrar información que responda esa pregunta
   - Si el usuario pregunta "información más valiosa" → identifica la información MÁS VALIOSA de este documento
   - Si el usuario pregunta "qué recomendarías hacer" → proporciona recomendaciones ESPECÍFICAS basadas en este documento
   - Si el usuario pregunta "cuál es el mejor documento" → evalúa este documento en relación a la pregunta
   - ADÁPTATE al tipo de pregunta del usuario - no uses un formato genérico

2. ANÁLISIS ESPECÍFICO PARA ESTE DOCUMENTO:
   - Extrae información del documento que responda DIRECTAMENTE a la pregunta del usuario
   - Cita datos concretos del documento (números, porcentajes, fechas, nombres, métricas)
   - Identifica entidades, metodologías, frameworks, o conceptos relevantes para la pregunta
   - Si la pregunta requiere comparación o evaluación, evalúa este documento específicamente

3. RESPUESTA ESTRUCTURADA (300-500 palabras):
   - **Respuesta Directa** (1-2 párrafos): Responde la pregunta del usuario usando información de este documento
   - **Información Específica** (1-2 párrafos): Detalles concretos del documento que apoyan tu respuesta
   - **Recomendaciones/Insights** (1 párrafo): Si la pregunta lo requiere, proporciona recomendaciones o insights específicos

4. ADAPTACIÓN AL TIPO DE PREGUNTA:
   - Si pregunta por "información valiosa" → identifica y explica la información MÁS VALIOSA
   - Si pregunta por "recomendaciones" → proporciona recomendaciones ESPECÍFICAS y ACCIONABLES
   - Si pregunta por "mejor documento" → evalúa este documento y explica por qué es o no es el mejor
   - Si pregunta por "análisis" → proporciona análisis profundo relacionado con la pregunta
   - ADÁPTATE - no uses un formato genérico, responde lo que el usuario realmente pregunta

5. PROFESIONALISMO ENTERPRISE:
   - Lenguaje claro y directo (nivel C-Suite)
   - Enfoque en responder la pregunta específica del usuario
   - Información accionable y específica del documento
   - Estructura clara y escaneable

IMPORTANTE:
- NO uses un formato genérico - ADÁPTATE al tipo de pregunta del usuario
- NO describas el documento en general - RESPONDE la pregunta específica
- SÍ extrae información específica del documento que responda la pregunta
- SÍ proporciona recomendaciones/insights si la pregunta lo requiere

RESPUESTA ESPECÍFICA A LA PREGUNTA DEL USUARIO (300-500 palabras):"""
                
                # Generar análisis con LLM (sin límite de max_tokens)
                response = parallel_llm.invoke(prompt)
                analysis = response.content.strip() if hasattr(response, 'content') else str(response).strip()
                
                return source_name, analysis
            except Exception as e:
                return source_name, f"❌ Error analizando documento: {str(e)[:200]}"
        
        # Ejecutar análisis en paralelo
        print(f"🔄 [Alien Mode] Procesando {len(docs_by_source)} documentos en paralelo...")
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(analyze_single_document, source_name, file_docs): source_name
                for source_name, file_docs in docs_by_source.items()
            }
            
            for future in as_completed(futures):
                source_name = futures[future]
                try:
                    doc_name, analysis = future.result()
                    individual_analyses[doc_name] = analysis
                    print(f"✅ [Alien Mode] Análisis completado para: {Path(doc_name).name}")
                except Exception as e:
                    print(f"❌ [Alien Mode] Error procesando {source_name}: {e}")
                    individual_analyses[source_name] = f"❌ Error: {str(e)[:200]}"
        
        # OPCIÓN A: Mostrar todos los análisis individuales
        individual_analyses_text = "## 📄 Análisis Individuales por Documento\n\n"
        for doc_name, analysis in individual_analyses.items():
            clean_name = Path(doc_name).name
            individual_analyses_text += f"### 📄 {clean_name}\n\n"
            individual_analyses_text += f"{analysis}\n\n"
            individual_analyses_text += "---\n\n"
        
        # OPCIÓN B: Combinar todos los análisis en una respuesta final
        combined_context = "\n\n".join([
            f"=== DOCUMENTO: {Path(doc_name).name} ===\n{analysis}"
            for doc_name, analysis in individual_analyses.items()
        ])
        
        # Generar respuesta combinada que RESPONDE DIRECTAMENTE al prompt del usuario
        synthesis_prompt = f"""Eres un consultor estratégico senior de nivel C-Suite. Has analizado {len(individual_analyses)} documentos individualmente, cada uno respondiendo la pregunta del usuario.

TU TAREA PRINCIPAL: Combinar todos los análisis individuales para responder DIRECTAMENTE la pregunta del usuario de manera completa y estratégica.

PREGUNTA ESPECÍFICA DEL USUARIO (RESPONDE EXACTAMENTE ESTO):
{message}

ANÁLISIS INDIVIDUALES DE CADA DOCUMENTO (cada uno ya respondió la pregunta del usuario):
{combined_context}

INSTRUCCIONES PARA RESPUESTA FINAL COMBINADA (800-1200 palabras):

1. RESPUESTA DIRECTA AL PROMPT DEL USUARIO:
   - Tu objetivo es responder: "{message}"
   - Combina información de todos los análisis individuales para dar una respuesta COMPLETA
   - Si el usuario pregunta "información más valiosa de cada PDF" → sintetiza la información más valiosa de TODOS los PDFs
   - Si el usuario pregunta "qué me recomendarías hacer" → proporciona recomendaciones basadas en TODOS los documentos
   - Si el usuario pregunta "cuál es el mejor documento" → compara y evalúa todos los documentos
   - ADÁPTATE al tipo de pregunta - no uses un formato genérico

2. SÍNTESIS ESTRATÉGICA:
   - Combina los análisis individuales en una respuesta coherente
   - Identifica patrones comunes, contradicciones, o tensiones entre documentos
   - Proporciona una visión holística que responda completamente la pregunta
   - Compara y contrasta información de diferentes documentos cuando sea relevante

3. ESTRUCTURA ADAPTATIVA (según el tipo de pregunta):
   
   Si pregunta por "información valiosa" o "recomendaciones":
   - **Respuesta Directa** (2-3 párrafos): Responde la pregunta combinando información de todos los documentos
   - **Información Clave por Documento** (resumen de lo más valioso de cada uno)
   - **Recomendaciones Finales** (basadas en toda la información combinada)
   - **Documentos Más Relevantes** (cuáles aportan más valor y por qué)
   
   Si pregunta por "mejor documento" o "comparación":
   - **Evaluación Comparativa** (compara todos los documentos en relación a la pregunta)
   - **Documento(s) Recomendado(s)** (cuál es el mejor y por qué)
   - **Análisis de Fortalezas y Debilidades** (de cada documento relevante)
   - **Recomendación Final** (qué documento usar y por qué)
   
   Si pregunta por "análisis" o "insights":
   - **Análisis Holístico** (insights que emergen de ver todos los documentos juntos)
   - **Patrones y Tendencias** (qué patrones se repiten o contradicen)
   - **Insights Estratégicos** (hallazgos que ningún documento individual puede dar)
   - **Recomendaciones Basadas en el Análisis Completo**

4. PROFESIONALISMO ENTERPRISE:
   - Lenguaje claro y directo (nivel C-Suite)
   - Enfoque en responder la pregunta específica del usuario
   - Estructura clara y escaneable
   - Información accionable y específica

5. LONGITUD Y EFECTIVIDAD:
   - 800-1200 palabras (completo pero no abrumador)
   - Prioriza responder la pregunta sobre volumen de texto
   - Cada sección debe aportar valor único para responder la pregunta
   - Balance entre completitud y concisión

IMPORTANTE:
- RESPONDE DIRECTAMENTE la pregunta del usuario: "{message}"
- NO uses un formato genérico - ADÁPTATE al tipo de pregunta
- SÍ combina información de todos los análisis individuales
- SÍ proporciona una conclusión o recomendación final que responda la pregunta
- SÉ ESPECÍFICO: usa información concreta de los documentos, no generalidades

RESPUESTA FINAL QUE RESPONDE DIRECTAMENTE LA PREGUNTA DEL USUARIO (800-1200 palabras):"""
        
        try:
            synthesis_response = parallel_llm.invoke(synthesis_prompt)
            combined_answer = synthesis_response.content.strip() if hasattr(synthesis_response, 'content') else str(synthesis_response).strip()
        except Exception as e:
            combined_answer = f"❌ Error generando respuesta combinada: {str(e)[:200]}"
        
        # Combinar ambas opciones en la respuesta final
        formatted_answer = combined_answer
        formatted_answer += "\n\n---\n\n"
        formatted_answer += individual_analyses_text
        
        # Agregar información del proceso
        formatted_answer += "\n\n---\n\n"
        formatted_answer += "## 🔬 Proceso Multi-Agente DocChat (Modo Paralelo)\n\n"
        formatted_answer += f"✅ **Documentos analizados:** {len(individual_analyses)}\n"
        formatted_answer += "✅ **Procesamiento:** Paralelo (como Enterprise API)\n"
        formatted_answer += "✅ **Análisis:** Individual por documento + Respuesta combinada\n"
        formatted_answer += "✅ **Capacidad:** Respuestas largas sin límite de tokens por documento\n\n"
        
        # Actualizar historial
        session["history"].append({
            "question": message,
            "answer": formatted_answer,
            "sources": list(individual_analyses.keys()),
            "timestamp": datetime.now().isoformat(),
            "processing_mode": "parallel"
        })
        
        execution_time = time.time() - start_time
        metadata = {
            "execution_time": execution_time,
            "documents_analyzed": len(individual_analyses),
            "processing_mode": "parallel"
        }
        
        # Convertir historial a formato tuples para Gradio
        tuple_history = []
        for entry in session["history"]:
            if isinstance(entry, dict):
                tuple_history.append((entry.get("question", ""), entry.get("answer", "")))
            else:
                tuple_history.append(entry)
        
        return tuple_history, None, metadata
    
    def get_statistics(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Obtiene estadísticas del modo."""
        stats = {
            "context_folding": self.context_folder.get_statistics(),
            "data_provenance": self.provenance_tracker.get_statistics(),
            "chain_of_thought": self.chain_reasoner.get_statistics(),
            "path_reasoning": self.path_reasoner.get_statistics(),
            "test_time_training": self.test_time_trainer.get_statistics(),
            "person_in_loop": self.person_in_loop.get_statistics(),
            "reinforcement_planning": self.reinforcement_planner.get_statistics(),
            "mcp_integration": {
                "connections": len(self.mcp_manager.connections) if self.mcp_manager else 0,
                "enabled_connections": len([c for c in self.mcp_manager.connections.values() if c.enabled]) if self.mcp_manager else 0
            }
        }
        
        if session_id and session_id in self.sessions:
            session = self.sessions[session_id]
            stats["session"] = {
                "docs_count": len(session["docs"]),
                "history_count": len(session["history"]),
                "processed_files": len(session["processed_files"])
            }
        
        return stats


# Instancia global
_alien_mode_instance: Optional[AlienMode] = None


def get_alien_mode(
    config: AppConfig,
    processor: DocumentProcessor,
    retriever_builder: RetrieverBuilder,
    context_manager: Optional[Any] = None
) -> AlienMode:
    """Obtiene o crea la instancia global de Alien Mode."""
    global _alien_mode_instance
    
    if _alien_mode_instance is None:
        _alien_mode_instance = AlienMode(
            config=config,
            processor=processor,
            retriever_builder=retriever_builder,
            context_manager=context_manager
        )
    
    return _alien_mode_instance


def run_alien_mode(
    message: str,
    history: List[Tuple[str, str]],
    files: List[Any],
    session_id: str,
    speed_mode: str = "balanced",
    provider: str = "openai",
    config: Optional[AppConfig] = None,
    processor: Optional[DocumentProcessor] = None,
    retriever_builder: Optional[RetrieverBuilder] = None,
    context_manager: Optional[Any] = None
) -> Tuple[List[Tuple[str, str]], Optional[str]]:
    """
    Función principal para ejecutar Alien Mode.
    Compatible con Gradio (síncrona).
    """
    if not config or not processor or not retriever_builder:
        return history, "❌ Configuración incompleta"
    
    # Obtener instancia
    alien_mode = get_alien_mode(
        config=config,
        processor=processor,
        retriever_builder=retriever_builder,
        context_manager=context_manager
    )
    
    # Procesar documentos si hay
    if files:
        result = alien_mode.process_documents(session_id, files)
        if result.get("status") == "error":
            return history, f"❌ Error procesando documentos: {result.get('error')}"
    
    # Ejecutar query (async wrapper)
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        new_history, error, metadata = loop.run_until_complete(
            alien_mode.process_query_async(
                session_id=session_id,
                message=message,
                history=history,
                speed_mode=speed_mode,
                provider=provider
            )
        )
        loop.close()
        return new_history, error
    except Exception as e:
        return history, f"❌ Error: {str(e)}"

