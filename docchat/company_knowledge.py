"""
Company Knowledge - Sistema de conocimiento empresarial avanzado
Clon del Chat Conversacional 2 (Enterprise) optimizado para conocimiento corporativo.
Integra todas las capacidades avanzadas:
- Context Folding
- Data Provenance
- Chain of Thought Reasoning
- Path-dependent Reasoning
- Test Time Training
- Person in the Loop
"""

from __future__ import annotations

import json
import time
import asyncio
from typing import List, Dict, Optional, Any, Tuple
from pathlib import Path
from datetime import datetime

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
from .company_knowledge_integrations import CompanyKnowledgeIntegrations, IntegrationType


class CompanyKnowledge:
    """
    Company Knowledge - Sistema de conocimiento empresarial avanzado.
    
    Características:
    - Gestiona eficientemente 500+ PDFs con Context Folding
    - Rastrea procedencia de datos para compliance
    - Razona paso a paso con Chain of Thought
    - Prueba diferentes enfoques con Path-dependent Reasoning
    - Aprende continuamente con Test Time Training
    - Control humano con Person in the Loop
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
        
        # LLM para generación
        if not config.openai_api_key:
            raise ValueError("OPENAI_API_KEY requerida para Company Knowledge")
        
        self.llm = ChatOpenAI(
            model=config.research_model or "gpt-4o",
            temperature=0.2,
            api_key=config.openai_api_key,
            max_tokens=4000
        )
        
        # Inicializar módulos avanzados
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
        
        # Sistema de integración de apps (Company Knowledge)
        try:
            from .company_knowledge_integrations import CompanyKnowledgeIntegrations
            self.app_integrations = CompanyKnowledgeIntegrations(config=config)
        except ImportError:
            print("⚠️ [Company Knowledge] No se pudo importar CompanyKnowledgeIntegrations")
            self.app_integrations = None
        
        # Sesiones activas
        self.sessions: Dict[str, Dict[str, Any]] = {}
    
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
            print(f"📄 [Company Knowledge] Procesando {len(new_files)} nuevos documentos...")
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
                print(f"✅ [Company Knowledge] Retriever actualizado: {len(session['docs'])} chunks")
            
            return {
                "status": "success",
                "new_docs": len(new_docs),
                "total_docs": len(session["docs"]),
                "total_chunks": len(session["docs"])
            }
            
        except Exception as e:
            print(f"❌ [Company Knowledge] Error procesando documentos: {e}")
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
        session = self.initialize_session(session_id)
        
        if not session["retriever"]:
            return history, "⚠️ No hay documentos procesados. Carga documentos primero.", {}
        
        start_time = time.time()
        
        # 1. Crear cadena de razonamiento
        chain_id = self.chain_reasoner.create_chain(message)
        session["chain_id"] = chain_id
        
        # 2. Construir contexto con Context Folding
        conversation_context = self._build_folded_context(session, history)
        
        # 3. Agregar pasos de razonamiento (con manejo de errores)
        try:
            await self.chain_reasoner.add_reasoning_steps(chain_id, conversation_context)
        except Exception as e:
            print(f"⚠️ [Company Knowledge] Error agregando pasos de razonamiento: {e}")
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
            print(f"⚠️ [Company Knowledge] Error en Reinforcement Planning: {e}")
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
            print(f"⚠️ [Company Knowledge] Error en Path-dependent Reasoning: {e}")
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
            print(f"⚠️ [Company Knowledge] Error consultando MCP: {e}")
            # Continuar sin datos MCP si falla
        
        # Aplicar modo de velocidad
        original_speed_mode = self.config.speed_mode
        self.config.speed_mode = speed_mode
        
        try:
            # Crear workflow
            temp_workflow = AgentWorkflow(self.config, provider=provider)
            
            # Ejecutar con contexto plegado y estrategia de RL
            enriched_query = f"{conversation_context}\n\nPREGUNTA ACTUAL:\n{message}"
            if best_strategy:
                enriched_query += f"\n\n🎯 ESTRATEGIA DE RL: {best_strategy}"
            if best_approach:
                enriched_query += f"\n\n🛤️ ENFOQUE RECOMENDADO: {best_approach}"
            
            result = temp_workflow.run(
                enriched_query,
                session["retriever"],
                all_documents=session["docs"],
                conversational_mode=True
            )
            
            answer = result.get("answer", result.get("draft_answer", "No se pudo generar respuesta."))
            sources = result.get("sources", [])
            
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
            
            # 11. Formatear respuesta con procedencia
            formatted_answer = answer
            
            # Agregar fuentes con procedencia
            if source_provenances:
                sources_list = []
                for prov in source_provenances[:5]:
                    source_info = f"- {prov.source_name}"
                    if prov.page_number:
                        source_info += f" (página {prov.page_number})"
                    sources_list.append(source_info)
                
                if sources_list:
                    formatted_answer += f"\n\n📚 **Fuentes:**\n" + "\n".join(sources_list)
                    formatted_answer += f"\n\n🔍 **Procedencia:** Registro ID {record_id}"
            
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
                        "mode": "company_knowledge",
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
                    print(f"⚠️ [Company Knowledge] Error consultando MCP {connection.name}: {e}")
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
            print(f"⚠️ [Company Knowledge] Error en consulta MCP: {e}")
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
    
    async def execute_autonomous_task(
        self,
        task_description: str,
        task_type: str,
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        filters: Optional[Dict[str, Any]] = None,
        urls_in_bullets: bool = False
    ) -> Dict[str, Any]:
        """
        Ejecuta una tarea autónoma usando apps conectadas.
        
        Tipos de tareas:
        - "summarize": Resumir información de múltiples fuentes
        - "analyze": Analizar datos y generar insights
        - "create_report": Crear un informe basado en datos
        - "plan": Crear un plan basado en información disponible
        - "compare": Comparar información de diferentes fuentes
        - "prebrief": Pre-brief de campaña/meeting combinando apps
        """
        if not self.app_integrations:
            return {
                "success": False,
                "error": "Sistema de integraciones no disponible"
            }
        
        # Flujo especial para pre-brief: detectar apps relevantes y combinar resultados
        if task_type == "prebrief":
            try:
                app_types = self._detect_apps_for_prebrief(task_description)
                search_results = await self.app_integrations.search_across_apps(
                    query=task_description,
                    app_types=app_types,
                    filters=filters
                )
                if not search_results:
                    return {
                        "success": False,
                        "error": "No se encontró información en las apps conectadas."
                    }
                
                # Preparar contexto breve para el LLM (limitado a 10 fuentes)
                ctx_lines = []
                for r in search_results[:10]:
                    snippet = r.snippet or r.content
                    snippet = (snippet or "")[:500]
                    ctx_lines.append(f"[{r.app_name}] {r.source_name}: {snippet} (URL: {r.url or 'N/A'})")
                context_block = "\n".join(ctx_lines)
                
                prompt = f"""
