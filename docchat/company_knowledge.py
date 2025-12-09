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
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

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
            # max_tokens REMOVIDO - dejar que la API decida la longitud (como Enterprise API)
            request_timeout=300  # Timeout más largo para respuestas extensas (como Enterprise API)
        )
        
        # Embeddings para relevancia semántica
        try:
            self.embeddings = OpenAIEmbeddings(
                model=config.embedding_model or "text-embedding-3-small",
                api_key=config.openai_api_key
            )
        except Exception as e:
            print(f"⚠️ [Company Knowledge] No se pudieron inicializar embeddings: {e}")
            self.embeddings = None
        
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
        provider: str = "openai",
        filters: Optional[Dict[str, Any]] = None,
        urls_in_bullets: bool = False
    ) -> Tuple[List[Tuple[str, str]], Optional[str], Dict[str, Any]]:
        """
        Procesa una consulta con todas las capacidades avanzadas.
        Ahora también busca en apps conectadas si están disponibles.
        
        Returns:
            (history, error, metadata): Historial actualizado, error si hay, metadatos
        """
        session = self.initialize_session(session_id)
        
        # NUEVO: Si hay apps conectadas, buscar en ellas primero
        app_results = []
        app_context = ""
        connected_apps = []
        if self.app_integrations:
            connected_apps = self.app_integrations.get_connected_apps()
            if connected_apps:
                print(f"🔍 [Company Knowledge] Buscando en {len(connected_apps)} apps conectadas...")
                try:
                    app_results = await self.app_integrations.search_across_apps(
                        query=message,
                        filters=filters
                    )
                    
                    if app_results:
                        # Preparar contexto de apps
                        ranked_results = self._rank_results_by_relevance_and_recency(
                            query=message,
                            results=app_results,
                            filters=filters
                        )
                        ctx_lines = []
                        for r in ranked_results[:10]:  # Top 10 resultados de apps
                            snippet = (r.snippet or r.content or "")[:400]
                            if urls_in_bullets and r.url:
                                ctx_lines.append(f"[{r.app_name}] {r.source_name}: {snippet} (URL: {r.url})")
                            else:
                                ctx_lines.append(f"[{r.app_name}] {r.source_name}: {snippet}")
                        app_context = "\n\n📱 INFORMACIÓN DE APPS CONECTADAS:\n" + "\n".join(ctx_lines)
                        print(f"✅ [Company Knowledge] Encontrados {len(app_results)} resultados en apps")
                    else:
                        print(f"⚠️ [Company Knowledge] No se encontraron resultados en las apps para la query: {message[:50]}...")
                except Exception as e:
                    print(f"⚠️ [Company Knowledge] Error buscando en apps: {e}")
                    import traceback
                    traceback.print_exc()
        
        # Si no hay documentos pero sí hay resultados de apps, usar solo apps
        if not session["retriever"] and app_results:
            print("📱 [Company Knowledge] Usando solo información de apps conectadas (no hay documentos)")
            # Generar respuesta basada solo en apps
            try:
                # Preparar contexto completo de apps
                ranked_results = self._rank_results_by_relevance_and_recency(
                    query=message,
                    results=app_results,
                    filters=filters
                )
                ctx_lines = []
                sources_list = []
                # Procesar TODOS los resultados, sin límite (máxima calidad)
                # Optimizado para aprovechar context windows grandes (128k OpenAI, 200k Claude)
                total_chars = 0
                max_chars = 500000 if provider == "openai" else 800000  # Claude puede manejar más contexto
                
                for r in ranked_results:
                    # Para PDFs, usar contenido completo (hasta 80,000 caracteres por PDF como Enterprise API)
                    # Para otros, usar snippet más largo
                    if r.content and len(r.content) > 1000:
                        # Es un PDF con contenido completo
                        # Usar hasta 80,000 caracteres por PDF (como Enterprise API Supreme)
                        content_to_use = r.content[:80000]
                        if total_chars + len(content_to_use) <= max_chars:
                            ctx_lines.append(f"=== [{r.app_name}] {r.source_name} ===\n{content_to_use}\n")
                            total_chars += len(content_to_use)
                        else:
                            # Si nos quedamos sin espacio, usar lo que quepa
                            remaining = max_chars - total_chars
                            if remaining > 1000:
                                ctx_lines.append(f"=== [{r.app_name}] {r.source_name} ===\n{content_to_use[:remaining]}\n")
                                total_chars = max_chars
                            break
                    else:
                        # Usar snippet o contenido limitado (más largo para otros tipos)
                        snippet = (r.snippet or r.content or "")[:5000]  # Aumentado a 5000 chars
                        if total_chars + len(snippet) <= max_chars:
                            ctx_lines.append(f"[{r.app_name}] {r.source_name}: {snippet}")
                            total_chars += len(snippet)
                        else:
                            break
                    if r.url:
                        sources_list.append({"app": r.app_name, "source": r.source_name, "url": r.url})
                
                context_block = "\n".join(ctx_lines)
                
                # Generar respuesta con LLM - PROMPT ESTILO ENTERPRISE API SUPREME (máxima calidad)
                prompt = f"""Eres un analista experto de documentos empresariales (nivel consultor senior C-level, estilo McKinsey/Deloitte). 
Analiza en profundidad la información proporcionada y genera resúmenes ejecutivos EXTENSOS, PROFESIONALES y ALTAMENTE ÚTILES.

INFORMACIÓN DE APPS CONECTADAS:
{context_block}

PREGUNTA DEL USUARIO: {message}

INSTRUCCIONES DETALLADAS (ESTILO ENTERPRISE API SUPREME):

1. **RESUMEN EJECUTIVO EXTENSO (6-10 párrafos por documento importante):**
   - Contexto histórico y propósito del documento
   - Ideas principales y argumentos centrales explicados con profundidad
   - Conclusiones y recomendaciones clave con justificación
   - Valor e importancia del contenido para diferentes audiencias
   - Aplicaciones prácticas y relevancia empresarial específica
   - Insights profundos y análisis crítico
   - Conexiones con otros documentos si hay múltiples
   - Implicaciones estratégicas y tácticas

2. **PUNTOS CLAVE DETALLADOS (15-20 puntos por documento importante):**
   - Conceptos fundamentales explicados con ejemplos concretos
   - Hallazgos importantes con contexto y evidencia
   - Recomendaciones específicas y accionables con pasos concretos
   - Insights valiosos para el negocio con casos de uso
   - Metodologías, frameworks o modelos presentados con explicación
   - Ejemplos concretos, estudios de caso o datos mencionados
   - Advertencias, limitaciones o consideraciones importantes
   - Oportunidades de implementación y ROI potencial

3. **ANÁLISIS PROFESIONAL COMPLETO:**
   - Tipo de documento y clasificación precisa (libro académico, whitepaper, informe ejecutivo, etc.)
   - Entidades principales (autores con credenciales, organizaciones, empresas, instituciones)
   - Temas y áreas de conocimiento cubiertas con profundidad
   - Fechas/períodos relevantes y contexto histórico
   - Valor para el negocio con métricas potenciales
   - Aplicaciones prácticas por industria o función
   - Nivel de complejidad y audiencia objetivo

4. **ESTRUCTURA PROFESIONAL:**
   - Organiza por documento cuando hay múltiples (cada uno con su sección completa)
   - Usa títulos claros, subtítulos y secciones bien definidas
   - Incluye referencias a las fuentes en cada punto (ej: "según [App] Nombre del Documento, página X")
   - Usa formato markdown profesional con negritas, listas y citas
   - Sé específico, detallado y evita generalidades
   - Proporciona valor real para la toma de decisiones ejecutivas

5. **LONGITUD Y PROFUNDIDAD MÁXIMA:**
   - Genera resúmenes EXTENSOS (mínimo 1000-2000 palabras por documento importante)
   - Profundiza en los conceptos clave con explicaciones detalladas
   - Explica el "por qué", el "cómo", el "cuándo" y el "dónde", no solo el "qué"
   - Incluye análisis crítico, perspectivas múltiples y contraargumentos cuando sea relevante
   - Proporciona contexto histórico, comparaciones y analogías cuando enriquezcan el análisis
   - Incluye citas directas importantes del documento cuando sean relevantes

6. **CALIDAD ENTERPRISE:**
   - Nivel de detalle equivalente a un informe de consultoría estratégica
   - Análisis que un CEO o C-level podría usar directamente para decisiones
   - Profundidad que permite entender el documento sin leerlo completo
   - Insights accionables con pasos concretos de implementación
   - Consideración de múltiples perspectivas y escenarios

IMPORTANTE:
- Usa SOLO la información proporcionada de las apps
- Sé específico y detallado - evita generalidades completamente
- Proporciona valor real para la toma de decisiones ejecutivas
- Usa lenguaje profesional pero claro (nivel C-level)
- Si hay múltiples documentos, analiza CADA UNO en profundidad completa
- No limites la longitud - genera el análisis más completo posible
- Incluye todos los detalles importantes que encuentres en el contenido

Genera un análisis COMPLETO, EXTENSO y PROFESIONAL de máxima calidad:"""
                
                # Generar respuesta con streaming
                from langchain_core.messages import HumanMessage
                full_response = ""
                
                # Stream tokens en tiempo real
                async for chunk in self.llm.astream([HumanMessage(content=prompt)]):
                    if hasattr(chunk, 'content'):
                        token = chunk.content
                    else:
                        token = str(chunk)
                    full_response += token
                
                # Agregar fuentes al final
                if sources_list:
                    sources_text = "\n\n---\n\n### 📚 Fuentes Consultadas\n\n"
                    for i, src in enumerate(sources_list[:10], 1):
                        app_name = src.get("app", "Unknown")
                        source_name = src.get("source", "Unknown")
                        url = src.get("url", "")
                        if url:
                            sources_text += f"{i}. **[{app_name}]** {source_name} - [🔗 Abrir]({url})\n"
                        else:
                            sources_text += f"{i}. **[{app_name}]** {source_name}\n"
                    full_response += sources_text
                
                new_history = history + [(message, full_response)]
                return new_history, None, {
                    "sources": sources_list,
                    "total_sources": len(sources_list),
                    "apps_searched": len(connected_apps) if connected_apps else 0
                }
            except Exception as e:
                return history, f"❌ Error generando respuesta: {str(e)}", {}
        
        # Si no hay documentos ni resultados de apps, mostrar mensaje apropiado
        if not session["retriever"] and not app_results:
            if connected_apps:
                # Hay apps conectadas pero no se encontraron resultados para esta query
                apps_names = ", ".join([app.app_name for app in connected_apps[:3]])
                if len(connected_apps) > 3:
                    apps_names += f" y {len(connected_apps) - 3} más"
                
                # Generar respuesta informativa aunque no haya resultados
                informative_response = f"""No se encontraron resultados específicos en tus apps conectadas ({apps_names}) para esta pregunta.

**💡 Sugerencias:**
- Intenta reformular la pregunta con palabras clave diferentes
- Verifica que la información que buscas esté disponible en esas apps
- Prueba con una búsqueda más general
- Asegúrate de que los permisos del token permitan acceder a los archivos que buscas

**🔍 Apps conectadas:** {apps_names}

Si crees que debería haber resultados, verifica:
1. Que el token tenga los permisos necesarios (scopes)
2. Que los archivos/documentos existan en las apps
3. Que la búsqueda use términos que aparezcan en el contenido"""
                
                new_history = history + [(message, informative_response)]
                return new_history, None, {
                    "sources": [],
                    "total_sources": 0,
                    "apps_searched": len(connected_apps),
                    "message": "No se encontraron resultados en apps conectadas"
                }
            elif self.app_integrations and self.app_integrations.get_connected_apps():
                return history, "⚠️ No hay documentos procesados. Puedes cargar documentos o hacer preguntas sobre tus apps conectadas.", {}
            else:
                return history, "⚠️ No hay documentos procesados. Carga documentos primero o conecta apps en 'Conectar Apps'.", {}
        
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
        
        # 8. Buscar en apps conectadas si están disponibles (combinar con documentos)
        if self.app_integrations and app_results:
            # Ya tenemos resultados de apps de antes, agregarlos al contexto
            conversation_context += app_context
            print(f"✅ [Company Knowledge] Combinando {len(app_results)} resultados de apps con documentos")
        elif self.app_integrations:
            # Buscar en apps ahora si no lo hicimos antes
            connected_apps = self.app_integrations.get_connected_apps()
            if connected_apps:
                try:
                    app_results = await self.app_integrations.search_across_apps(
                        query=message,
                        filters=filters
                    )
                    if app_results:
                        ranked_results = self._rank_results_by_relevance_and_recency(
                            query=message,
                            results=app_results,
                            filters=filters
                        )
                        ctx_lines = []
                        for r in ranked_results[:5]:  # Top 5 para no saturar
                            snippet = (r.snippet or r.content or "")[:300]
                            ctx_lines.append(f"[{r.app_name}] {r.source_name}: {snippet}")
                        app_context = "\n\n📱 INFORMACIÓN DE APPS CONECTADAS:\n" + "\n".join(ctx_lines)
                        conversation_context += app_context
                        print(f"✅ [Company Knowledge] Agregados {len(app_results)} resultados de apps al contexto")
                except Exception as e:
                    print(f"⚠️ [Company Knowledge] Error buscando en apps: {e}")
        
        # 9. Usar MCP potenciado para buscar en sistemas externos si es necesario
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
    
