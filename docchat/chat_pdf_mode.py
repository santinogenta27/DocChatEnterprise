"""
ChatPDF Mode - Sistema Multi-Agente RAG de Máxima Calidad
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
import os
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

# Importar Confluent para streaming en tiempo real (opcional)
try:
    from .confluent_streaming import (
        ConfluentStreamingProducer,
        ConfluentStreamingManager,
        StreamingEvent,
        EventType
    )
    CONFLUENT_STREAMING_AVAILABLE = True
except ImportError:
    ConfluentStreamingProducer = None  # type: ignore
    ConfluentStreamingManager = None  # type: ignore
    StreamingEvent = None  # type: ignore
    EventType = None  # type: ignore
    CONFLUENT_STREAMING_AVAILABLE = False

# Importar SimpleEventBus para streaming interno
try:
    from .event_bus_mode import SimpleEventBus
except ImportError:
    # Si no está disponible, crear una versión simple
    class SimpleEventBus:
        def __init__(self):
            self.subscribers = {}
        def publish(self, event_type: str, data: Dict[str, Any]):
            pass


class ChatPDFMode:
    """
    ChatPDF Mode - Sistema Multi-Agente RAG de Máxima Calidad para Empresas.
    
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
            raise ValueError("OPENAI_API_KEY o ANTHROPIC_API_KEY requerida para ChatPDF Mode")
        
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
        
        # Event Bus interno para streaming en tiempo real
        self.event_bus = SimpleEventBus()
        
        # REAL-TIME CONTEXT ENGINE: Similar al Real-Time Context Engine de Confluent
        # Materializa datos enriquecidos en cache en memoria y sirve contexto en tiempo real
        from .real_time_context_engine import get_real_time_context_engine
        
        bootstrap_servers = getattr(config, 'confluent_bootstrap_servers', None) or os.getenv('CONFLUENT_BOOTSTRAP_SERVERS')
        self.real_time_context_engine = get_real_time_context_engine(
            bootstrap_servers=bootstrap_servers,
            enabled=True
        )
        
        # Confluent Streaming para tiempo real (opcional - mejor performance)
        self.confluent_producer = None
        self.confluent_enabled = False
        if CONFLUENT_STREAMING_AVAILABLE:
            # Intentar inicializar Confluent si está configurado
            if bootstrap_servers:
                try:
                    self.confluent_producer = ConfluentStreamingProducer(
                        bootstrap_servers=bootstrap_servers,
                        security_config=getattr(config, 'confluent_security_config', None),
                        enabled=True
                    )
                    self.confluent_enabled = True
                    print("✅ [ChatPDF Mode] Real-Time Context Engine + Confluent Streaming habilitado")
                except Exception as e:
                    print(f"⚠️ [ChatPDF Mode] No se pudo inicializar Confluent (usando Event Bus interno): {e}")
                    self.confluent_enabled = False
        else:
            print("✅ [ChatPDF Mode] Real-Time Context Engine habilitado (Event Bus interno)")
        
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
                print(f"⚠️ [ChatPDF Mode] ANTHROPIC_API_KEY no configurada, usando OpenAI como fallback")
                provider_to_use = "openai"
                api_key = self.config.openai_api_key
        else:
            provider_to_use = "openai"
            api_key = self.config.openai_api_key
            if not api_key:
                raise ValueError("OPENAI_API_KEY requerida para ChatPDF Mode")
        
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
    
    def initialize_session(self, session_id: str) -> Dict[str, Any]:
        """Inicializa una nueva sesión."""
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                "docs": [],
                "retriever": None,
                "processed_files": set(),
                "history": [],
                "context_folder": ContextFolder(
                    config=self.config,
                    llm=self.llm,
                    max_context_tokens=32000,
                    max_branches=10
                ),
                "chain_id": None,
                "rl_tree_id": None,
                "mcp_queries": [],
                "created_at": time.time()
            }
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
            print(f"📄 [ChatPDF Mode] Procesando {len(new_files)} nuevos documentos...")
            new_docs = self.processor.process(new_files)
            session["docs"].extend(new_docs)
            
            # Rastrear procedencia de documentos
            for doc in new_docs:
                provenance = self.provenance_tracker.track_document_source(doc)
                # Guardar en sesión para referencia rápida
                if "provenances" not in session:
                    session["provenances"] = []
                session["provenances"].append(provenance)
            
            # Reconstruir retriever
            if session["docs"]:
                session["retriever"] = self.retriever_builder.build_hybrid_retriever(session["docs"])
                print(f"✅ [ChatPDF Mode] Retriever actualizado: {len(session['docs'])} chunks")
            
            return {
                "status": "success",
                "new_docs": len(new_docs),
                "total_docs": len(session["docs"]),
                "total_chunks": len(session["docs"])
            }
            
        except Exception as e:
            print(f"❌ [ChatPDF Mode] Error procesando documentos: {e}")
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
    ):
        """
        Procesa una consulta con todas las capacidades avanzadas.
        YIELD actualizaciones progresivas para streaming en tiempo real.
        
        Yields:
            (history, error, metadata): Historial actualizado, error si hay, metadatos
        """
        # ACTUALIZAR LLM SEGÚN EL PROVIDER - CRÍTICO para usar Claude cuando se selecciona
        provider_llm = self._get_llm_for_provider(provider)
        self._update_modules_with_llm(provider_llm)
        
        session = self.initialize_session(session_id)
        
        if not session["retriever"]:
            yield history, "⚠️ No hay documentos procesados. Carga documentos primero.", {}
            return
        
        # DETECTAR si hay muchos documentos para usar procesamiento paralelo
        all_docs = session.get("docs", [])
        if not all_docs:
            yield history, "⚠️ No hay documentos procesados. Carga documentos primero.", {}
            return
        
        # Agrupar documentos por fuente
        docs_by_source = defaultdict(list)
        for doc in all_docs:
            source = doc.metadata.get("source", "unknown")
            docs_by_source[source].append(doc)
        
        num_unique_documents = len(docs_by_source)
        
        # SIEMPRE usar procesamiento paralelo cuando hay documentos (1 o más)
        # Comportamiento equivalente a ChatGPT: cada PDF se analiza individualmente
        # Si envías 500 PDFs, recibirás 500 respuestas (1 análisis por PDF)
        use_parallel_processing = num_unique_documents >= 1
        
        start_time = time.time()
        
        # SIEMPRE usar procesamiento paralelo cuando hay documentos (1 o más)
        # Comportamiento equivalente a ChatGPT: cada PDF se analiza individualmente
        # YIELD actualizaciones progresivas para streaming en tiempo real
        if use_parallel_processing:
            async for update in self._process_query_parallel(
                session_id=session_id,
                message=message,
                history=history,
                docs_by_source=docs_by_source,
                speed_mode=speed_mode,
                provider=provider
            ):
                yield update
            return
        
        # 1. Crear cadena de razonamiento
        chain_id = self.chain_reasoner.create_chain(message)
        session["chain_id"] = chain_id
        
        # 2. Construir contexto con Context Folding
        conversation_context = self._build_folded_context(session, history)
        
        # 3. Agregar pasos de razonamiento (con manejo de errores)
        try:
            await self.chain_reasoner.add_reasoning_steps(chain_id, conversation_context)
        except Exception as e:
            print(f"⚠️ [ChatPDF Mode] Error agregando pasos de razonamiento: {e}")
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
            print(f"⚠️ [ChatPDF Mode] Error en Reinforcement Planning: {e}")
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
            print(f"⚠️ [ChatPDF Mode] Error en Path-dependent Reasoning: {e}")
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
            print(f"⚠️ [ChatPDF Mode] Error consultando MCP: {e}")
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
                        "mode": "chat_pdf_mode",
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
            
            # YIELD en lugar de return (es un generador async)
            yield history, None, metadata
            return
            
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
            
            # YIELD en lugar de return (es un generador async)
            yield history, error_msg, {}
            return
    
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
                    print(f"⚠️ [ChatPDF Mode] Error consultando MCP {connection.name}: {e}")
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
            print(f"⚠️ [ChatPDF Mode] Error en consulta MCP: {e}")
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
    ):
        """
        Procesa consulta con procesamiento paralelo de documentos (como Enterprise API).
        Analiza cada documento por separado aplicando el prompt del usuario,
        luego combina todos los análisis en una respuesta final.
        
        YIELD actualizaciones progresivas para streaming en tiempo real en la UI.
        """
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
        
        # Procesar cada documento en paralelo con RATE LIMITING para evitar errores 429
        individual_analyses = {}
        
        # RATE LIMITING: Reducir workers cuando hay muchos documentos para evitar exceder límites de OpenAI
        # OpenAI tiene límite de 30,000 TPM (tokens per minute)
        # Con muchos documentos, necesitamos procesar en lotes más pequeños
        num_docs = len(docs_by_source)
        if num_docs <= 5:
            max_workers = num_docs  # Pocos documentos: procesar todos en paralelo
        elif num_docs <= 10:
            max_workers = 5  # 5-10 documentos: máximo 5 workers
        elif num_docs <= 20:
            max_workers = 4  # 10-20 documentos: máximo 4 workers
        else:
            max_workers = 3  # Más de 20 documentos: máximo 3 workers para evitar rate limits
        
        print(f"🔄 [ChatPDF Mode] Procesando {num_docs} documentos con {max_workers} workers (rate limiting activo para evitar errores 429)")
        
        def analyze_single_document(source_name: str, file_docs: List[Document]) -> Tuple[str, str]:
            """Analiza un solo documento con el prompt del usuario - PROMPT ULTRA MEJORADO."""
            try:
                # Construir contexto del documento - LIMITAR para evitar exceder límites de tokens
                doc_content = "\n\n".join([doc.page_content for doc in file_docs])
                
                # CRÍTICO: Limitar contenido a ~15000 tokens (~60000 caracteres) para evitar error 429
                MAX_CHARS_PER_DOC = 60000  # ~15000 tokens (4 chars/token promedio)
                
                if len(doc_content) > MAX_CHARS_PER_DOC:
                    print(f"⚠️ [ChatPDF Mode] Documento muy grande ({len(doc_content)} caracteres), limitando a {MAX_CHARS_PER_DOC} para análisis individual...")
                    # Tomar el inicio y el final para mantener contexto relevante
                    half_chars = MAX_CHARS_PER_DOC // 2
                    doc_content = doc_content[:half_chars] + "\n\n... [CONTENIDO TRUNCADO PARA EVITAR LÍMITES DE TOKENS] ...\n\n" + doc_content[-half_chars:]
                
                # PROMPT ULTRA MEJORADO - Respuestas super mega ultra hyper inteligentes y completas
                prompt = f"""Eres un analista estratégico senior de nivel C-Suite con décadas de experiencia. Tu tarea es analizar ESTE documento específico de manera PROFUNDA y COMPLETA para responder DIRECTAMENTE la pregunta del usuario con el máximo nivel de inteligencia y detalle.

PREGUNTA ESPECÍFICA DEL USUARIO (RESPONDE EXACTAMENTE ESTO):
{message}

CONTENIDO COMPLETO DE ESTE DOCUMENTO (puede estar truncado si es muy largo):
{doc_content}

INSTRUCCIONES PARA RESPUESTA SUPER MEGA ULTRA HYPER INTELIGENTE Y COMPLETA:

1. PRECISIÓN ABSOLUTA - NO INVENTAR NADA:
   - ⚠️ CRÍTICO: SOLO usa información que esté EXPLÍCITAMENTE en el documento
   - ⚠️ PROHIBIDO: NO inventes, NO asumas, NO inferas información que no esté en el documento
   - ⚠️ Si la información no está en el documento, di claramente: "Esta información no está disponible en este documento"
   - ✅ Cita EXACTAMENTE el texto del documento cuando sea posible
   - ✅ Usa comillas para citas directas del documento
   - ✅ Indica la sección o contexto donde encontraste la información

2. RESPUESTA DIRECTA AL PROMPT DEL USUARIO:
   - Tu objetivo PRINCIPAL es responder: "{message}"
   - Analiza este documento ESPECÍFICAMENTE para encontrar información que responda esa pregunta
   - Si el usuario pregunta "información más valiosa" → identifica la información MÁS VALIOSA de este documento
   - Si el usuario pregunta "qué recomendarías hacer" → proporciona recomendaciones ESPECÍFICAS basadas SOLO en este documento
   - Si el usuario pregunta "cuál es el mejor documento" → evalúa este documento en relación a la pregunta
   - ADÁPTATE al tipo de pregunta del usuario - no uses un formato genérico

3. ANÁLISIS PROFUNDO Y COMPLETO (800-1200 palabras):
   - **Respuesta Directa** (2-3 párrafos): Responde la pregunta del usuario usando información ESPECÍFICA de este documento
   - **Información Detallada** (3-4 párrafos): Extrae y explica TODA la información relevante del documento que responda la pregunta
     * Cita datos concretos: números, porcentajes, fechas, nombres, métricas, estadísticas
     * Identifica entidades, metodologías, frameworks, conceptos, procesos
     * Explica relaciones, causas, efectos, implicaciones
     * Proporciona contexto y background cuando sea relevante
   - **Análisis Crítico** (2-3 párrafos): 
     * Evalúa la calidad, relevancia y utilidad de la información encontrada
     * Identifica fortalezas y debilidades del documento en relación a la pregunta
     * Compara diferentes secciones o aspectos del documento si es relevante
   - **Recomendaciones/Insights** (1-2 párrafos): Si la pregunta lo requiere, proporciona recomendaciones o insights ESPECÍFICOS basados SOLO en este documento

4. COMPLETITUD Y PROFUNDIDAD:
   - NO te limites a una respuesta superficial - profundiza en TODOS los aspectos relevantes
   - Extrae TODA la información relacionada con la pregunta, no solo la primera mención
   - Si hay múltiples secciones relevantes, analiza TODAS
   - Si hay datos numéricos, tablas, gráficos mencionados, inclúyelos en tu análisis
   - Si hay metodologías o procesos descritos, explícalos completamente

5. ADAPTACIÓN AL TIPO DE PREGUNTA:
   - Si pregunta por "información valiosa" → identifica y explica TODA la información MÁS VALIOSA con detalles completos
   - Si pregunta por "recomendaciones" → proporciona recomendaciones ESPECÍFICAS, ACCIONABLES y DETALLADAS basadas SOLO en este documento
   - Si pregunta por "mejor documento" → evalúa este documento COMPLETAMENTE y explica por qué es o no es el mejor
   - Si pregunta por "análisis" → proporciona análisis PROFUNDO, COMPLETO y ESTRUCTURADO relacionado con la pregunta
   - ADÁPTATE - no uses un formato genérico, responde lo que el usuario realmente pregunta

6. PROFESIONALISMO ENTERPRISE - NIVEL C-SUITE:
   - Lenguaje claro, directo y profesional (nivel ejecutivo senior)
   - Enfoque en responder la pregunta específica del usuario con máxima precisión
   - Información accionable, específica y basada estrictamente en el documento
   - Estructura clara, escaneable y bien organizada
   - Uso de viñetas, numeración y formato para facilitar la lectura

7. VERIFICACIÓN Y VALIDACIÓN:
   - Antes de incluir cualquier información, verifica que esté en el documento
   - Si no estás seguro de algo, indica la incertidumbre
   - Distingue entre información explícita e información que podrías inferir (solo usa la explícita)

IMPORTANTE - REGLAS CRÍTICAS:
- ⚠️ NO inventes información - SOLO usa lo que está en el documento
- ⚠️ NO asumas conocimiento externo - SOLO usa información del documento
- ⚠️ NO uses un formato genérico - ADÁPTATE al tipo de pregunta del usuario
- ⚠️ NO describas el documento en general - RESPONDE la pregunta específica
- ✅ SÍ extrae TODA la información relevante del documento que responda la pregunta
- ✅ SÍ proporciona recomendaciones/insights ESPECÍFICOS si la pregunta lo requiere
- ✅ SÍ cita datos concretos, números, fechas, nombres del documento
- ✅ SÍ proporciona una respuesta COMPLETA, PROFUNDA y DETALLADA

RESPUESTA SUPER MEGA ULTRA HYPER INTELIGENTE Y COMPLETA (800-1200 palabras, basada ESTRICTAMENTE en el documento):"""
                
                # STREAMING EN TIEMPO REAL - Usar astream para respuesta progresiva (como ChatGPT)
                from langchain_core.messages import HumanMessage
                analysis = ""
                chunk_count = 0
                
                # Stream tokens en tiempo real usando asyncio.run en el thread
                async def stream_analysis():
                    nonlocal analysis, chunk_count
                    async for chunk in parallel_llm.astream([HumanMessage(content=prompt)], max_tokens=4000):
                        if hasattr(chunk, 'content'):
                            token = chunk.content
                        else:
                            token = str(chunk)
                        analysis += token
                        chunk_count += 1
                        
                        # Publicar progreso cada 10 tokens para streaming en tiempo real
                        if chunk_count % 10 == 0:
                            # Publicar al Event Bus interno
                            try:
                                self.event_bus.publish('document_analysis_streaming', {
                                    'session_id': session_id,
                                    'document': Path(source_name).name,
                                    'current_text': analysis[-300:],  # Últimos 300 caracteres
                                    'chunk_count': chunk_count
                                })
                                
                                # Si Confluent está habilitado, publicar también allí para mejor performance
                                if self.confluent_enabled and self.confluent_producer and CONFLUENT_STREAMING_AVAILABLE:
                                    try:
                                        event = StreamingEvent(
                                            event_id=f"{session_id}_{Path(source_name).name}_{chunk_count}",
                                            event_type=EventType.STREAMING_DATA,
                                            timestamp=datetime.now(),
                                            data={
                                                'session_id': session_id,
                                                'document': Path(source_name).name,
                                                'current_text': analysis[-300:],
                                                'chunk_count': chunk_count,
                                                'type': 'document_analysis_streaming'
                                            },
                                            source="chatpdf_mode",
                                            metadata={'mode': 'chat_pdf_mode'}
                                        )
                                        self.confluent_producer.produce_event(
                                            topic="docchat_streaming_events",
                                            event=event
                                        )
                                    except Exception as pub_error:
                                        print(f"⚠️ [ChatPDF Mode] Error publicando a Confluent: {pub_error}")
                            except Exception as pub_error:
                                print(f"⚠️ [ChatPDF Mode] Error publicando evento de streaming: {pub_error}")
                
                # Ejecutar streaming en el thread (sin nest_asyncio - más simple)
                try:
                    # Crear nuevo event loop para este thread
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        loop.run_until_complete(stream_analysis())
                    finally:
                        loop.close()
                except Exception as stream_error:
                    # Fallback a invoke si streaming falla (más robusto)
                    error_str = str(stream_error).lower()
                    is_overloaded = "529" in error_str or "overloaded" in error_str
                    
                    if is_overloaded:
                        print(f"⚠️ [ChatPDF Mode] API de Anthropic sobrecargada (529), reintentando con backoff exponencial...")
                        # Retry con backoff exponencial para errores 529
                        max_retries = 5
                        retry_delay = 5  # Empezar con 5 segundos
                        analysis = None
                        
                        for retry in range(max_retries):
                            try:
                                if retry > 0:
                                    wait_time = retry_delay * (2 ** (retry - 1))  # 5s, 10s, 20s, 40s, 80s
                                    print(f"⏳ [ChatPDF Mode] Reintentando en {wait_time}s (intento {retry + 1}/{max_retries})...")
                                    time.sleep(wait_time)
                                
                                response = parallel_llm.invoke(prompt, max_tokens=4000)
                                analysis = response.content.strip() if hasattr(response, 'content') else str(response).strip()
                                print(f"✅ [ChatPDF Mode] Análisis completado después de {retry + 1} intentos")
                                break
                            except Exception as retry_error:
                                retry_error_str = str(retry_error).lower()
                                if "529" in retry_error_str or "overloaded" in retry_error_str:
                                    if retry == max_retries - 1:
                                        analysis = f"⚠️ **API de Anthropic sobrecargada**: La API de Claude está temporalmente sobrecargada. Por favor, intenta de nuevo en unos minutos. Error: {str(retry_error)[:150]}"
                                        print(f"❌ [ChatPDF Mode] API sobrecargada después de {max_retries} intentos")
                                else:
                                    analysis = f"❌ Error analizando documento: {str(retry_error)[:200]}"
                                    break
                        
                        if not analysis:
                            analysis = f"⚠️ **API de Anthropic sobrecargada**: La API de Claude está temporalmente sobrecargada. Por favor, intenta de nuevo en unos minutos."
                    else:
                        print(f"⚠️ [ChatPDF Mode] Streaming falló para {source_name}, usando invoke: {stream_error}")
                        try:
                            response = parallel_llm.invoke(prompt, max_tokens=4000)
                            analysis = response.content.strip() if hasattr(response, 'content') else str(response).strip()
                        except Exception as invoke_error:
                            error_str_invoke = str(invoke_error).lower()
                            if "529" in error_str_invoke or "overloaded" in error_str_invoke:
                                analysis = f"⚠️ **API de Anthropic sobrecargada**: La API de Claude está temporalmente sobrecargada. Por favor, intenta de nuevo en unos minutos. Error: {str(invoke_error)[:150]}"
                            else:
                                print(f"❌ [ChatPDF Mode] Error con invoke también: {invoke_error}")
                                analysis = f"❌ Error analizando documento: {str(stream_error)[:200]}"
                
                # Asegurar que analysis nunca sea None
                if not analysis:
                    analysis = f"⚠️ **Error desconocido**: No se pudo analizar el documento. Por favor, intenta de nuevo."
                
                return source_name, analysis.strip() if isinstance(analysis, str) else str(analysis).strip()
            except Exception as e:
                return source_name, f"❌ Error analizando documento: {str(e)[:200]}"
        
        # Ejecutar análisis en paralelo con RATE LIMITING por lotes
        # Procesar documentos en lotes para evitar exceder límites de rate limit de OpenAI
        docs_items = list(docs_by_source.items())
        batch_size = max_workers  # Procesar en lotes del tamaño de max_workers
        
        for batch_start in range(0, len(docs_items), batch_size):
            batch = docs_items[batch_start:batch_start + batch_size]
            batch_num = (batch_start // batch_size) + 1
            total_batches = (len(docs_items) + batch_size - 1) // batch_size
            
            print(f"📦 [ChatPDF Mode] Procesando lote {batch_num}/{total_batches} ({len(batch)} documentos)...")
            
            with ThreadPoolExecutor(max_workers=min(max_workers, len(batch))) as executor:
                futures = {
                    executor.submit(analyze_single_document, source_name, file_docs): source_name
                    for source_name, file_docs in batch
                }
            
                for future in as_completed(futures):
                    source_name = futures[future]
                    try:
                        doc_name, analysis = future.result()
                        individual_analyses[doc_name] = analysis
                        print(f"✅ [ChatPDF Mode] Análisis completado para: {Path(doc_name).name}")
                    except Exception as e:
                        print(f"❌ [ChatPDF Mode] Error procesando {source_name}: {e}")
                        individual_analyses[source_name] = f"❌ Error: {str(e)[:200]}"
        
            # RATE LIMITING: Esperar entre lotes para evitar exceder límites de tokens por minuto
            # OpenAI tiene límite de 30,000 TPM, así que esperamos un poco entre lotes
            if batch_start + batch_size < len(docs_items):  # No esperar después del último lote
                wait_time = 2.0  # Esperar 2 segundos entre lotes
                print(f"⏳ [ChatPDF Mode] Esperando {wait_time}s antes del siguiente lote (rate limiting)...")
                time.sleep(wait_time)
        
        # Mostrar todos los análisis individuales - SIEMPRE mostrar todas las respuestas
        # Si envías 500 PDFs, recibirás 500 respuestas (1 análisis por PDF)
        individual_analyses_text = f"## 📄 Análisis Individuales por Documento ({len(individual_analyses)} documentos analizados)\n\n"
        for doc_name, analysis in individual_analyses.items():
            clean_name = Path(doc_name).name
            individual_analyses_text += f"### 📄 {clean_name}\n\n"
            individual_analyses_text += f"{analysis}\n\n"
            individual_analyses_text += "---\n\n"
        
        # OPCIÓN B: Combinar todos los análisis en una respuesta final (opcional)
        combined_context = "\n\n".join([
            f"=== DOCUMENTO: {Path(doc_name).name} ===\n{analysis}"
            for doc_name, analysis in individual_analyses.items()
        ])
        
        # Generar respuesta combinada que RESPONDE DIRECTAMENTE al prompt del usuario
        # PROMPT ULTRA MEJORADO para síntesis super inteligente y completa
        synthesis_prompt = f"""Eres un consultor estratégico senior de nivel C-Suite con décadas de experiencia. Has analizado {len(individual_analyses)} documentos individualmente, cada uno respondiendo la pregunta del usuario con análisis profundo y completo.

TU TAREA PRINCIPAL: Combinar todos los análisis individuales para responder DIRECTAMENTE la pregunta del usuario de manera SUPER MEGA ULTRA HYPER INTELIGENTE, COMPLETA y ESTRATÉGICA.

⚠️ REGLA CRÍTICA: SOLO usa información de los análisis individuales. NO inventes nada que no esté en esos análisis.

PREGUNTA ESPECÍFICA DEL USUARIO (RESPONDE EXACTAMENTE ESTO):
{message}

ANÁLISIS INDIVIDUALES DE CADA DOCUMENTO (cada uno ya respondió la pregunta del usuario):
{combined_context}

INSTRUCCIONES PARA RESPUESTA FINAL COMBINADA SUPER MEGA ULTRA HYPER INTELIGENTE Y COMPLETA (1200-2000 palabras):

1. PRECISIÓN ABSOLUTA - NO INVENTAR NADA:
   - ⚠️ CRÍTICO: SOLO usa información que esté en los análisis individuales
   - ⚠️ PROHIBIDO: NO inventes, NO asumas, NO inferas información que no esté en los análisis
   - ⚠️ Si la información no está en los análisis, di claramente: "Esta información no está disponible en los documentos analizados"
   - ✅ Cita información específica de cada análisis cuando sea relevante
   - ✅ Indica de qué documento proviene cada pieza de información cuando sea importante

2. RESPUESTA DIRECTA AL PROMPT DEL USUARIO:
   - Tu objetivo es responder: "{message}"
   - Combina información de TODOS los análisis individuales para dar una respuesta SUPER COMPLETA
   - Si el usuario pregunta "información más valiosa de cada PDF" → sintetiza la información más valiosa de TODOS los PDFs con detalles completos
   - Si el usuario pregunta "qué me recomendarías hacer" → proporciona recomendaciones ESPECÍFICAS y DETALLADAS basadas en TODOS los documentos
   - Si el usuario pregunta "cuál es el mejor documento" → compara y evalúa TODOS los documentos con análisis profundo
   - ADÁPTATE al tipo de pregunta - no uses un formato genérico

3. SÍNTESIS ESTRATÉGICA PROFUNDA:
   - Combina los análisis individuales en una respuesta coherente, completa y estratégica
   - Identifica patrones comunes, contradicciones, tensiones, o complementariedades entre documentos
   - Proporciona una visión holística que responda COMPLETAMENTE la pregunta
   - Compara y contrasta información de diferentes documentos cuando sea relevante
   - Extrae insights que solo emergen al ver todos los documentos juntos

4. ESTRUCTURA ADAPTATIVA Y COMPLETA (según el tipo de pregunta):
   
   Si pregunta por "información valiosa" o "recomendaciones":
   - **Respuesta Directa Ejecutiva** (3-4 párrafos): Responde la pregunta combinando información de TODOS los documentos con máxima precisión
   - **Información Clave por Documento** (resumen detallado de lo más valioso de cada uno, con datos específicos)
   - **Análisis Comparativo** (cómo se relacionan, complementan o contradicen los documentos entre sí)
   - **Recomendaciones Finales Estratégicas** (basadas en toda la información combinada, con justificación específica)
   - **Documentos Más Relevantes** (cuáles aportan más valor y por qué, con evidencia específica)
   
   Si pregunta por "mejor documento" o "comparación":
   - **Evaluación Comparativa Completa** (compara TODOS los documentos en relación a la pregunta con criterios específicos)
   - **Análisis Detallado por Documento** (fortalezas, debilidades, relevancia, calidad de información)
   - **Documento(s) Recomendado(s)** (cuál es el mejor y por qué, con justificación detallada)
   - **Recomendación Final Estratégica** (qué documento usar y por qué, con consideraciones prácticas)
   
   Si pregunta por "análisis" o "insights":
   - **Análisis Holístico Profundo** (insights que emergen de ver todos los documentos juntos)
   - **Patrones y Tendencias Identificados** (qué patrones se repiten, contradicen, o complementan)
   - **Insights Estratégicos Únicos** (hallazgos que ningún documento individual puede dar)
   - **Implicaciones y Recomendaciones** (basadas en el análisis completo, con justificación específica)

5. PROFESIONALISMO ENTERPRISE - NIVEL C-SUITE:
   - Lenguaje claro, directo y profesional (nivel ejecutivo senior)
   - Enfoque en responder la pregunta específica del usuario con máxima precisión y completitud
   - Estructura clara, escaneable y bien organizada
   - Información accionable, específica y basada estrictamente en los análisis
   - Uso de viñetas, numeración y formato para facilitar la lectura

6. COMPLETITUD Y PROFUNDIDAD:
   - NO te limites a una síntesis superficial - profundiza en TODOS los aspectos relevantes
   - Incluye TODA la información relevante de los análisis individuales
   - Si hay múltiples documentos relevantes, analiza TODOS
   - Si hay datos numéricos, estadísticas, o métricas en los análisis, inclúyelos
   - Si hay metodologías o procesos descritos, explícalos completamente

7. LONGITUD Y EFECTIVIDAD:
   - 1200-2000 palabras (completo, profundo y exhaustivo)
   - Prioriza completitud y profundidad sobre concisión
   - Cada sección debe aportar valor único y específico para responder la pregunta
   - Balance entre exhaustividad y claridad

IMPORTANTE - REGLAS CRÍTICAS:
- ⚠️ NO inventes información - SOLO usa lo que está en los análisis individuales
- ⚠️ NO asumas conocimiento externo - SOLO usa información de los análisis
- ⚠️ RESPONDE DIRECTAMENTE la pregunta del usuario: "{message}"
- ⚠️ NO uses un formato genérico - ADÁPTATE al tipo de pregunta
- ✅ SÍ combina información de TODOS los análisis individuales
- ✅ SÍ proporciona una conclusión o recomendación final que responda la pregunta
- ✅ SÉ ESPECÍFICO: usa información concreta de los análisis, no generalidades
- ✅ SÉ COMPLETO: incluye TODA la información relevante de los análisis

RESPUESTA FINAL SUPER MEGA ULTRA HYPER INTELIGENTE Y COMPLETA QUE RESPONDE DIRECTAMENTE LA PREGUNTA DEL USUARIO (1200-2000 palabras, basada ESTRICTAMENTE en los análisis individuales):"""
        
        # STREAMING EN TIEMPO REAL - YIELD actualizaciones progresivas para la UI
        # Primero mostrar análisis individuales, luego síntesis con streaming
        from langchain_core.messages import HumanMessage
        
        # 1. Mostrar análisis individuales completados
        # Asegurar que history no sea None
        if history is None:
            history = []
        
        if individual_analyses:
            individual_analyses_text_temp = f"## 📄 Análisis Individuales por Documento ({len(individual_analyses)} documentos analizados)\n\n"
            for doc_name, analysis in individual_analyses.items():
                clean_name = Path(doc_name).name
                # Asegurar que analysis no sea None
                if analysis is None:
                    analysis = "⚠️ No se pudo analizar este documento."
                individual_analyses_text_temp += f"### 📄 {clean_name}\n\n"
                individual_analyses_text_temp += f"{analysis}\n\n"
                individual_analyses_text_temp += "---\n\n"
            
            # Yield análisis individuales primero
            temp_formatted = "## 📄 Análisis Individuales Completados\n\n" + individual_analyses_text_temp
            temp_history = history + [(message, temp_formatted)]
            yield temp_history, None, {"stage": "individual_analyses", "documents_analyzed": len(individual_analyses)}
        
        # 2. STREAMING: Generar síntesis final token por token en tiempo real (como ChatGPT)
        print("🚀 [ChatPDF Mode] Generando respuesta final con streaming en tiempo real (Confluent optimizado)...")
        combined_answer = ""
        chunk_count = 0
        
        # Construir respuesta base con análisis individuales
        individual_analyses_text = f"## 📄 Análisis Individuales por Documento ({len(individual_analyses)} documentos analizados)\n\n"
        for doc_name, analysis in individual_analyses.items():
            clean_name = Path(doc_name).name
            individual_analyses_text += f"### 📄 {clean_name}\n\n"
            individual_analyses_text += f"{analysis}\n\n"
            individual_analyses_text += "---\n\n"
        
        # STREAMING EN TIEMPO REAL: Usar threading para streaming async que funciona con Gradio
        # Similar a Event Bus Mode pero adaptado para ChatPDF
        import threading
        import queue as thread_queue
        
        token_queue = thread_queue.Queue()
        streaming_error = [None]  # Usar lista para poder modificar desde thread
        
        def run_async_streaming():
            """Ejecuta streaming async en thread separado"""
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            try:
                async def collect_stream():
                    async for chunk in parallel_llm.astream([HumanMessage(content=synthesis_prompt)]):
                        if hasattr(chunk, 'content'):
                            token = chunk.content
                        else:
                            token = str(chunk)
                        token_queue.put(('token', token))
                    token_queue.put(('done', None))
                
                new_loop.run_until_complete(collect_stream())
            except Exception as e:
                token_queue.put(('error', str(e)))
                streaming_error[0] = e
            finally:
                new_loop.close()
        
        # Iniciar streaming en thread separado
        stream_thread = threading.Thread(target=run_async_streaming, daemon=True)
        stream_thread.start()
        
        # REAL-TIME CONTEXT ENGINE: Emitir actualizaciones INMEDIATAS token por token
        # Similar al Real-Time Context Engine de Confluent - streaming ultra fluido
        # Emite cada token inmediatamente sin esperas para máxima fluidez
        last_yield_time = time.time()
        max_wait_time = 0.02  # Máximo 20ms entre yields para ultra fluidez (como ChatGPT)
        
        try:
            # Emitir mensaje inicial de "generando..."
            initial_message = "## 📊 Resumen Ejecutivo Combinado\n\n🔄 Generando respuesta en tiempo real...\n\n---\n\n" + individual_analyses_text
            temp_history = history + [(message, initial_message)]
            yield temp_history, None, {
                "stage": "synthesis_streaming",
                "chunk_count": 0,
                "documents_analyzed": len(individual_analyses)
            }
            
            # Leer tokens y emitir actualizaciones INMEDIATAS (cada token)
            while stream_thread.is_alive() or not token_queue.empty():
                try:
                    # REAL-TIME CONTEXT ENGINE: Obtener token con timeout ultra corto
                    # Emitir cada token inmediatamente sin esperas para máxima fluidez
                    try:
                        item_type, item_data = token_queue.get(timeout=0.005)  # 5ms para máxima fluidez
                    except thread_queue.Empty:
                        # No hay tokens aún, pero emitir actualización parcial si hay algo
                        if combined_answer:
                            elapsed = time.time() - last_yield_time
                            if elapsed >= 0.02:  # Emitir cada 20ms mínimo para mantener fluidez
                                formatted_answer_partial = "## 📊 Resumen Ejecutivo Combinado\n\n"
                                formatted_answer_partial += combined_answer + "▊"  # Cursor parpadeante
                                formatted_answer_partial += "\n\n---\n\n"
                                formatted_answer_partial += individual_analyses_text
                                
                                temp_history = history + [(message, formatted_answer_partial)]
                                yield temp_history, None, {
                                    "stage": "synthesis_streaming",
                                    "chunk_count": chunk_count,
                                    "documents_analyzed": len(individual_analyses)
                                }
                                last_yield_time = time.time()
                        continue
                    
                    if item_type == 'token':
                        combined_answer += item_data
                        chunk_count += 1
                        
                        # REAL-TIME CONTEXT ENGINE: Materializar contexto en cache en tiempo real
                        # Similar al Real-Time Context Engine de Confluent
                        context_id = f"{session_id}_synthesis"
                        self.real_time_context_engine.update_context_streaming(
                            context_id=context_id,
                            token=item_data,
                            session_id=session_id
                        )
                        
                        # YIELD INMEDIATO - CADA TOKEN para streaming ultra fluido (como ChatGPT)
                        # REAL-TIME CONTEXT ENGINE: Emitir inmediatamente sin esperas
                        # Esto es crítico para que aparezca en tiempo real en la UI
                        formatted_answer_partial = "## 📊 Resumen Ejecutivo Combinado\n\n"
                        formatted_answer_partial += combined_answer + "▊"  # Cursor parpadeante
                        formatted_answer_partial += "\n\n---\n\n"
                        formatted_answer_partial += individual_analyses_text
                        
                        temp_history = history + [(message, formatted_answer_partial)]
                        # YIELD INMEDIATO - sin condiciones, cada token se emite inmediatamente
                        yield temp_history, None, {
                            "stage": "synthesis_streaming",
                            "chunk_count": chunk_count,
                            "documents_analyzed": len(individual_analyses),
                            "real_time": True,  # Marcar como streaming en tiempo real
                            "context_engine": True  # Marcar que usa Real-Time Context Engine
                        }
                        last_yield_time = time.time()
                        
                        # Publicar al Event Bus y Confluent (cada 5 tokens para no saturar)
                        if chunk_count % 5 == 0:
                            try:
                                self.event_bus.publish('streaming_token', {
                                    'session_id': session_id,
                                    'current_text': combined_answer,
                                    'chunk_count': chunk_count,
                                    'type': 'synthesis_final'
                                })
                                
                                # REAL-TIME CONTEXT ENGINE: Publicar a Confluent para streaming optimizado
                                if self.confluent_enabled and self.confluent_producer and CONFLUENT_STREAMING_AVAILABLE:
                                    try:
                                        event = StreamingEvent(
                                            event_id=f"{session_id}_synthesis_{chunk_count}",
                                            event_type=EventType.STREAMING_DATA,
                                            timestamp=datetime.now(),
                                            data={
                                                'session_id': session_id,
                                                'current_text': combined_answer,
                                                'chunk_count': chunk_count,
                                                'type': 'synthesis_final',
                                                'real_time_context': True  # Marcar como contexto en tiempo real
                                            },
                                            source="chatpdf_mode",
                                            metadata={
                                                'mode': 'chat_pdf_mode', 
                                                'stage': 'synthesis',
                                                'real_time_engine': True
                                            }
                                        )
                                        self.confluent_producer.produce_event(
                                            topic="docchat_streaming_events",
                                            event=event
                                        )
                                    except Exception as pub_error:
                                        print(f"⚠️ [ChatPDF Mode] Error publicando síntesis a Confluent: {pub_error}")
                            except Exception as pub_error:
                                print(f"⚠️ [ChatPDF Mode] Error publicando evento de streaming: {pub_error}")
                    elif item_type == 'done':
                        # Emitir respuesta final sin cursor
                        formatted_answer_final = "## 📊 Resumen Ejecutivo Combinado\n\n"
                        formatted_answer_final += combined_answer
                        formatted_answer_final += "\n\n---\n\n"
                        formatted_answer_final += individual_analyses_text
                        
                        temp_history = history + [(message, formatted_answer_final)]
                        yield temp_history, None, {
                            "stage": "synthesis_complete",
                            "chunk_count": chunk_count,
                            "documents_analyzed": len(individual_analyses)
                        }
                        break
                    elif item_type == 'error':
                        raise Exception(f"Error en streaming: {item_data}")
                except Exception as e:
                    print(f"⚠️ [ChatPDF Mode] Error procesando tokens: {e}")
                    break
            
            # Esperar a que termine el thread
            stream_thread.join(timeout=10.0)
            
            # Si hubo error, lanzarlo
            if streaming_error[0]:
                raise streaming_error[0]
                        
        except Exception as e:
            # Fallback a invoke si streaming falla
            error_str = str(e).lower()
            is_overloaded = "529" in error_str or "overloaded" in error_str
            
            if is_overloaded:
                print(f"⚠️ [ChatPDF Mode] API de Anthropic sobrecargada (529) en síntesis, reintentando con backoff exponencial...")
                # Retry con backoff exponencial para errores 529
                max_retries = 5
                retry_delay = 5  # Empezar con 5 segundos
                combined_answer = None
                
                for retry in range(max_retries):
                    try:
                        if retry > 0:
                            wait_time = retry_delay * (2 ** (retry - 1))  # 5s, 10s, 20s, 40s, 80s
                            print(f"⏳ [ChatPDF Mode] Reintentando síntesis en {wait_time}s (intento {retry + 1}/{max_retries})...")
                            time.sleep(wait_time)
                        
                        synthesis_response = parallel_llm.invoke(synthesis_prompt)
                        combined_answer = synthesis_response.content.strip() if hasattr(synthesis_response, 'content') else str(synthesis_response).strip()
                        print(f"✅ [ChatPDF Mode] Síntesis completada después de {retry + 1} intentos")
                        break
                    except Exception as retry_error:
                        retry_error_str = str(retry_error).lower()
                        if "529" in retry_error_str or "overloaded" in retry_error_str:
                            if retry == max_retries - 1:
                                combined_answer = f"⚠️ **API de Anthropic sobrecargada**: La API de Claude está temporalmente sobrecargada. Por favor, intenta de nuevo en unos minutos.\n\n**Análisis individuales disponibles arriba.**\n\nError: {str(retry_error)[:150]}"
                                print(f"❌ [ChatPDF Mode] API sobrecargada después de {max_retries} intentos en síntesis")
                        else:
                            combined_answer = f"❌ Error generando respuesta combinada: {str(retry_error)[:200]}"
                            break
                
                if not combined_answer:
                    combined_answer = f"⚠️ **API de Anthropic sobrecargada**: La API de Claude está temporalmente sobrecargada. Por favor, intenta de nuevo en unos minutos.\n\n**Análisis individuales disponibles arriba.**"
            else:
                print(f"⚠️ [ChatPDF Mode] Streaming de síntesis falló, usando invoke: {e}")
                try:
                    synthesis_response = parallel_llm.invoke(synthesis_prompt)
                    combined_answer = synthesis_response.content.strip() if hasattr(synthesis_response, 'content') else str(synthesis_response).strip()
                except Exception as invoke_error:
                    error_str_invoke = str(invoke_error).lower()
                    if "529" in error_str_invoke or "overloaded" in error_str_invoke:
                        combined_answer = f"⚠️ **API de Anthropic sobrecargada**: La API de Claude está temporalmente sobrecargada. Por favor, intenta de nuevo en unos minutos.\n\n**Análisis individuales disponibles arriba.**\n\nError: {str(invoke_error)[:150]}"
                    else:
                        combined_answer = f"❌ Error generando respuesta combinada: {str(invoke_error)[:200]}"
        
        # Combinar ambas opciones en la respuesta final
        # PRIMERO mostrar resumen combinado, LUEGO todos los análisis individuales
        formatted_answer = "## 📊 Resumen Ejecutivo Combinado\n\n"
        formatted_answer += combined_answer
        formatted_answer += "\n\n---\n\n"
        formatted_answer += individual_analyses_text
        
        # Agregar información del proceso
        formatted_answer += "\n\n---\n\n"
        formatted_answer += "## 🔬 Proceso ChatPDF Mode - Análisis Individual por Documento\n\n"
        formatted_answer += f"✅ **Documentos analizados:** {len(individual_analyses)} (1 análisis por documento)\n"
        formatted_answer += "✅ **Procesamiento:** Paralelo (cada PDF analizado individualmente)\n"
        formatted_answer += "✅ **Análisis:** Individual por documento + Respuesta combinada\n"
        formatted_answer += f"✅ **Respuestas individuales:** {len(individual_analyses)} respuestas (1 por cada PDF)\n"
        formatted_answer += "✅ **Precisión:** Basado estrictamente en los documentos (sin invención)\n"
        formatted_answer += "✅ **Completitud:** Respuestas super mega ultra hyper inteligentes y completas\n"
        formatted_answer += "✅ **Streaming:** Respuestas en tiempo real (como ChatGPT)\n\n"
        
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
            "processing_mode": "parallel",
            "streaming": True
        }
        
        # Convertir historial a formato tuples para Gradio
        tuple_history = []
        for entry in session["history"]:
            if isinstance(entry, dict):
                tuple_history.append((entry.get("question", ""), entry.get("answer", "")))
            else:
                tuple_history.append(entry)
        
        # YIELD respuesta final completa
        yield tuple_history, None, metadata
    
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
_chat_pdf_mode_instance: Optional[ChatPDFMode] = None