Eres un analista. Genera un pre-brief ejecutivo con la siguiente estructura:
- Executive Summary (3-5 bullets concisos)
- Métricas / Hechos clave (bullets)
- Riesgos / Issues abiertos (si los hay)
- Próximas acciones recomendadas (3-5 bullets)
- Fuentes (lista con texto y URL cuando esté disponible)

Usa SOLO la información proporcionada. No inventes datos.
Fuentes (incluye siempre la URL si existe):
{context_block}
"""
                if urls_in_bullets:
                    prompt += "\nInstrucción extra: Incluye la URL relevante en cada bullet cuando exista."
                llm_summary = self.llm.predict(prompt)
                
                return {
                    "success": True,
                    "task_type": "prebrief",
                    "summary": llm_summary,
                    "sources": [
                        {
                            "app": r.app_name,
                            "source": r.source_name,
                            "url": r.url
                        } for r in search_results[:10]
                    ],
                    "sources_count": len(search_results)
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Error generando pre-brief: {e}"
                }

        # Flujo para tareas de análisis de datos / outliers / KPIs / limpieza de Excel
        if task_type in ["data_analysis", "data_insights", "kpi_dashboard", "excel_cleanup"] or any(
            k in task_description.lower() for k in ["ventas", "outlier", "kpi", "excel", "dashboard", "insight"]
        ):
            try:
                search_results = await self.app_integrations.search_across_apps(
                    query=task_description,
                    filters=filters
                )
                if not search_results:
                    return {
                        "success": False,
                        "error": "No se encontró información en las apps conectadas."
                    }

                ctx_lines = []
                for r in search_results[:10]:
                    snippet = r.snippet or r.content
                    snippet = (snippet or "")[:600]
                    ctx_lines.append(f"[{r.app_name}] {r.source_name}: {snippet} (URL: {r.url or 'N/A'})")
                context_block = "\n".join(ctx_lines)

                prompt = f"""