<<<<<<< HEAD
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

    async def execute_autonomous_task_v2(
        self,
        task_description: str,
        task_type: str,
        filters: Optional[Dict[str, Any]] = None,
        urls_in_bullets: bool = False
    ) -> Dict[str, Any]:
        """
        Versión mejorada de execute_autonomous_task con:
        - Multi-source synthesis con resolución de conflictos
        - Ranking por recencia y calidad
        - Manejo de queries ambiguas
        - Citations mejoradas con links directos
        """
        if not self.app_integrations:
            return {"success": False, "error": "Sistema de integraciones no disponible"}

        # Extraer query de búsqueda
        search_query = self._extract_search_query_from_task(task_description)
        
        # Buscar en todas las apps conectadas
        app_results = await self.app_integrations.search_across_apps(
            query=search_query,
            filters=filters
        )

        if not app_results:
            return {"success": False, "error": "No se encontró información en las apps conectadas."}

        # Aplicar ranking inteligente (relevancia semántica + recencia + calidad)
        ranked_results = self._rank_results_by_relevance_and_recency(
            query=search_query,
            results=app_results,
            filters=filters
        )
        
        # Detectar y resolver conflictos entre fuentes
        conflict_analysis = self._detect_conflicts(ranked_results)
        
        # Preparar contexto para LLM con información de conflictos
        # Usar contenido completo de PDFs (hasta 80k chars) para máxima calidad
        ctx_lines = []
        search_status = []  # Para sidebar en tiempo real
        total_chars = 0
        max_chars = 500000 if hasattr(self, 'provider') and self.provider == "claude" else 500000
        
        for r in ranked_results:  # TODOS los resultados, sin límite
            app_display = f"[{r.app_name}]"
            search_status.append({
                "app": r.app_name,
                "source": r.source_name,
                "status": "found"
            })
            
            # Para PDFs, usar contenido completo (hasta 80k chars)
            if r.content and len(r.content) > 1000:
                content_to_use = r.content[:80000]  # Hasta 80k chars por PDF
                if total_chars + len(content_to_use) <= max_chars:
                    if urls_in_bullets and r.url:
                        ctx_lines.append(f"{app_display} {r.source_name} (URL: {r.url}):\n{content_to_use}\n")
                    else:
                        ctx_lines.append(f"{app_display} {r.source_name}:\n{content_to_use}\n")
                    total_chars += len(content_to_use)
                else:
                    remaining = max_chars - total_chars
                    if remaining > 1000:
                        ctx_lines.append(f"{app_display} {r.source_name}:\n{r.content[:remaining]}\n")
                        total_chars = max_chars
                    break
            else:
                # Para otros tipos, usar snippet más largo
                snippet = (r.snippet or r.content or "")[:5000]
                if total_chars + len(snippet) <= max_chars:
                    if urls_in_bullets and r.url:
                        ctx_lines.append(f"{app_display} {r.source_name} (URL: {r.url}): {snippet}")
                    else:
                        ctx_lines.append(f"{app_display} {r.source_name}: {snippet}")
                    total_chars += len(snippet)
                else:
                    break
        
        context_block = "\n".join(ctx_lines)
        
        # Agregar información de conflictos si existen
        conflict_context = ""
        if conflict_analysis.get("has_conflicts"):
            conflict_context = f"\n\n⚠️ CONFLICTOS DETECTADOS:\n"
            for conflict in conflict_analysis.get("conflicts", [])[:3]:
                conflict_context += f"- {conflict['description']}\n"
            conflict_context += "\nPor favor, presenta perspectivas balanceadas y destaca las diferencias.\n"

        if task_type == "prebrief":
            # Preparar lista de fuentes agrupadas por app para el formato de citations
            sources_by_app = {}
            for r in ranked_results[:15]:
                app = r.app_name
                if app not in sources_by_app:
                    sources_by_app[app] = []
                sources_by_app[app].append({
                    "name": r.source_name,
                    "url": r.url
                })
            
            sources_summary = "\n".join([
                f"- **{app}**: {len(sources)} fuente(s) - {', '.join([s['name'] for s in sources[:3]])}"
                for app, sources in list(sources_by_app.items())[:5]
            ])
            
            prompt = f"""
Eres un asistente experto en preparar pre-briefs ejecutivos estilo ChatGPT Enterprise Company Knowledge.

Genera un pre-brief profesional y detallado basado en la información de múltiples fuentes conectadas.

FORMATO REQUERIDO (EXACTAMENTE como ChatGPT Enterprise - ver ejemplo real abajo):

## Executive summary

[Un párrafo fluido de 3-5 oraciones que resume los hallazgos más importantes. DEBE incluir métricas específicas cuando estén disponibles: porcentajes exactos (+42%), números concretos, fechas específicas, comparaciones temporales (vs September, vs Q3 baseline). 

Ejemplo exacto del formato esperado:
"The October campaign outperformed benchmarks for engagement and conversion, setting a strong baseline for Q4 growth initiatives. The campaign exceeded engagement targets, driving a +42% lift in new leads and a 3-point increase in feature adoption compared to September. Sentiment in customer channels shifted positive following the 10/24 patch release, while conversion metrics stabilized above the Q3 baseline."]

## Key insights

[Bullets con insights clave. Cada bullet DEBE:
- Incluir métricas específicas cuando estén disponibles (números exactos, porcentajes, fechas)
- Contexto temporal (Week 2, month-over-month, compared to X)
- Referencias a eventos específicos (10/10 email, 10/24 patch release)
- Impacto cuantificado cuando sea posible (+18% month-over-month)

Formato de ejemplo exacto:
- Peak engagement: Week 2 (aligned with 10/10 email)
- Retention impact: +18% month-over-month
- Conversion metrics: 3-point increase vs September baseline
- Feature adoption: +42% lift in new leads

Agrega más bullets con insights clave encontrados en las fuentes, siempre con métricas específicas cuando estén disponibles.]

## Risks / Issues (si aplica)

[Si hay riesgos o issues identificados en las fuentes, listarlos aquí con detalles específicos. Si no hay, OMITIR completamente esta sección]

## Next actions

[3-5 acciones recomendadas basadas en los insights. Cada acción debe ser específica, accionable y con contexto temporal cuando aplique]

---

**Fuentes consultadas:** {len(ranked_results)} fuentes de {len(sources_by_app)} apps
{sources_summary}

INSTRUCCIONES CRÍTICAS:
1. USA SOLO la información proporcionada en las fuentes. NO inventes datos ni métricas.
2. Incluye métricas específicas (números exactos, porcentajes, fechas) SOLO cuando estén disponibles en las fuentes.
3. Si encuentras información contradictoria, presenta ambas perspectivas de forma balanceada.
4. Si no hay una respuesta clara, explica la ambigüedad y qué información falta.
5. Prioriza información más reciente cuando sea relevante.
6. Formatea las métricas de forma destacada (ej: "+42% lift", "+18% MoM", "3-point increase", "Week 2").
7. Incluye referencias a las fuentes cuando sea relevante (ej: "según [App] Source Name").
8. El Executive Summary debe ser un párrafo fluido y continuo, NO bullets.
9. Los Key Insights deben ser bullets concisos con métricas específicas.
10. Si la tarea menciona "campaign results", "customer feedback", "company performance", busca métricas de rendimiento, KPIs, y datos cuantitativos en las fuentes.

{conflict_context}

Información de las apps conectadas:
{context_block}

Tarea original: {task_description}

Genera el pre-brief ahora siguiendo EXACTAMENTE el formato especificado arriba.
"""
            from langchain_core.messages import HumanMessage
            response_obj = self.llm.invoke([HumanMessage(content=prompt)])
            llm_response = response_obj.content if hasattr(response_obj, 'content') else str(response_obj)
            
            # Formatear respuesta final con citations mejoradas
            formatted_response = llm_response
            
            # Agrupar fuentes por app para el formato final
            sources_by_app_final = {}
            for r in ranked_results[:20]:
                app = r.app_name
                if app not in sources_by_app_final:
                    sources_by_app_final[app] = []
                sources_by_app_final[app].append({
                    "name": r.source_name,
                    "url": r.url,
                    "snippet": (r.snippet or r.content or "")[:100]
                })
            
            # Agregar sección de fuentes al final con formato mejorado
            if ranked_results:
                formatted_response += "\n\n---\n\n### 📚 Fuentes Consultadas\n\n"
                
                # Formatear como cards/badges
                for app, sources in list(sources_by_app_final.items())[:10]:
                    formatted_response += f"**{app}** ({len(sources)} fuente{'s' if len(sources) > 1 else ''})\n"
                    for src in sources[:5]:  # Top 5 por app
                        if src["url"]:
                            formatted_response += f"- [{src['name']}]({src['url']})"
                        else:
                            formatted_response += f"- {src['name']}"
                        if src["snippet"]:
                            formatted_response += f" — {src['snippet']}..."
                        formatted_response += "\n"
                    if len(sources) > 5:
                        formatted_response += f"- ... y {len(sources) - 5} fuente{'s' if len(sources) - 5 > 1 else ''} más\n"
                    formatted_response += "\n"
            
            return {
                "success": True,
                "task_type": "prebrief",
                "prebrief_summary": formatted_response,
                "sources": [{"app": r.app_name, "source": r.source_name, "url": r.url} for r in ranked_results if r.url],
                "search_status": search_status,
                "conflicts_detected": conflict_analysis.get("has_conflicts", False),
                "total_sources": len(ranked_results),
                "sources_by_app": sources_by_app_final
            }
        elif task_type == "email_response" or task_type == "auto_reply":
            # Tarea especial: Responder emails automáticamente
            return await self._task_email_response_v2(
                task_description=task_description,
                ranked_results=ranked_results,
                filters=filters
            )
        elif task_type == "data_analysis":
            prompt = f"""
            Eres un analista de Business Intelligence experto. Tu tarea es analizar los datos proporcionados
            de múltiples fuentes conectadas y generar un reporte profesional con insights clave, detección de KPIs,
            análisis de tendencias y outliers, y recomendaciones accionables.
            
            INSTRUCCIONES ESPECIALES:
            1. Si encuentras datos contradictorios, identifica las discrepancias y explica posibles causas.
            2. Prioriza datos más recientes para análisis de tendencias.
            3. Si no hay suficiente información para un análisis completo, indica qué datos faltan.
            4. Incluye URLs de las fuentes en los bullets cuando aplique.
            
            {conflict_context}
            
            Estructura tu respuesta de la siguiente manera:

            ## 📊 Reporte de Análisis de Datos y KPIs

            ### 📝 Resumen Ejecutivo
            [Un resumen conciso de los hallazgos más importantes.]

            ### 📈 KPIs Clave Identificados y Análisis
            [Lista de KPIs relevantes detectados automáticamente en los datos, con su valor, tendencia y una breve explicación.
            Ej: "MRR: $X (↑ 8.2% en 30 días) - Impulsado por nuevas ventas orgánicas."]

            ### 📉 Tendencias, Patrones y Outliers
            [Identifica tendencias significativas (crecimiento, decrecimiento), patrones recurrentes y cualquier anomalía o "outlier"
            inesperado en los datos, explicando su posible causa o implicación.
            Ej: "Las cancelaciones subieron 12% en el último mes, lo que podría indicar un problema de onboarding reciente."]

            ### 🛠️ Plan de Limpieza y Normalización de Datos (si aplica)
            [Si se detectan inconsistencias o problemas de calidad de datos, propone un plan para limpiarlos y normalizarlos.]

            ### 💡 Propuesta de Dashboard de KPIs
            [Sugiere un dashboard con los KPIs más críticos, incluyendo:
            - Métrica: [Nombre del KPI]
            - Fórmula: [Cómo se calcula]
            - Periodicidad: [Diario/Semanal/Mensual/Trimestral]
            - Segmentación sugerida: [Por producto, región, cliente, etc.]
            - Gráfico sugerido: [Líneas, barras, pastel, etc.]
            ]

            ### 🚀 Próximas Acciones y Recomendaciones Estratégicas
            [Recomendaciones de negocio concretas y accionables, estilo consultor, para mejorar los resultados basados en el análisis.
            Ej: "Basado en los datos de tráfico y conversiones, la estrategia más rentable es escalar Google Ads un 20%
            mientras optimizas la landing page X con un test A/B."]

            Información de las apps conectadas:
            {context_block}

            Tarea original: {task_description}
            """
            from langchain_core.messages import HumanMessage
            response_obj = self.llm.invoke([HumanMessage(content=prompt)])
            llm_response = response_obj.content if hasattr(response_obj, 'content') else str(response_obj)
            return {
                "success": True,
                "task_type": "data_analysis",
                "summary": llm_response,
                "sources": [{"app": r.app_name, "source": r.source_name, "url": r.url} for r in ranked_results if r.url],
                "search_status": search_status,
                "conflicts_detected": conflict_analysis.get("has_conflicts", False),
                "total_sources": len(ranked_results)
            }
        elif task_type == "email_response" or task_type == "auto_reply":
            # Tarea especial: Responder emails automáticamente
            return await self._task_email_response_v2(
                task_description=task_description,
                ranked_results=ranked_results,
                filters=filters
            )
        else:
            return {"success": False, "error": f"Tipo de tarea autónoma no soportado: {task_type}"}
    
    async def _task_email_response_v2(
        self,
        task_description: str,
        ranked_results: List[Any],
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Tarea avanzada: Responder emails automáticamente de forma inteligente.
        
        Proceso:
        1. Filtra emails de Gmail de los resultados
        2. Analiza cada email con LLM
        3. Genera respuesta personalizada usando LLM
        4. Retorna respuestas listas para revisar y enviar
        """
        from .company_knowledge_integrations import IntegrationType
        
        if not self.app_integrations:
            return {"success": False, "error": "Sistema de integraciones no disponible"}
        
        # Filtrar solo resultados de Gmail
        gmail_results = [r for r in ranked_results if r.app_type == IntegrationType.GMAIL]
        
        if not gmail_results:
            return {
                "success": False,
                "error": "No se encontraron emails de Gmail. Busca emails primero con una pregunta sobre tus emails."
            }
        
        # Buscar conexión de Gmail
        gmail_connection = None
        for conn in self.app_integrations.connections.values():
            if conn.app_type == IntegrationType.GMAIL and conn.status == "connected":
                gmail_connection = conn
                break
        
        if not gmail_connection:
            return {
                "success": False,
                "error": "No hay conexión de Gmail activa. Conecta Gmail primero en 'Conectar Apps'."
            }
        
        token = gmail_connection.credentials.get("token") or gmail_connection.credentials.get("access_token")
        if not token:
            return {
                "success": False,
                "error": "Token de Gmail no disponible. Reconecta Gmail."
            }
        
        # Extraer parámetros de la tarea
        task_lower = task_description.lower()
        import re
        numbers = re.findall(r'\d+', task_description)
        max_emails = min(int(numbers[0]), 50) if numbers else min(len(gmail_results), 10)  # Máximo 50 por seguridad
        
        # Limitar cantidad de emails
        emails_to_respond = gmail_results[:max_emails]
        
        # Generar respuestas usando LLM
        responses = []
        errors = []
        
        for email_result in emails_to_respond:
            try:
                metadata = email_result.metadata
                subject = metadata.get("subject", "Sin asunto")
                sender = metadata.get("from", "")
                email_content = email_result.content
                
                # Extraer dirección de email del remitente
                email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', sender)
                sender_email = email_match.group(0) if email_match else sender
                
                if not sender_email or "@" not in sender_email:
                    errors.append(f"Email inválido para {subject}: {sender}")
                    continue
                
                # Generar respuesta usando LLM
                from langchain_core.messages import HumanMessage
                
                response_prompt = f"""Eres un asistente profesional de email empresarial de máxima calidad.

EMAIL ORIGINAL A RESPONDER:
Asunto: {subject}
De: {sender_email}
Contenido:
{email_content[:3000]}

INSTRUCCIONES DEL USUARIO:
{task_description}

GENERA UNA RESPUESTA PROFESIONAL que:
1. Responda directamente a las preguntas o solicitudes del email original
2. Siga EXACTAMENTE las instrucciones específicas del usuario
3. Sea concisa pero completa (2-4 párrafos)
4. Mantenga un tono profesional y empresarial
5. Incluya información relevante cuando sea apropiado
6. Sea específica y accionable
7. NO inventes información que no esté disponible

IMPORTANTE:
- Responde SOLO con el texto del email (sin "Asunto:", "Para:", etc.)
- NO incluyas saludos genéricos a menos que sea necesario
- Sé directo y profesional
- Si el email original tiene preguntas específicas, respóndelas todas

RESPUESTA:"""
                
                # Generar respuesta con LLM
                response_obj = self.llm.invoke([HumanMessage(content=response_prompt)])
                response_body = response_obj.content if hasattr(response_obj, 'content') else str(response_obj)
                
                # Limpiar respuesta (remover posibles prefijos)
                response_body = response_body.strip()
                if response_body.startswith("Respuesta:"):
                    response_body = response_body.replace("Respuesta:", "").strip()
                
                responses.append({
                    "email_id": email_result.source_id,
                    "to": sender_email,
                    "subject": f"Re: {subject}",
                    "body": response_body,
                    "original_subject": subject,
                    "original_from": sender,
                    "status": "ready_to_send",
                    "gmail_url": email_result.url
                })
                
            except Exception as e:
                import traceback
                traceback.print_exc()
                errors.append(f"Error procesando email {email_result.source_id}: {str(e)}")
                continue
        
        return {
            "success": True,
            "task_type": "email_response",
            "emails_found": len(gmail_results),
            "emails_processed": len(emails_to_respond),
            "responses_generated": len(responses),
            "responses": responses,
            "errors": errors,
            "gmail_token_available": bool(token),
            "message": f"✅ Generadas {len(responses)} respuestas profesionales. Listas para revisar y enviar."
        }
    
    def _extract_search_query_from_task(self, task_description: str) -> str:
        """Extrae términos de búsqueda de la descripción de la tarea."""
        # Mejorar extracción de términos clave para búsquedas más precisas
        desc_lower = task_description.lower()
        
        # Extraer palabras clave relevantes
        keywords = []
        
        # Detectar meses/períodos temporales
        months = ["january", "february", "march", "april", "may", "june", 
                  "july", "august", "september", "october", "november", "december",
                  "enero", "febrero", "marzo", "abril", "mayo", "junio",
                  "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
        for month in months:
            if month in desc_lower:
                keywords.append(month)
        
        # Detectar términos de negocio
        business_terms = ["campaign", "campaña", "performance", "rendimiento", 
                         "customer feedback", "feedback", "comentarios",
                         "results", "resultados", "metrics", "métricas",
                         "kpi", "growth", "crecimiento", "revenue", "ingresos",
                         "conversion", "conversión", "engagement", "compromiso"]
        for term in business_terms:
            if term in desc_lower:
                keywords.append(term)
        
        # Si hay keywords específicos, usarlos; sino usar descripción completa
        if keywords:
            return " ".join(keywords) + " " + task_description
        return task_description
    
    async def _should_use_company_knowledge(
        self,
        message: str,
        history: List[Tuple[str, str]]
    ) -> bool:
        """
        Auto-detecta si una pregunta requiere búsqueda en apps conectadas.
        Usa LLM para determinar si la pregunta es sobre datos empresariales.
        
        Returns:
            True si debería buscar en apps, False si no
        """
        # Si no hay apps conectadas, no usar
        if not self.app_integrations:
            return False
        
        connected_apps = self.app_integrations.get_connected_apps()
        if not connected_apps:
            return False
        
        # Preguntas que claramente NO requieren apps (respuestas rápidas)
        simple_questions = [
            "hola", "hello", "hi", "gracias", "thanks",
            "qué es", "what is", "explica", "explain"
        ]
        message_lower = message.lower().strip()
        if any(message_lower.startswith(q) for q in simple_questions) and len(message) < 50:
            return False
        
        # Usar LLM para detección inteligente
        try:
            # Construir contexto de apps disponibles
            app_names = [app.app_name for app in connected_apps[:5]]
            apps_context = ", ".join(app_names)
            
            prompt = f"""Analiza esta pregunta del usuario y determina si requiere buscar información en aplicaciones empresariales conectadas.

APPS DISPONIBLES: {apps_context}

PREGUNTA: {message}

HISTORIAL RECIENTE:
{chr(10).join([f"Usuario: {h[0]}" for h in history[-2:]]) if history else "Ninguno"}

INSTRUCCIONES:
- Responde SOLO con "SI" o "NO"
- Responde "SI" si la pregunta:
  * Pide información específica de la empresa (ej: "¿Qué se discutió en Slack?", "Muéstrame documentos de Q4")
  * Requiere datos actuales de apps conectadas (ej: "Contactos de HubSpot", "Issues de Jira")
  * Necesita búsqueda en documentos empresariales (ej: "Busca en Drive", "Revisa emails")
  * Es sobre métricas, KPIs, o datos de negocio
- Responde "NO" si la pregunta:
  * Es general/conceptual (ej: "¿Qué es un CRM?", "Explica machine learning")
  * No requiere datos específicos de apps
  * Es una conversación casual sin necesidad de datos

RESPUESTA:"""
            
            from langchain_core.messages import HumanMessage
            response_obj = self.llm.invoke([HumanMessage(content=prompt)])
            response = response_obj.content if hasattr(response_obj, 'content') else str(response_obj)
            response_clean = response.strip().upper()
            
            # Detectar respuesta positiva
            if "SI" in response_clean or "YES" in response_clean or "TRUE" in response_clean:
                return True
            elif "NO" in response_clean or "FALSE" in response_clean:
                return False
            else:
                # Si no está claro, usar heurística de palabras clave
                company_keywords = [
                    "slack", "drive", "hubspot", "salesforce", "jira", "confluence",
                    "github", "gitlab", "linear", "asana", "clickup", "intercom",
                    "documento", "email", "mensaje", "canal", "contacto", "deal",
                    "issue", "ticket", "proyecto", "tarea", "reunión", "meeting",
                    "kpi", "métrica", "dato", "reporte", "análisis", "performance"
                ]
                message_lower = message.lower()
                return any(keyword in message_lower for keyword in company_keywords)
                
        except Exception as e:
            print(f"⚠️ [Company Knowledge] Error en auto-detección: {e}")
            # Fallback: usar heurística de palabras clave
            company_keywords = [
                "slack", "drive", "hubspot", "salesforce", "jira", "confluence",
                "github", "gitlab", "linear", "asana", "clickup", "intercom",
                "documento", "email", "mensaje", "canal", "contacto", "deal"
            ]
            message_lower = message.lower()
            return any(keyword in message_lower for keyword in company_keywords)
    
    def _rank_results_by_relevance_and_recency(
        self,
        query: str,
        results: List[Any],
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Any]:
        """
        Ranking OPTIMIZADO: Combina relevancia semántica + recencia.
        Usa embeddings para calcular similitud semántica con la query.
        
        Returns:
            Lista de resultados ordenados por relevancia + recencia
        """
        from datetime import datetime
        import numpy as np
        
        if not results:
            return []
        
        # Si no hay embeddings, usar ranking básico
        if not self.embeddings:
            return self._rank_results_by_recency_and_quality(results, filters)
        
        try:
            # 1. Calcular embeddings de la query
            query_embedding = self.embeddings.embed_query(query)
            
            # 2. Calcular scores combinados (relevancia semántica + recencia)
            scored_results = []
            
            for result in results:
                # Score base de relevancia semántica
                semantic_score = 0.5  # Default
                
                # Calcular similitud semántica con el contenido del resultado
                result_text = (result.snippet or result.content or result.source_name or "").strip()
                if result_text:
                    try:
                        result_embedding = self.embeddings.embed_query(result_text[:500])  # Limitar para eficiencia
                        
                        # Calcular cosine similarity
                        query_vec = np.array(query_embedding)
                        result_vec = np.array(result_embedding)
                        
                        # Normalizar vectores
                        query_norm = np.linalg.norm(query_vec)
                        result_norm = np.linalg.norm(result_vec)
                        
                        if query_norm > 0 and result_norm > 0:
                            cosine_sim = np.dot(query_vec, result_vec) / (query_norm * result_norm)
                            semantic_score = float(cosine_sim)
                            # Normalizar a 0-1 (cosine similarity ya está en -1 a 1, pero ajustamos a 0-1)
                            semantic_score = (semantic_score + 1) / 2
                    except Exception as e:
                        print(f"⚠️ [Company Knowledge] Error calculando embedding: {e}")
                        # Usar score de relevancia del resultado si existe
                        semantic_score = result.relevance_score or 0.5
                else:
                    # Si no hay texto, usar score de relevancia del resultado
                    semantic_score = result.relevance_score or 0.5
                
                # Score de recencia (0-1)
                recency_score = 0.0
                if hasattr(result, 'metadata') and result.metadata:
                    modified = result.metadata.get("modified") or result.metadata.get("timestamp")
                    if modified:
                        try:
                            if isinstance(modified, str):
                                from dateutil import parser
                                mod_date = parser.parse(modified)
                            else:
                                mod_date = modified
                            
                            days_ago = (datetime.now() - mod_date.replace(tzinfo=None)).days
                            
                            # Función exponencial para recencia (más reciente = mayor score)
                            if days_ago <= 7:
                                recency_score = 1.0  # Muy reciente
                            elif days_ago <= 30:
                                recency_score = 0.7  # Reciente
                            elif days_ago <= 90:
                                recency_score = 0.4  # Moderadamente reciente
                            elif days_ago <= 180:
                                recency_score = 0.2  # Antiguo
                            else:
                                recency_score = 0.1  # Muy antiguo
                        except:
                            pass
                
                # Score de calidad (0-1)
                quality_score = 0.0
                if result.url:
                    quality_score += 0.2  # Fuente verificable
                if result.snippet and len(result.snippet) > 100:
                    quality_score += 0.1  # Snippet detallado
                if result.app_name:
                    quality_score += 0.1  # Tiene app identificada
                quality_score = min(quality_score, 1.0)
                
                # Score combinado: 60% relevancia semántica + 30% recencia + 10% calidad
                combined_score = (
                    0.6 * semantic_score +  # PESO PRINCIPAL: Relevancia semántica
                    0.3 * recency_score +    # PESO SECUNDARIO: Recencia
                    0.1 * quality_score      # PESO MENOR: Calidad
                )
                
                scored_results.append((combined_score, semantic_score, recency_score, result))
            
            # Ordenar por score combinado (descendente)
            scored_results.sort(key=lambda x: x[0], reverse=True)
            
            # Log para debugging
            if scored_results:
                top_score = scored_results[0][0]
                top_semantic = scored_results[0][1]
                top_recency = scored_results[0][2]
                print(f"📊 [Company Knowledge] Top result: score={top_score:.3f} (semantic={top_semantic:.3f}, recency={top_recency:.3f})")
            
            return [result for _, _, _, result in scored_results]
            
        except Exception as e:
            print(f"⚠️ [Company Knowledge] Error en ranking mejorado: {e}, usando ranking básico")
            return self._rank_results_by_recency_and_quality(results, filters)
    
    def _rank_results_by_recency_and_quality(
        self,
        results: List[Any],
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Any]:
        """
        Ranking básico por recencia y calidad (fallback).
        Basado en el artículo: "ranking sources by recency and quality"
        """
        from datetime import datetime, timedelta
        
        # Obtener días de filtro
        days = filters.get("days") if filters else None
        
        # Calcular scores combinados
        scored_results = []
        for result in results:
            score = result.relevance_score or 0.5
            
            # Bonus por recencia si hay metadata de fecha
            if hasattr(result, 'metadata') and result.metadata:
                modified = result.metadata.get("modified") or result.metadata.get("timestamp")
                if modified:
                    try:
                        if isinstance(modified, str):
                            # Parsear fecha
                            from dateutil import parser
                            mod_date = parser.parse(modified)
                        else:
                            mod_date = modified
                        
                        # Calcular días desde modificación
                        days_ago = (datetime.now() - mod_date.replace(tzinfo=None)).days
                        
                        # Bonus: más reciente = mayor score
                        if days_ago <= 7:
                            score += 0.3  # Muy reciente
                        elif days_ago <= 30:
                            score += 0.2  # Reciente
                        elif days_ago <= 90:
                            score += 0.1  # Moderadamente reciente
                    except:
                        pass
            
            # Bonus por tener URL (fuente verificable)
            if result.url:
                score += 0.1
            
            # Bonus por tener snippet detallado
            if result.snippet and len(result.snippet) > 100:
                score += 0.05
            
            scored_results.append((score, result))
        
        # Ordenar por score
        scored_results.sort(key=lambda x: x[0], reverse=True)
        
        return [result for _, result in scored_results]
    
    def _detect_conflicts(self, results: List[Any]) -> Dict[str, Any]:
        """
        Detecta conflictos entre fuentes.
        Basado en: "can run multiple searches to resolve conflicting details"
        """
        conflicts = []
        
        # Agrupar resultados por tema/sujeto similar
        # Simplificado: buscar resultados con contenido similar pero información diferente
        
        # Buscar números contradictorios (ej: diferentes métricas)
        numeric_values = {}
        for result in results:
            import re
            numbers = re.findall(r'\$[\d,]+|[\d,]+%|[\d,]+\.\d+', result.content or result.snippet or "")
            for num in numbers:
                key = num
                if key not in numeric_values:
                    numeric_values[key] = []
                numeric_values[key].append({
                    "source": result.source_name,
                    "app": result.app_name,
                    "value": num
                })
        
        # Detectar discrepancias en valores numéricos
        for value, sources in numeric_values.items():
            if len(sources) > 1:
                # Verificar si hay variación significativa
                unique_sources = set(s["source"] for s in sources)
                if len(unique_sources) > 1:
                    conflicts.append({
                        "type": "numeric_discrepancy",
                        "description": f"Diferentes valores reportados para {value} en {len(unique_sources)} fuentes",
                        "sources": sources
                    })
        
        # Buscar afirmaciones contradictorias (simplificado)
        positive_keywords = ["éxito", "crecimiento", "aumento", "mejora", "positivo", "bueno"]
        negative_keywords = ["fallo", "decrecimiento", "disminución", "problema", "negativo", "malo"]
        
        positive_results = []
        negative_results = []
        
        for result in results:
            content_lower = (result.content or result.snippet or "").lower()
            if any(kw in content_lower for kw in positive_keywords):
                positive_results.append(result)
            if any(kw in content_lower for kw in negative_keywords):
                negative_results.append(result)
        
        if positive_results and negative_results:
            conflicts.append({
                "type": "sentiment_conflict",
                "description": "Se encontraron perspectivas positivas y negativas sobre el mismo tema",
                "positive_sources": [r.source_name for r in positive_results[:3]],
                "negative_sources": [r.source_name for r in negative_results[:3]]
            })
        
        return {
            "has_conflicts": len(conflicts) > 0,
            "conflicts": conflicts,
            "total_conflicts": len(conflicts)
        }
    
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
):
    """
    Función principal para ejecutar Company Knowledge con streaming.
    Compatible con Gradio (devuelve generador para streaming).
    """
    if not config or not processor or not retriever_builder:
        yield history, "❌ Configuración incompleta", None
        return
    
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
            yield history, f"❌ Error procesando documentos: {result.get('error')}", None
            return
    
    # Ejecutar query con streaming
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Crear generador para streaming
        response_chunks = []
        current_history = history.copy()
        
        async def stream_response():
            nonlocal response_chunks, current_history
            full_response = ""
            
            # Procesar query con streaming
            async for chunk in company_knowledge.process_query_async_stream(
                session_id=session_id,
                message=message,
                history=history,
                speed_mode=speed_mode,
                provider=provider,
                filters=filters,
                urls_in_bullets=urls_in_bullets
            ):
                if isinstance(chunk, tuple):
                    # Es un update de history
                    current_history = chunk[0]
                    error = chunk[1]
                    metadata = chunk[2] if len(chunk) > 2 else {}
                    yield current_history, error, metadata
                else:
                    # Es un token de respuesta
                    full_response += chunk
                    current_history = history + [(message, full_response)]
                    yield current_history, None, {}
        
        # Ejecutar streaming usando loop.run_until_complete
        async_gen = stream_response()
        try:
            while True:
                try:
                    # Usar run_until_complete para obtener el siguiente valor del async generator
                    result = loop.run_until_complete(async_gen.__anext__())
                    yield result
                except StopAsyncIteration:
                    break
        finally:
            loop.close()
    except Exception as e:
        yield history, f"❌ Error: {str(e)}", None