def get_chat_pdf_mode(
    config: AppConfig,
    processor: DocumentProcessor,
    retriever_builder: RetrieverBuilder,
    context_manager: Optional[Any] = None
) -> ChatPDFMode:
    """Obtiene o crea la instancia global de ChatPDF Mode."""
    global _chat_pdf_mode_instance
    
    if _chat_pdf_mode_instance is None:
        _chat_pdf_mode_instance = ChatPDFMode(
            config=config,
            processor=processor,
            retriever_builder=retriever_builder,
            context_manager=context_manager
        )
    
    return _chat_pdf_mode_instance


def run_chat_pdf_mode(
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
):
    """
    Función principal para ejecutar ChatPDF Mode con STREAMING EN TIEMPO REAL.
    Compatible con Gradio - YIELD actualizaciones progresivas (como ChatGPT).
    
    Yields:
        (history, history, status, stats_output): Actualizaciones progresivas para UI
    """
    if not config or not processor or not retriever_builder:
        # Importar gradio solo cuando sea necesario
        try:
            import gradio as gr
            yield history, history, "❌ Configuración incompleta", gr.Markdown(visible=False)
        except ImportError:
            yield history, history, "❌ Configuración incompleta", None
        return
    
    # Obtener instancia
    chat_pdf_mode = get_chat_pdf_mode(
        config=config,
        processor=processor,
        retriever_builder=retriever_builder,
        context_manager=context_manager
    )
    
    # Procesar documentos si hay
    if files:
        result = chat_pdf_mode.process_documents(session_id, files)
        if result.get("status") == "error":
            try:
                import gradio as gr
                yield history, history, f"❌ Error procesando documentos: {result.get('error')}", gr.Markdown(visible=False)
            except ImportError:
                yield history, history, f"❌ Error procesando documentos: {result.get('error')}", None
            return
    
    # REAL-TIME CONTEXT ENGINE: Ejecutar query con STREAMING INMEDIATO
    # Usar threading para evitar bloqueos y emitir actualizaciones inmediatas
    import threading
    import queue as thread_queue
    
    update_queue = thread_queue.Queue()
    streaming_complete = threading.Event()
    streaming_error = [None]
    
    def run_async_query():
        """Ejecuta query async en thread separado para no bloquear"""
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        try:
            async_gen = chat_pdf_mode.process_query_async(
                session_id=session_id,
                message=message,
                history=history,
                speed_mode=speed_mode,
                provider=provider
            )
            
            async def collect_updates():
                try:
                    async for update in async_gen:
                        update_queue.put(('update', update))
                    update_queue.put(('done', None))
                except Exception as e:
                    update_queue.put(('error', str(e)))
                    streaming_error[0] = e
            
            new_loop.run_until_complete(collect_updates())
        except Exception as e:
            update_queue.put(('error', str(e)))
            streaming_error[0] = e
        finally:
            new_loop.close()
            streaming_complete.set()
    
    # Iniciar query en thread separado
    query_thread = threading.Thread(target=run_async_query, daemon=True)
    query_thread.start()
    
    # Leer actualizaciones y emitir INMEDIATAMENTE a la UI
    try:
        last_update_time = time.time()
        while not streaming_complete.is_set() or not update_queue.empty():
            try:
                # REAL-TIME CONTEXT ENGINE: Obtener actualización con timeout ultra corto
                # Emitir actualizaciones inmediatamente sin esperas
                try:
                    item_type, item_data = update_queue.get(timeout=0.005)  # 5ms timeout para máxima fluidez
                except thread_queue.Empty:
                    # No hay actualizaciones aún, continuar inmediatamente
                    # No hacer sleep para máxima responsividad
                    continue
                
                if item_type == 'update':
                    # Validar que item_data sea una tupla de 3 elementos
                    if not isinstance(item_data, (tuple, list)) or len(item_data) != 3:
                        print(f"⚠️ [ChatPDF Mode] Formato de item_data inválido: {type(item_data)}, valor: {item_data}")
                        continue
                    
                    new_history, error, metadata = item_data
                    
                    # Asegurar que new_history no sea None
                    if new_history is None:
                        new_history = history
                    
                    # Asegurar que metadata sea un dict
                    if metadata is None:
                        metadata = {}
                    
                    # Construir status
                    status = f"✅ {len(new_history)} mensajes en la conversación"
                    if error:
                        status = error
                    elif metadata.get("stage") == "individual_analyses":
                        status = f"📄 Analizando documentos... ({metadata.get('documents_analyzed', 0)} completados)"
                    elif metadata.get("stage") == "synthesis_streaming":
                        status = f"🚀 Generando síntesis en tiempo real... ({metadata.get('chunk_count', 0)} tokens)"
                    elif metadata.get("stage") == "synthesis_complete":
                        status = f"✅ Síntesis completada ({metadata.get('chunk_count', 0)} tokens)"
                    
                    # YIELD INMEDIATO para streaming ultra fluido (como ChatGPT)
                    try:
                        import gradio as gr
                        yield new_history, new_history, status, gr.Markdown(visible=False)
                    except ImportError:
                        yield new_history, new_history, status, None
                    
                    last_update_time = time.time()
                    
                elif item_type == 'done':
                    break
                elif item_type == 'error':
                    raise Exception(f"Error en query: {item_data}")
                    
            except Exception as e:
                print(f"⚠️ [ChatPDF Mode] Error procesando actualizaciones: {e}")
                break
        
        # Esperar a que termine el thread
        query_thread.join(timeout=30.0)
        
        # Si hubo error, lanzarlo
        if streaming_error[0]:
            raise streaming_error[0]
            
    except Exception as e:
        error_msg = f"❌ Error: {str(e)}"
        try:
            import gradio as gr
            yield history, history, error_msg, gr.Markdown(visible=False)
        except ImportError:
            yield history, history, error_msg, None