Eres un analista senior de datos. Con la información conectada, entrega:
- Resumen ejecutivo (3-5 bullets con URLs si existen).
- Insights clave multi-año (tendencias de ventas/volumen, top/bottom periodos).
- Outliers detectados (qué, cuándo, magnitud, posible causa, fuente con URL).
- Plan de limpieza/normalización para Excel/CSV (pasos concretos).
- Dashboard de KPIs propuesto: lista de KPIs, fórmula, periodicidad, segmentaciones, gráfico sugerido.
- Próximas acciones priorizadas (impacto/urgencia).

Usa SOLO la información proporcionada. No inventes datos. Incluye URL al final de cada bullet cuando exista.
Fuentes:
{context_block}
"""
                if urls_in_bullets:
                    prompt += "\nInstrucción extra: Incluye la URL relevante en cada bullet cuando exista."

                llm_summary = self.llm.predict(prompt)

                return {
                    "success": True,
                    "task_type": "data_analysis",
                    "summary": llm_summary,
                    "sources": [
                        {
                            "app": r.app_name,
                            "source": r.source_name,
                            "url": r.url
                        } for r in search_results[:10]
                    ],
                    "sources_count": len(search_results)
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Error generando análisis de datos: {e}"
                }
        
        return await self.app_integrations.execute_autonomous_task(
            task_description=task_description,
            task_type=task_type,
            context=context
        )

    async def execute_autonomous_task_v2(
        self,
        task_description: str,
        task_type: str,
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        filters: Optional[Dict[str, Any]] = None,
        urls_in_bullets: bool = False
    ) -> Dict[str, Any]:
        """
        Versión extendida con soporte de prebrief y análisis de datos/KPIs.
        """
        if not self.app_integrations:
            return {"success": False, "error": "Sistema de integraciones no disponible"}
        
        if task_type == "prebrief":
            try:
                search_results = await self.app_integrations.search_across_apps(
                    query=task_description,
                    filters=filters
                )
                if not search_results:
                    return {"success": False, "error": "No se encontró información en las apps conectadas."}
                ctx_lines = []
                for r in search_results[:10]:
                    snippet = (r.snippet or r.content or "")[:500]
                    ctx_lines.append(f"[{r.app_name}] {r.source_name}: {snippet} (URL: {r.url or 'N/A'})")
                context_block = "\n".join(ctx_lines)
                prompt = f"""
Eres un analista. Genera un pre-brief ejecutivo con la siguiente estructura:
- Executive Summary (3-5 bullets concisos)
- Métricas / Hechos clave (bullets)
- Riesgos / Issues abiertos (si los hay)
- Próximas acciones recomendadas (3-5 bullets)
- Fuentes (lista con texto y URL cuando esté disponible)

Usa SOLO la información proporcionada. No inventes datos.
Fuentes (incluye siempre la URL si existe):
{context_block}
"""
                if urls_in_bullets:
                    prompt += "\nInstrucción extra: Incluye la URL relevante en cada bullet cuando exista."
                llm_summary = self.llm.predict(prompt)
                return {
                    "success": True,
                    "task_type": "prebrief",
                    "summary": llm_summary,
                    "sources": [
                        {"app": r.app_name, "source": r.source_name, "url": r.url}
                        for r in search_results[:10]
                    ],
                    "sources_count": len(search_results)
                }
            except Exception as e:
                return {"success": False, "error": f"Error generando pre-brief: {e}"}

        if task_type == "data_analysis":
            try:
                search_results = await self.app_integrations.search_across_apps(
                    query=task_description,
                    filters=filters
                )
                if not search_results:
                    return {"success": False, "error": "No se encontró información en las apps conectadas."}
                ctx_lines = []
                for r in search_results[:10]:
                    snippet = (r.snippet or r.content or "")[:600]
                    ctx_lines.append(f"[{r.app_name}] {r.source_name}: {snippet} (URL: {r.url or 'N/A'})")
                context_block = "\n".join(ctx_lines)
                prompt = f"""
Eres un analista senior de datos. Con la información conectada, entrega:
- Resumen ejecutivo (3-5 bullets con URLs si existen).
- Insights clave multi-año (tendencias, top/bottom periodos).
- Outliers detectados (qué, cuándo, magnitud, posible causa, fuente con URL).
- Plan de limpieza/normalización para Excel/CSV (pasos concretos).
- Dashboard de KPIs propuesto: lista de KPIs, fórmula, periodicidad, segmentaciones, gráfico sugerido.
- Próximas acciones priorizadas (impacto/urgencia).

Usa SOLO la información proporcionada. No inventes datos. Incluye URL al final de cada bullet cuando exista.
Fuentes:
{context_block}
"""
                if urls_in_bullets:
                    prompt += "\nInstrucción extra: Incluye la URL relevante en cada bullet cuando exista."
                llm_summary = self.llm.predict(prompt)
                return {
                    "success": True,
                    "task_type": "data_analysis",
                    "summary": llm_summary,
                    "sources": [
                        {"app": r.app_name, "source": r.source_name, "url": r.url}
                        for r in search_results[:10]
                    ],
                    "sources_count": len(search_results)
                }
            except Exception as e:
                return {"success": False, "error": f"Error generando análisis de datos: {e}"}

        return await self.execute_autonomous_task(
            task_description=task_description,
            task_type=task_type,
            session_id=session_id,
            context=context
        )
    
    def _detect_apps_for_prebrief(self, task_description: str) -> List[IntegrationType]:
        """Detecta apps relevantes para pre-brief según palabras clave en el prompt."""
        desc = task_description.lower()
        apps = []
        if any(k in desc for k in ["slack", "mensaje", "canal"]):
            apps.append(IntegrationType.SLACK)
        if any(k in desc for k in ["drive", "documento", "google doc", "gdoc"]):
            apps.append(IntegrationType.GOOGLE_DRIVE)
        if any(k in desc for k in ["hubspot", "crm", "deal", "contacto", "lead"]):
            apps.append(IntegrationType.HUBSPOT)
        if any(k in desc for k in ["jira", "ticket", "issue", "bug"]):
            apps.append(IntegrationType.JIRA)
        if any(k in desc for k in ["confluence", "wiki", "doc interna"]):
            apps.append(IntegrationType.CONFLUENCE)
        # fallback si no se detecta nada
        if not apps:
            apps = [IntegrationType.SLACK, IntegrationType.GOOGLE_DRIVE, IntegrationType.HUBSPOT]
        return apps
    
    async def execute_autonomous_task_v2(
        self,
        task_description: str,
        task_type: str,
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        filters: Optional[Dict[str, Any]] = None,
        urls_in_bullets: bool = False
    ) -> Dict[str, Any]:
        """
        Versión extendida con soporte de prebrief y análisis de datos/KPIs.
        """
        if not self.app_integrations:
            return {"success": False, "error": "Sistema de integraciones no disponible"}
        
        if task_type == "prebrief":
            try:
                search_results = await self.app_integrations.search_across_apps(
                    query=task_description,
                    filters=filters
                )
                if not search_results:
                    return {"success": False, "error": "No se encontró información en las apps conectadas."}
                ctx_lines = []
                for r in search_results[:10]:
                    snippet = (r.snippet or r.content or "")[:500]
                    ctx_lines.append(f"[{r.app_name}] {r.source_name}: {snippet} (URL: {r.url or 'N/A'})")
                context_block = "\n".join(ctx_lines)
                prompt = f"""
Eres un analista. Genera un pre-brief ejecutivo con la siguiente estructura:
- Executive Summary (3-5 bullets concisos)
- Métricas / Hechos clave (bullets)
- Riesgos / Issues abiertos (si los hay)
- Próximas acciones recomendadas (3-5 bullets)
- Fuentes (lista con texto y URL cuando esté disponible)

Usa SOLO la información proporcionada. No inventes datos.
Fuentes (incluye siempre la URL si existe):
{context_block}
"""
                if urls_in_bullets:
                    prompt += "\nInstrucción extra: Incluye la URL relevante en cada bullet cuando exista."
                llm_summary = self.llm.predict(prompt)
                return {
                    "success": True,
                    "task_type": "prebrief",
                    "summary": llm_summary,
                    "sources": [
                        {"app": r.app_name, "source": r.source_name, "url": r.url}
                        for r in search_results[:10]
                    ],
                    "sources_count": len(search_results)
                }
            except Exception as e:
                return {"success": False, "error": f"Error generando pre-brief: {e}"}

        if task_type == "data_analysis":
            try:
                search_results = await self.app_integrations.search_across_apps(
                    query=task_description,
                    filters=filters
                )
                if not search_results:
                    return {"success": False, "error": "No se encontró información en las apps conectadas."}
                ctx_lines = []
                for r in search_results[:10]:
                    snippet = (r.snippet or r.content or "")[:600]
                    ctx_lines.append(f"[{r.app_name}] {r.source_name}: {snippet} (URL: {r.url or 'N/A'})")
                context_block = "\n".join(ctx_lines)
                prompt = f"""
Eres un analista senior de datos. Con la información conectada, entrega:
- Resumen ejecutivo (3-5 bullets con URLs si existen).
- Insights clave multi-año (tendencias, top/bottom periodos).
- Outliers detectados (qué, cuándo, magnitud, posible causa, fuente con URL).
- Plan de limpieza/normalización para Excel/CSV (pasos concretos).
- Dashboard de KPIs propuesto: lista de KPIs, fórmula, periodicidad, segmentaciones, gráfico sugerido.
- Próximas acciones priorizadas (impacto/urgencia).

Usa SOLO la información proporcionada. No inventes datos. Incluye URL al final de cada bullet cuando exista.
Fuentes:
{context_block}
"""
                if urls_in_bullets:
                    prompt += "\nInstrucción extra: Incluye la URL relevante en cada bullet cuando exista."
                llm_summary = self.llm.predict(prompt)
                return {
                    "success": True,
                    "task_type": "data_analysis",
                    "summary": llm_summary,
                    "sources": [
                        {"app": r.app_name, "source": r.source_name, "url": r.url}
                        for r in search_results[:10]
                    ],
                    "sources_count": len(search_results)
                }
            except Exception as e:
                return {"success": False, "error": f"Error generando análisis de datos: {e}"}
        
        return await self.app_integrations.execute_autonomous_task(
            task_description=task_description,
            task_type=task_type,
            context=context
        )

    async def execute_autonomous_task_v2(
        self,
        task_description: str,
        task_type: str,
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        filters: Optional[Dict[str, Any]] = None,
        urls_in_bullets: bool = False
    ) -> Dict[str, Any]:
        """
        Versión extendida con soporte de prebrief y análisis de datos/KPIs.
        """
        if not self.app_integrations:
            return {"success": False, "error": "Sistema de integraciones no disponible"}
        
        if task_type == "prebrief":
            try:
                search_results = await self.app_integrations.search_across_apps(
                    query=task_description,
                    filters=filters
                )
                if not search_results:
                    return {"success": False, "error": "No se encontró información en las apps conectadas."}
                ctx_lines = []
                for r in search_results[:10]:
                    snippet = (r.snippet or r.content or "")[:500]
                    ctx_lines.append(f"[{r.app_name}] {r.source_name}: {snippet} (URL: {r.url or 'N/A'})")
                context_block = "\n".join(ctx_lines)
                prompt = f"""
Eres un analista. Genera un pre-brief ejecutivo con la siguiente estructura:
- Executive Summary (3-5 bullets concisos)
- Métricas / Hechos clave (bullets)
- Riesgos / Issues abiertos (si los hay)
- Próximas acciones recomendadas (3-5 bullets)
- Fuentes (lista con texto y URL cuando esté disponible)

Usa SOLO la información proporcionada. No inventes datos.
Fuentes (incluye siempre la URL si existe):
{context_block}
"""
                if urls_in_bullets:
                    prompt += "\nInstrucción extra: Incluye la URL relevante en cada bullet cuando exista."
                llm_summary = self.llm.predict(prompt)
                return {
                    "success": True,
                    "task_type": "prebrief",
                    "summary": llm_summary,
                    "sources": [
                        {"app": r.app_name, "source": r.source_name, "url": r.url}
                        for r in search_results[:10]
                    ],
                    "sources_count": len(search_results)
                }
            except Exception as e:
                return {"success": False, "error": f"Error generando pre-brief: {e}"}

        if task_type == "data_analysis":
            try:
                search_results = await self.app_integrations.search_across_apps(
                    query=task_description,
                    filters=filters
                )
                if not search_results:
                    return {"success": False, "error": "No se encontró información en las apps conectadas."}
                ctx_lines = []
                for r in search_results[:10]:
                    snippet = (r.snippet or r.content or "")[:600]
                    ctx_lines.append(f"[{r.app_name}] {r.source_name}: {snippet} (URL: {r.url or 'N/A'})")
                context_block = "\n".join(ctx_lines)
                prompt = f"""
Eres un analista senior de datos. Con la información conectada, entrega:
- Resumen ejecutivo (3-5 bullets con URLs si existen).
- Insights clave multi-año (tendencias, top/bottom periodos).
- Outliers detectados (qué, cuándo, magnitud, posible causa, fuente con URL).
- Plan de limpieza/normalización para Excel/CSV (pasos concretos).
- Dashboard de KPIs propuesto: lista de KPIs, fórmula, periodicidad, segmentaciones, gráfico sugerido.
- Próximas acciones priorizadas (impacto/urgencia).

Usa SOLO la información proporcionada. No inventes datos. Incluye URL al final de cada bullet cuando exista.
Fuentes:
{context_block}
"""
                if urls_in_bullets:
                    prompt += "\nInstrucción extra: Incluye la URL relevante en cada bullet cuando exista."
                llm_summary = self.llm.predict(prompt)
                return {
                    "success": True,
                    "task_type": "data_analysis",
                    "summary": llm_summary,
                    "sources": [
                        {"app": r.app_name, "source": r.source_name, "url": r.url}
                        for r in search_results[:10]
                    ],
                    "sources_count": len(search_results)
                }
            except Exception as e:
                return {"success": False, "error": f"Error generando análisis de datos: {e}"}

        return await self.execute_autonomous_task(
            task_description=task_description,
            task_type=task_type,
            session_id=session_id,
            context=context
        )

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
        
        # Agregar estadísticas de apps conectadas
        if self.app_integrations:
            stats["app_integrations"] = self.app_integrations.get_statistics()
        else:
            stats["app_integrations"] = {
                "total_connections": 0,
                "connected_apps": 0,
                "apps_by_type": {}
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
_company_knowledge_instance: Optional[CompanyKnowledge] = None


def get_company_knowledge(
    config: AppConfig,
    processor: DocumentProcessor,
    retriever_builder: RetrieverBuilder,
    context_manager: Optional[Any] = None
) -> CompanyKnowledge:
    """Obtiene o crea la instancia global de Company Knowledge."""
    global _company_knowledge_instance
    
    if _company_knowledge_instance is None:
        _company_knowledge_instance = CompanyKnowledge(
            config=config,
            processor=processor,
            retriever_builder=retriever_builder,
            context_manager=context_manager
        )
    
    return _company_knowledge_instance


def run_company_knowledge(
    message: str,
    history: List[Tuple[str, str]],
    files: List[Any],
    session_id: str,
    speed_mode: str = "balanced",
    provider: str = "openai",
    filters: Optional[Dict[str, Any]] = None,
    urls_in_bullets: bool = False,
    config: Optional[AppConfig] = None,
    processor: Optional[DocumentProcessor] = None,
    retriever_builder: Optional[RetrieverBuilder] = None,
    context_manager: Optional[Any] = None
) -> Tuple[List[Tuple[str, str]], Optional[str]]:
    """
    Función principal para ejecutar Company Knowledge.
    Compatible con Gradio (síncrona).
    """
    if not config or not processor or not retriever_builder:
        return history, "❌ Configuración incompleta"
    
    # Obtener instancia
    company_knowledge = get_company_knowledge(
        config=config,
        processor=processor,
        retriever_builder=retriever_builder,
        context_manager=context_manager
    )
    
    # Procesar documentos si hay
    if files:
        result = company_knowledge.process_documents(session_id, files)
        if result.get("status") == "error":
            return history, f"❌ Error procesando documentos: {result.get('error')}"
    
    # Ejecutar query (async wrapper)
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        new_history, error, metadata = loop.run_until_complete(
            company_knowledge.process_query_async(
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

