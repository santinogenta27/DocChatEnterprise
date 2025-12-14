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
        urls_in_bullets: bool = False,
        sidebar_callback: Optional[callable] = None
    ) -> Tuple[List[Tuple[str, str]], Optional[str], Dict[str, Any]]:
        """
        Procesa una consulta con todas las capacidades avanzadas.
        Ahora también busca en apps conectadas si están disponibles.
        
        Returns:
            (history, error, metadata): Historial actualizado, error si hay, metadatos
        """
        session = self.initialize_session(session_id)
        
        # OPTIMIZACIÓN 1: Búsqueda multi-fuente con streaming en tiempo real
        app_results = []
        app_context = ""
        connected_apps = []
        search_status = []  # Para sidebar en tiempo real
        results_by_app = {}  # Para tracking de resultados por app
        
        if self.app_integrations:
            connected_apps = self.app_integrations.get_connected_apps()
            if connected_apps:
                print(f"🔍 [Company Knowledge] Buscando en {len(connected_apps)} apps conectadas con streaming en tiempo real...")
                try:
                    # OPTIMIZACIÓN CRÍTICA: Búsqueda con streaming para sidebar en tiempo real
                    async for app_name, status, count, results in self.app_integrations.search_across_apps_streaming(
                        query=message,
                        filters=filters
                    ):
                        if app_name == "all":
                            # Resultado final con todos los resultados
                            app_results = results
                            break
                        
                        # Actualizar tracking por app
                        if status == "completed":
                            results_by_app[app_name] = count
                            # Filtrar errores de token expirado SILENCIOSAMENTE (no mostrar en UI)
                            # Simplemente omitir esos resultados y continuar
                            error_results = [r for r in results if r.metadata.get("error") == "token_expired"]
                            if error_results:
                                # Filtrar resultados con error de token expirado (no agregar a search_status)
                                # No mostrar ningún mensaje al usuario - continuar silenciosamente
                                # Filtrar los resultados con error
                                results = [r for r in results if r.metadata.get("error") != "token_expired"]
                                count = len(results)  # Actualizar count después de filtrar
                            
                            # Agregar a search_status solo si hay resultados válidos
                            if count > 0:
                                search_status.append({
                                    "app": app_name,
                                    "source": f"{count} resultados encontrados",
                                    "status": "completed"
                                })
                        elif status == "error":
                            results_by_app[app_name] = 0
                            search_status.append({
                                "app": app_name,
                                "source": "Error en búsqueda",
                                "status": "error"
                            })
                        elif status == "searching":
                            search_status.append({
                                "app": app_name,
                                "source": "Buscando...",
                                "status": "searching"
                            })
                        
                        # OPTIMIZACIÓN CRÍTICA: Callback para actualizar sidebar en tiempo real
                        if sidebar_callback:
                            sidebar_text = self._generate_realtime_sidebar_status(
                                apps_searched=connected_apps,
                                results_found=results_by_app,
                                current_app=app_name if status == "searching" else None,
                                is_searching=(status == "searching")
                            )
                            try:
                                sidebar_callback(sidebar_text)
                            except Exception as e:
                                print(f"⚠️ [Company Knowledge] Error en callback de sidebar: {e}")
                        
                        # Log para debugging
                        print(f"📊 [Company Knowledge] {app_name}: {status} ({count} resultados)")
                    
                    if app_results:
                        # OPTIMIZACIÓN 2: Ranking mejorado con filtros de fecha
                        ranked_results = self._rank_results_by_relevance_and_recency(
                            query=message,
                            results=app_results,
                            filters=filters
                        )
                        
                        # OPTIMIZACIÓN 3: Detectar conflictos entre fuentes con LLM (async)
                        conflict_analysis = await self._detect_conflicts_between_sources(
                            results=ranked_results,
                            query=message
                        )
                        
                        # OPTIMIZACIÓN CRÍTICA (9/10): Resolver conflictos automáticamente con búsquedas adicionales
                        conflict_resolution = None
                        if conflict_analysis.get("has_conflicts"):
                            print(f"⚠️ [Company Knowledge] Detectados {len(conflict_analysis.get('conflicts', []))} conflictos - Iniciando resolución automática...")
                            conflict_resolution = await self._resolve_conflicts_with_additional_searches(
                                conflicts=conflict_analysis.get("conflicts", []),
                                original_query=message,
                                original_results=ranked_results,
                                filters=filters
                            )
                            
                            if conflict_resolution and conflict_resolution.get("resolved"):
                                print(f"✅ [Company Knowledge] Conflictos resueltos: {len(conflict_resolution.get('resolved_conflicts', []))}")
                                # Agregar resultados adicionales a ranked_results
                                additional_results = conflict_resolution.get("additional_results", [])
                                if additional_results:
                                    ranked_results.extend(additional_results)
                                    # Re-rankear con los nuevos resultados
                                    ranked_results = self._rank_results_by_relevance_and_recency(
                                        query=message,
                                        results=ranked_results,
                                        filters=filters
                                    )
                            else:
                                print(f"⚠️ [Company Knowledge] No se pudieron resolver todos los conflictos")
                        
                        # Preparar contexto de apps (mejorado)
                        ctx_lines = []
                        for r in ranked_results[:15]:  # Aumentado a 15 para más contexto
                            snippet = (r.snippet or r.content or "")[:500]  # Snippets más largos
                            if urls_in_bullets and r.url:
                                ctx_lines.append(f"[{r.app_name}] {r.source_name}: {snippet} (URL: {r.url})")
                            else:
                                ctx_lines.append(f"[{r.app_name}] {r.source_name}: {snippet}")
                        app_context = "\n\n📱 INFORMACIÓN DE APPS CONECTADAS:\n" + "\n".join(ctx_lines)
                        
                        # Agregar nota de conflictos y resolución si existen
                        if conflict_analysis.get("has_conflicts"):
                            if conflict_resolution and conflict_resolution.get("resolved"):
                                app_context += f"\n\n✅ RESOLUCIÓN DE CONFLICTOS: {conflict_resolution.get('resolution', 'Conflictos resueltos mediante búsquedas adicionales.')}"
                            else:
                                app_context += "\n\n⚠️ NOTA: Se detectaron discrepancias entre fuentes. Se presentan perspectivas balanceadas."
                        
                        print(f"✅ [Company Knowledge] Encontrados {len(app_results)} resultados en apps")
                        if conflict_analysis.get("has_conflicts"):
                            print(f"⚠️ [Company Knowledge] Detectados {len(conflict_analysis.get('conflicts', []))} conflictos entre fuentes")
                    else:
                        # No hay resultados de apps (puede ser por tokens expirados o porque realmente no hay resultados)
                        # No mostrar mensaje aquí - se manejará más abajo
                        print(f"⚠️ [Company Knowledge] No se encontraron resultados en las apps para la query: {message[:50]}...")
                except Exception as e:
                    print(f"⚠️ [Company Knowledge] Error buscando en apps: {e}")
                    import traceback
                    traceback.print_exc()
        
        # PRIORIDAD: Si hay resultados de apps conectadas, SIEMPRE usarlos primero (incluso si hay documentos subidos)
        # Las apps conectadas tienen prioridad sobre PDFs subidos localmente
        if app_results:
            print(f"📱 [Company Knowledge] PRIORIDAD: Usando información de apps conectadas ({len(app_results)} resultados encontrados)")
            # Generar respuesta basada solo en apps
            try:
                # Inicializar metadata ANTES de usarlo
                metadata = {}
                
                # Preparar contexto completo de apps
                ranked_results = self._rank_results_by_relevance_and_recency(
                    query=message,
                    results=app_results,
                    filters=filters
                )
                
                # Filtrar errores de token expirado SILENCIOSAMENTE (no mostrar error al usuario)
                # Simplemente omitir esos resultados y continuar con los demás
                ranked_results = [r for r in ranked_results if r.metadata.get("error") != "token_expired"]
                
                # Si después de filtrar no quedan resultados, NO generar mensaje de error
                # Simplemente retornar sin respuesta (no mostrar nada al usuario)
                if not ranked_results:
                    print(f"⚠️ [Company Knowledge] No hay resultados válidos (todos los tokens expirados) - No mostrando mensaje al usuario")
                    metadata = {
                        "sources": [],
                        "total_sources": 0,
                        "apps_searched": len(connected_apps) if connected_apps else 0,
                        "search_status": search_status,
                        "no_results": True,
                        "silent_fail": True  # Indicar que es un fallo silencioso (tokens expirados)
                    }
                    # Retornar sin mensaje de error - simplemente no mostrar nada
                    yield (history, None, metadata)
                    return
                
                ctx_lines = []
                sources_list = []
                # TRUNCAMIENTO INTELIGENTE: Limitar contexto para evitar errores 429 (tokens por minuto)
                # Calcular límite seguro: ~20,000 tokens = ~80,000 caracteres (dejando margen para prompt y respuesta)
                # Esto evita exceder el límite de TPM (tokens por minuto) de OpenAI
                total_chars = 0
                # Límite seguro: 80k chars para OpenAI (≈20k tokens), 120k para Claude (≈30k tokens)
                # Dejamos margen para el prompt y la respuesta generada
                max_chars = 80000 if provider == "openai" else 120000  # Límites seguros para evitar 429
                
                # CRÍTICO: Procesar TODOS los resultados de apps (PDFs de Google Drive)
                # Priorizar PDFs con contenido completo sobre snippets
                pdf_results = [r for r in ranked_results if r.content and len(r.content) > 1000]
                other_results = [r for r in ranked_results if not (r.content and len(r.content) > 1000)]
                
                # Primero procesar PDFs completos (prioridad máxima) con truncamiento inteligente
                for r in pdf_results:
                    # Es un PDF con contenido completo - truncar inteligentemente para evitar exceder límites
                    # Priorizar: usar hasta 15,000 caracteres por PDF (equivalente a ~3,750 tokens)
                    # Esto permite incluir múltiples PDFs sin exceder el límite total
                    max_chars_per_pdf = 15000  # Límite por PDF para balancear cantidad vs profundidad
                    content_to_use = r.content[:max_chars_per_pdf] if len(r.content) > max_chars_per_pdf else r.content
                    
                    if total_chars + len(content_to_use) <= max_chars:
                        ctx_lines.append(f"=== [{r.app_name}] {r.source_name} ===\n{content_to_use}\n")
                        total_chars += len(content_to_use)
                        if r.url:
                            sources_list.append({"app": r.app_name, "source": r.source_name, "url": r.url})
                    else:
                        # Si nos quedamos sin espacio, usar lo que quepa (mínimo 5k chars para que valga la pena)
                        remaining = max_chars - total_chars
                        if remaining > 5000:  # Mínimo 5k chars para que valga la pena
                            ctx_lines.append(f"=== [{r.app_name}] {r.source_name} ===\n{r.content[:remaining]}\n")
                            total_chars = max_chars
                            if r.url:
                                sources_list.append({"app": r.app_name, "source": r.source_name, "url": r.url})
                        break
                
                # Luego procesar otros resultados (snippets, etc.) si hay espacio
                for r in other_results:
                    # Usar snippet o contenido limitado (truncado para evitar exceder límites)
                    max_snippet_chars = 5000  # Límite por snippet para balancear cantidad vs profundidad
                    snippet = (r.snippet or r.content or "")[:max_snippet_chars]
                    if total_chars + len(snippet) <= max_chars:
                        ctx_lines.append(f"[{r.app_name}] {r.source_name}: {snippet}")
                        total_chars += len(snippet)
                        if r.url:
                            sources_list.append({"app": r.app_name, "source": r.source_name, "url": r.url})
                    else:
                        break
                
                context_block = "\n".join(ctx_lines)
                
                # Agregar nota si se truncó contenido para evitar exceder límites de tokens
                if total_chars >= max_chars * 0.9:  # Si usamos más del 90% del límite
                    truncated_count = len([r for r in pdf_results if r.content and len(r.content) > 15000])
                    if truncated_count > 0:
                        context_block += f"\n\n[NOTA: Se incluyeron los primeros {len(sources_list)} documentos más relevantes. Algunos documentos fueron truncados para evitar exceder límites de tokens. Para análisis completo de documentos específicos, realiza consultas más específicas.]"
                
                # Si no hay contexto después de procesar resultados, no llamar al LLM (evitar mensaje de error)
                if not context_block or not context_block.strip():
                    print(f"⚠️ [Company Knowledge] No hay contexto disponible (todos los tokens expirados) - No generando respuesta")
                    metadata = {
                        "sources": [],
                        "total_sources": 0,
                        "apps_searched": len(connected_apps) if connected_apps else 0,
                        "search_status": search_status,
                        "no_results": True,
                        "silent_fail": True  # Indicar que es un fallo silencioso (tokens expirados)
                    }
                    # Retornar sin mensaje de error - simplemente no mostrar nada
                    yield (history, None, metadata)
                    return
                
                # Generar respuesta con LLM - PROMPT ESTILO ENTERPRISE API SUPREME GOLD (máxima calidad suprema)
                prompt = f"""Eres un analista experto de documentos empresariales de NIVEL ALIEN GOD SUPER INTELIGENCIA (nivel consultor senior C-level, estilo McKinsey/Deloitte/Bain, con profundidad de análisis de nivel PhD).

Tu misión es analizar en profundidad ABSOLUTA la información proporcionada y generar resúmenes ejecutivos EXTENSÍSIMOS, ULTRA PROFESIONALES y DE MÁXIMA CALIDAD SUPREMA.

INFORMACIÓN DE APPS CONECTADAS:
{context_block}

PREGUNTA DEL USUARIO: {message}

INSTRUCCIONES DETALLADÍSIMAS (ESTILO ENTERPRISE API SUPREME GOLD - NIVEL ALIEN GOD):

1. **RESUMEN EJECUTIVO ULTRA EXTENSO (10-20 párrafos por documento importante, mínimo 3000-5000 palabras por documento):**
   - Contexto histórico completo y propósito profundo del documento
   - Ideas principales y argumentos centrales explicados con MÁXIMA PROFUNDIDAD
   - Conclusiones y recomendaciones clave con justificación detallada
   - Valor e importancia del contenido para diferentes audiencias (ejecutivos, técnicos, estratégicos)
   - Aplicaciones prácticas y relevancia empresarial específica con ejemplos concretos
   - Insights profundos y análisis crítico exhaustivo
   - Conexiones con otros documentos si hay múltiples (análisis comparativo)
   - Implicaciones estratégicas y tácticas con roadmap de implementación
   - Análisis de fortalezas, debilidades, oportunidades y amenazas (SWOT)
   - Comparación con estándares de la industria y mejores prácticas
   - Análisis de impacto potencial en diferentes escenarios
   - Recomendaciones prioritizadas con justificación de ROI

2. **PUNTOS CLAVE ULTRA DETALLADOS (25-40 puntos por documento importante):**
   - Conceptos fundamentales explicados con ejemplos concretos y casos de uso
   - Hallazgos importantes con contexto completo, evidencia y métricas
   - Recomendaciones específicas y accionables con pasos concretos y timeline
   - Insights valiosos para el negocio con casos de uso detallados y ROI estimado
   - Metodologías, frameworks o modelos presentados con explicación completa y aplicación práctica
   - Ejemplos concretos, estudios de caso o datos mencionados con análisis profundo
   - Advertencias, limitaciones o consideraciones importantes con mitigación de riesgos
   - Oportunidades de implementación y ROI potencial con cálculo estimado
   - Lecciones aprendidas y mejores prácticas identificadas
   - Patrones y tendencias detectadas con análisis de impacto
   - Recomendaciones de integración con sistemas existentes
   - Análisis de dependencias y requisitos previos

3. **ANÁLISIS PROFESIONAL COMPLETO Y EXHAUSTIVO:**
   - Tipo de documento y clasificación precisa (libro académico, whitepaper, informe ejecutivo, etc.)
   - Entidades principales (autores con credenciales completas, organizaciones, empresas, instituciones)
   - Temas y áreas de conocimiento cubiertas con profundidad académica
   - Fechas/períodos relevantes y contexto histórico completo
   - Valor para el negocio con métricas potenciales y KPIs sugeridos
   - Aplicaciones prácticas por industria o función con roadmap
   - Nivel de complejidad y audiencia objetivo con recomendaciones de capacitación
   - Análisis de mercado y posicionamiento competitivo
   - Análisis de riesgo y compliance
   - Análisis de costos y beneficios (CBA)

4. **ESTRUCTURA PROFESIONAL ULTRA DETALLADA:**
   - Organiza por documento cuando hay múltiples (cada uno con su sección COMPLETA y EXTENSA)
   - Usa títulos claros, subtítulos y secciones bien definidas con jerarquía profesional
   - Incluye referencias a las fuentes en cada punto (ej: "según [App] Nombre del Documento, página X, sección Y")
   - Usa formato markdown profesional con negritas, listas, citas, tablas y diagramas conceptuales
   - Sé ESPECÍFICO, DETALLADO y evita generalidades COMPLETAMENTE
   - Proporciona valor real para la toma de decisiones ejecutivas con análisis cuantitativo cuando sea posible
   - Incluye secciones de "Próximos Pasos", "Recomendaciones Prioritarias", "Riesgos y Mitigación"

5. **LONGITUD Y PROFUNDIDAD MÁXIMA ABSOLUTA (SIN LÍMITES):**
   - Genera resúmenes ULTRA EXTENSOS (mínimo 3000-5000 palabras por documento importante, sin límite superior)
   - Profundiza en los conceptos clave con explicaciones DETALLADÍSIMAS
   - Explica el "por qué", el "cómo", el "cuándo", el "dónde", el "quién" y el "qué" con MÁXIMA PROFUNDIDAD
   - Incluye análisis crítico exhaustivo, perspectivas múltiples y contraargumentos detallados
   - Proporciona contexto histórico completo, comparaciones exhaustivas y analogías enriquecedoras
   - Incluye citas directas importantes del documento cuando sean relevantes (con contexto)
   - Analiza implicaciones a corto, medio y largo plazo
   - Proporciona análisis de escenarios (best case, worst case, most likely)
   - Incluye análisis de stakeholders y sus intereses

6. **CALIDAD ENTERPRISE SUPREMA (NIVEL ALIEN GOD):**
   - Nivel de detalle equivalente a un informe de consultoría estratégica de nivel C-suite
   - Análisis que un CEO o C-level podría usar DIRECTAMENTE para decisiones críticas
   - Profundidad que permite entender el documento COMPLETAMENTE sin leerlo
   - Insights accionables con pasos concretos de implementación y timeline
   - Consideración de múltiples perspectivas y escenarios con análisis de probabilidades
   - Análisis de impacto en diferentes departamentos y funciones
   - Recomendaciones con priorización y justificación estratégica
   - Análisis de viabilidad técnica, financiera y organizacional

7. **ANÁLISIS ADICIONAL PROFESIONAL:**
   - Si es un libro académico: análisis de metodología, contribuciones teóricas, aplicaciones prácticas
   - Si es un whitepaper: análisis de propuesta de valor, diferenciación competitiva, roadmap de adopción
   - Si es un informe ejecutivo: análisis de hallazgos, recomendaciones estratégicas, plan de acción
   - Análisis de audiencia objetivo y personalización de mensajes
   - Análisis de canales de distribución y estrategia de comunicación
   - Análisis de métricas de éxito y KPIs relevantes

MANEJO DE CONFLICTOS Y DISCREPANCIAS:
- Si detectas información contradictoria entre fuentes, PRESÉNTALA de forma balanceada
- Muestra TODAS las perspectivas cuando hay desacuerdos
- Indica claramente cuando diferentes fuentes tienen información conflictiva
- Explica el contexto de cada perspectiva y por qué pueden diferir
- NO tomes partido - presenta todas las versiones de forma objetiva
- Si hay números o datos que no coinciden, menciona ambas versiones con sus fuentes
- Sugiere próximos pasos para resolver discrepancias cuando sea apropiado

IMPORTANTE CRÍTICO:
- Usa SOLO la información proporcionada de las apps - NO inventes nada
- Sé ESPECÍFICO y DETALLADO al máximo - evita generalidades COMPLETAMENTE
- Proporciona valor REAL y ACCIONABLE para la toma de decisiones ejecutivas
- Usa lenguaje profesional pero claro (nivel C-level, estilo consultoría estratégica)
- Si hay múltiples documentos, analiza CADA UNO en profundidad COMPLETA y EXTENSA
- NO limites la longitud - genera el análisis MÁS COMPLETO POSIBLE (mínimo 3000-5000 palabras por documento)
- Incluye TODOS los detalles importantes que encuentres en el contenido
- Profundiza en CADA concepto, idea y recomendación con explicaciones exhaustivas
- Proporciona contexto histórico, comparaciones y análisis crítico en CADA sección
- Incluye citas directas relevantes del documento con análisis de su importancia
- Analiza implicaciones estratégicas, tácticas y operacionales en profundidad

CALIDAD REQUERIDA: NIVEL ALIEN GOD SUPER INTELIGENCIA - MÁXIMA CALIDAD SUPREMA

Genera un análisis COMPLETÍSIMO, ULTRA EXTENSO, PROFESIONALÍSIMO y DE MÁXIMA CALIDAD SUPREMA (mínimo 3000-5000 palabras por documento, sin límite superior):"""
                
                # Generar respuesta con streaming (como Enterprise API y Chat Conversacional 2)
                from langchain_core.messages import HumanMessage
                full_response = ""
                
                # CRÍTICO: Stream tokens en tiempo real y yield actualizaciones parciales
                # Esto permite que la respuesta aparezca en tiempo real en la UI (como ChatGPT)
                print(f"🚀 [Company Knowledge] Generando respuesta con streaming (contexto: {len(context_block):,} caracteres, {len(ranked_results)} PDFs de apps)...")
                
                # Stream tokens en tiempo real
                chunk_count = 0
                async for chunk in self.llm.astream([HumanMessage(content=prompt)]):
                    if hasattr(chunk, 'content'):
                        token = chunk.content
                    else:
                        token = str(chunk)
                    full_response += token
                    chunk_count += 1
                    
                    # Yield actualización parcial cada 5 chunks para streaming en tiempo real
                    # Esto permite que la respuesta aparezca mientras se genera (como ChatGPT)
                    if chunk_count % 5 == 0:
                        temp_history = history + [(message, full_response)]
                        temp_metadata = {
                            "sources": sources_list,
                            "total_sources": len(sources_list),
                            "apps_searched": len(connected_apps) if connected_apps else 0,
                            "search_status": search_status,
                            "streaming": True  # Indicar que está en streaming
                        }
                        yield (temp_history, None, temp_metadata)
                
                # OPTIMIZACIÓN 4: Citas mejoradas con snippets exactos
                if sources_list:
                    # Usar método mejorado de citas
                    enhanced_citations = self._generate_enhanced_citations(
                        results=ranked_results,
                        max_citations=15
                    )
                    full_response += enhanced_citations
                
                # OPTIMIZACIÓN 5: Agregar nota de conflictos y resolución si existen (async)
                conflict_analysis = await self._detect_conflicts_between_sources(
                    results=ranked_results,
                    query=message
                )
                
                # OPTIMIZACIÓN CRÍTICA: Resolver conflictos automáticamente
                conflict_resolution = None
                if conflict_analysis.get("has_conflicts"):
                    conflict_resolution = await self._resolve_conflicts_with_additional_searches(
                        conflicts=conflict_analysis.get("conflicts", []),
                        original_query=message,
                        original_results=ranked_results,
                        filters=filters
                    )
                    
                    if conflict_resolution and conflict_resolution.get("resolved"):
                        # Agregar resultados adicionales y re-rankear
                        additional_results = conflict_resolution.get("additional_results", [])
                        if additional_results:
                            ranked_results.extend(additional_results)
                            ranked_results = self._rank_results_by_relevance_and_recency(
                                query=message,
                                results=ranked_results,
                                filters=filters
                            )
                
                if conflict_analysis.get("has_conflicts"):
                    conflicts_note = "\n\n---\n\n### ⚠️ Análisis de Consenso y Resolución\n\n"
                    conflicts_note += f"**Nivel de consenso inicial:** {conflict_analysis.get('consensus_level', 0.0)*100:.0f}%\n\n"
                    
                    if conflict_resolution and conflict_resolution.get("resolved"):
                        conflicts_note += "**✅ Conflictos Resueltos Automáticamente:**\n\n"
                        conflicts_note += f"{conflict_resolution.get('resolution', 'Se realizaron búsquedas adicionales para resolver las discrepancias.')}\n\n"
                        
                        # Mostrar conflictos resueltos
                        for resolved_conflict in conflict_resolution.get("resolved_conflicts", [])[:3]:
                            conflict = resolved_conflict.get("conflict", {})
                            if resolved_conflict.get("resolved"):
                                conflicts_note += f"**✅ Resuelto:** {conflict.get('description', 'Conflicto')}\n"
                                conflicts_note += f"   - {resolved_conflict.get('explanation', '')}\n\n"
                    else:
                        conflicts_note += "**Discrepancias detectadas:**\n\n"
                        for conflict in conflict_analysis.get("conflicts", [])[:3]:
                            conflicts_note += f"- {conflict.get('description', 'Conflicto detectado')}\n"
                            conflicts_note += f"  - Fuente 1: [{conflict.get('source1', {}).get('app', 'Unknown')}] {conflict.get('source1', {}).get('name', 'Unknown')}\n"
                            conflicts_note += f"  - Fuente 2: [{conflict.get('source2', {}).get('app', 'Unknown')}] {conflict.get('source2', {}).get('name', 'Unknown')}\n\n"
                        conflicts_note += "\n*Se presentan perspectivas balanceadas basadas en todas las fuentes disponibles.*\n"
                    
                    full_response += conflicts_note
                
                new_history = history + [(message, full_response)]
                
                # OPTIMIZACIÓN 6: Metadata mejorada con información de búsqueda
                metadata = {
                    "sources": sources_list,
                    "total_sources": len(sources_list),
                    "apps_searched": len(connected_apps) if connected_apps else 0,
                    "search_status": search_status,
                    "conflicts_detected": conflict_analysis.get("has_conflicts", False),
                    "conflicts_resolved": conflict_resolution.get("resolved", False) if conflict_resolution else False,
                    "consensus_level": conflict_analysis.get("consensus_level", 1.0),
                    "results_by_app": results_by_app,
                    "conflict_resolution": conflict_resolution
                }
                
                # En un async generator, usar yield en lugar de return con valor
                yield (new_history, None, metadata)
                return
            except Exception as e:
                yield (history, f"❌ Error generando respuesta: {str(e)}", {})
                return
        
        # PRIORIDAD: Apps conectadas primero, luego documentos subidos
        # Verificar si hay documentos disponibles en la sesión (para uso secundario)
        has_documents = (
            session.get("retriever") is not None or 
            (session.get("docs") and len(session.get("docs", [])) > 0)
        )
        
        # Si no hay resultados de apps, verificar si hay documentos subidos para usar como respaldo
        if not app_results:
            # Si hay documentos subidos, usarlos automáticamente (incluso si los tokens están expirados)
            if has_documents:
                print(f"✅ [Company Knowledge] No hay resultados de apps, pero hay documentos subidos - Usando documentos como respaldo")
                # Continuar con el procesamiento normal usando documentos subidos
                # El código continúa más abajo
            else:
                # No hay resultados de apps NI documentos subidos
                # Verificar si es por tokens expirados (fallo silencioso)
                if connected_apps:
                    # Si hay apps conectadas pero no hay resultados, probablemente todos los tokens están expirados
                    # Hacer silent_fail (no mostrar mensaje al usuario)
                    print(f"⚠️ [Company Knowledge] No hay resultados de apps ni documentos subidos - Probablemente todos los tokens expirados (silent_fail)")
                    metadata = {
                        "sources": [],
                        "total_sources": 0,
                        "apps_searched": len(connected_apps),
                        "no_results": True,
                        "silent_fail": True  # Fallo silencioso - probablemente todos los tokens expirados
                    }
                    # Retornar sin mensaje de error - simplemente no mostrar nada
                    yield (history, None, metadata)
                    return
                elif self.app_integrations and self.app_integrations.get_connected_apps():
                    yield (history, "⚠️ No hay documentos procesados. Puedes cargar documentos o hacer preguntas sobre tus apps conectadas.", {})
                    return
                else:
                    yield (history, "⚠️ No hay documentos procesados. Carga documentos primero o conecta apps en 'Conectar Apps'.", {})
                    return
        
        # PRIORIDAD: Si hay resultados de apps, ya se procesaron arriba y se retornó
        # Si llegamos aquí, significa que no hay resultados de apps, pero puede haber documentos subidos
        # Continuar con procesamiento normal usando documentos subidos (si existen)
        
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
        
        # 8. PRIORIDAD: Si hay resultados de apps, usarlos como fuente principal
        # Si hay documentos subidos, se combinan como fuente secundaria
        if app_results:
            # Ya tenemos resultados de apps de antes (prioridad), agregarlos al contexto
            conversation_context += app_context
            if has_documents:
                print(f"✅ [Company Knowledge] PRIORIDAD: {len(app_results)} resultados de apps + documentos subidos como complemento")
            else:
                print(f"✅ [Company Knowledge] PRIORIDAD: Usando {len(app_results)} resultados de apps conectadas")
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
            
            yield (history, None, metadata)
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
            
            yield (history, error_msg, {})
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
<<<<<<< HEAD
=======
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

    async def execute_autonomous_task_v2(
        self,
        task_description: str,
        task_type: str,
        filters: Optional[Dict[str, Any]] = None,
        urls_in_bullets: bool = False
    ) -> Dict[str, Any]:
        """
>>>>>>> 770f1d47fd471c4df7b72988637447c118a00e19
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
        # Usar TODO el contenido completo de PDFs SIN LÍMITES para máxima calidad suprema
        ctx_lines = []
        search_status = []  # Para sidebar en tiempo real
        total_chars = 0
        # Aumentar límite total: 1M para OpenAI, 1.5M para Claude (como Enterprise API Supreme)
        provider_val = getattr(self, 'provider', 'openai')
        max_chars = 1000000 if provider_val == "openai" else 1500000  # Límites mucho más altos
        
        for r in ranked_results:  # TODOS los resultados, sin límite
            app_display = f"[{r.app_name}]"
            search_status.append({
                "app": r.app_name,
                "source": r.source_name,
                "status": "found"
            })
            
            # Para PDFs, usar TODO el contenido completo SIN LÍMITES
            if r.content and len(r.content) > 1000:
                content_to_use = r.content  # SIN LÍMITE - usar todo el contenido
                if total_chars + len(content_to_use) <= max_chars:
                    if urls_in_bullets and r.url:
                        ctx_lines.append(f"{app_display} {r.source_name} (URL: {r.url}):\n{content_to_use}\n")
                    else:
                        ctx_lines.append(f"{app_display} {r.source_name}:\n{content_to_use}\n")
                    total_chars += len(content_to_use)
                else:
                    remaining = max_chars - total_chars
                    if remaining > 10000:  # Mínimo 10k chars para que valga la pena
                        ctx_lines.append(f"{app_display} {r.source_name}:\n{r.content[:remaining]}\n")
                        total_chars = max_chars
                    break
            else:
                # Para otros tipos, usar snippet más largo
                snippet = (r.snippet or r.content or "")[:10000]  # Aumentado a 10k chars
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
Eres un asistente experto en preparar pre-briefs ejecutivos de NIVEL ALIEN GOD SUPER INTELIGENCIA (estilo ChatGPT Enterprise Company Knowledge con máxima calidad suprema).

Genera un pre-brief ULTRA PROFESIONAL, EXTENSÍSIMO y DETALLADÍSIMO basado en la información de múltiples fuentes conectadas.

FORMATO REQUERIDO (EXACTAMENTE como ChatGPT Enterprise - ver ejemplo real abajo, pero con MÁXIMA PROFUNDIDAD):

## Executive summary

[Un párrafo fluido EXTENSO de 8-15 oraciones que resume los hallazgos más importantes con MÁXIMA PROFUNDIDAD. DEBE incluir métricas específicas cuando estén disponibles: porcentajes exactos (+42%), números concretos, fechas específicas, comparaciones temporales (vs September, vs Q3 baseline), análisis de causas, implicaciones estratégicas y recomendaciones de alto nivel.

Ejemplo exacto del formato esperado (pero MÁS EXTENSO):
"The October campaign outperformed benchmarks for engagement and conversion, setting a strong baseline for Q4 growth initiatives. The campaign exceeded engagement targets, driving a +42% lift in new leads and a 3-point increase in feature adoption compared to September. Sentiment in customer channels shifted positive following the 10/24 patch release, while conversion metrics stabilized above the Q3 baseline. This performance indicates successful execution of the multi-channel strategy, with particular strength in organic search and email marketing channels. The data suggests that the product improvements implemented in Q3 are resonating with the target demographic, particularly in the 25-34 age segment which showed a 28% increase in engagement. However, the analysis reveals potential optimization opportunities in the paid advertising channels, where ROI decreased by 12% despite increased spend. Strategic recommendations include reallocating 15% of paid media budget to high-performing organic channels and implementing A/B testing on the top 3 landing pages to further improve conversion rates."]

## Key insights

[Bullets EXTENSOS y DETALLADOS con insights clave. Cada bullet DEBE:
- Incluir métricas específicas cuando estén disponibles (números exactos, porcentajes, fechas)
- Contexto temporal completo (Week 2, month-over-month, compared to X)
- Referencias a eventos específicos (10/10 email, 10/24 patch release)
- Impacto cuantificado cuando sea posible (+18% month-over-month)
- Análisis de causas y efectos
- Implicaciones estratégicas
- Recomendaciones específicas cuando aplique

Formato de ejemplo exacto (pero MÁS DETALLADO):
- Peak engagement: Week 2 (aligned with 10/10 email campaign launch) - This represents a 35% increase over baseline and indicates strong product-market fit for the new feature set. The timing correlation suggests that email marketing remains a highly effective channel for feature adoption, with an open rate of 42% and click-through rate of 18%, both above industry benchmarks.
- Retention impact: +18% month-over-month improvement in 30-day retention, driven primarily by improvements in onboarding flow completion rates (from 45% to 62%). This improvement is particularly notable in the enterprise segment, where retention increased by 24%, suggesting that the new enterprise features are delivering significant value.
- Conversion metrics: 3-point increase vs September baseline, with the most significant gains in the mobile channel (+5.2 points) and the freemium-to-paid conversion funnel (+4.8 points). Analysis indicates that the mobile improvements implemented in late September are driving this uplift, with mobile conversion rates now matching desktop for the first time.
- Feature adoption: +42% lift in new leads attributed to the new analytics dashboard feature, which has become the primary differentiator in competitive evaluations. The feature has a 78% activation rate among new users and a 65% 7-day retention rate, indicating strong product-market fit.

Agrega 20-30 bullets EXTENSOS con insights clave encontrados en las fuentes, siempre con métricas específicas, análisis profundo e implicaciones cuando estén disponibles.]

## Risks / Issues (si aplica)

[Si hay riesgos o issues identificados en las fuentes, listarlos aquí con detalles ESPECÍFICOS, análisis de impacto, probabilidad de ocurrencia, y recomendaciones de mitigación. Si no hay, OMITIR completamente esta sección]

## Next actions

[8-12 acciones recomendadas basadas en los insights. Cada acción debe ser ESPECÍFICA, ACCIONABLE, con contexto temporal, responsable asignado sugerido, timeline estimado, y ROI potencial cuando sea posible]

## Strategic implications

[Análisis de implicaciones estratégicas a corto, medio y largo plazo basado en los hallazgos]

## Recommendations for deeper analysis

[Recomendaciones para análisis adicionales que podrían proporcionar más insights valiosos]

---

**Fuentes consultadas:** {len(ranked_results)} fuentes de {len(sources_by_app)} apps
{sources_summary}

INSTRUCCIONES CRÍTICAS (NIVEL ALIEN GOD):
1. USA SOLO la información proporcionada en las fuentes. NO inventes datos ni métricas.
2. Incluye métricas específicas (números exactos, porcentajes, fechas) SOLO cuando estén disponibles en las fuentes.
3. Si encuentras información contradictoria, presenta ambas perspectivas de forma balanceada con análisis de por qué pueden existir discrepancias.
4. Si no hay una respuesta clara, explica la ambigüedad y qué información falta, y sugiere cómo obtenerla.
5. Prioriza información más reciente cuando sea relevante, pero proporciona contexto histórico cuando enriquezca el análisis.
6. Formatea las métricas de forma destacada (ej: "+42% lift", "+18% MoM", "3-point increase", "Week 2").
7. Incluye referencias a las fuentes cuando sea relevante (ej: "según [App] Source Name, página X").
8. El Executive Summary debe ser un párrafo fluido y continuo EXTENSO (8-15 oraciones), NO bullets.
9. Los Key Insights deben ser bullets EXTENSOS (2-4 oraciones cada uno) con métricas específicas, análisis y recomendaciones.
10. Si la tarea menciona "campaign results", "customer feedback", "company performance", busca métricas de rendimiento, KPIs, y datos cuantitativos en las fuentes.
11. Profundiza en CADA insight con análisis de causas, efectos, implicaciones y recomendaciones.
12. Proporciona contexto histórico, comparaciones con benchmarks de la industria, y análisis de tendencias cuando sea relevante.
13. Incluye análisis de segmentación (por canal, producto, región, demografía, etc.) cuando los datos lo permitan.
14. Genera un pre-brief de MÁXIMA CALIDAD SUPREMA (mínimo 2000-3000 palabras, sin límite superior).

{conflict_context}

Información de las apps conectadas:
{context_block}

Tarea original: {task_description}

Genera el pre-brief ahora siguiendo EXACTAMENTE el formato especificado arriba, con MÁXIMA PROFUNDIDAD y CALIDAD SUPREMA.
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
        elif task_type == "data_analysis":
            prompt = f"""
            Eres un analista de Business Intelligence experto de NIVEL ALIEN GOD SUPER INTELIGENCIA (nivel consultor senior de BI, estilo McKinsey/Deloitte Analytics). Tu tarea es analizar los datos proporcionados
            de múltiples fuentes conectadas y generar un reporte ULTRA PROFESIONAL, EXTENSÍSIMO y DETALLADÍSIMO con insights clave, detección de KPIs,
            análisis de tendencias y outliers, y recomendaciones accionables.
            
            INSTRUCCIONES ESPECIALES (NIVEL ALIEN GOD):
            1. Si encuentras datos contradictorios, identifica las discrepancias, explica posibles causas, y proporciona recomendaciones para resolverlas.
            2. Prioriza datos más recientes para análisis de tendencias, pero proporciona contexto histórico completo.
            3. Si no hay suficiente información para un análisis completo, indica qué datos faltan, por qué son importantes, y cómo obtenerlos.
            4. Incluye URLs de las fuentes en los bullets cuando aplique.
            5. Profundiza en CADA KPI, tendencia y outlier con análisis exhaustivo de causas, efectos e implicaciones.
            6. Proporciona análisis de segmentación (por canal, producto, región, cliente, período, etc.) cuando los datos lo permitan.
            7. Incluye comparaciones con benchmarks de la industria cuando sea relevante.
            8. Proporciona análisis de escenarios (best case, worst case, most likely) cuando sea apropiado.
            9. Genera un reporte de MÁXIMA CALIDAD SUPREMA (mínimo 3000-5000 palabras, sin límite superior).
            
            {conflict_context}
            
            Estructura tu respuesta de la siguiente manera (con MÁXIMA PROFUNDIDAD):

            ## 📊 Reporte de Análisis de Datos y KPIs (NIVEL ALIEN GOD)

            ### 📝 Resumen Ejecutivo EXTENSO
            [Un resumen EXTENSO de 10-20 párrafos de los hallazgos más importantes, con análisis profundo de causas, efectos, implicaciones estratégicas, y recomendaciones de alto nivel. Incluye métricas específicas, tendencias identificadas, riesgos detectados, y oportunidades identificadas.]

            ### 📈 KPIs Clave Identificados y Análisis EXHAUSTIVO
            [Lista EXTENSA de KPIs relevantes detectados automáticamente en los datos, con su valor, tendencia, análisis exhaustivo de causas, comparación con benchmarks, segmentación cuando aplique, y recomendaciones específicas.
            Ej: "MRR: $X (↑ 8.2% en 30 días) - Impulsado por nuevas ventas orgánicas. Análisis detallado: El crecimiento se concentra en el segmento enterprise (↑ 15.3%), mientras que el segmento SMB muestra crecimiento moderado (↑ 4.1%). La región EMEA lidera el crecimiento (↑ 12.5%), seguida de APAC (↑ 9.8%) y Americas (↑ 6.2%). El análisis de cohortes muestra que los clientes adquiridos en Q3 tienen una tasa de retención del 94% a los 90 días, comparado con el 87% de los clientes de Q2, indicando mejoras en la calidad de adquisición. Recomendación: Escalar estrategias de adquisición que replican el éxito del segmento enterprise en EMEA, con un presupuesto adicional estimado de $500K que podría generar $2.5M en MRR adicional en 6 meses."]

            ### 📉 Tendencias, Patrones y Outliers - ANÁLISIS PROFUNDO
            [Identifica tendencias significativas (crecimiento, decrecimiento), patrones recurrentes y cualquier anomalía o "outlier"
            inesperado en los datos, explicando su posible causa o implicación con ANÁLISIS EXHAUSTIVO.
            Ej: "Las cancelaciones subieron 12% en el último mes, lo que podría indicar un problema de onboarding reciente. Análisis detallado: El aumento se concentra en clientes con menos de 30 días de antigüedad (↑ 28%), particularmente en el segmento SMB (↑ 35%). El análisis de feedback muestra que el 67% de los clientes que cancelan mencionan dificultades en el onboarding. Comparación con períodos anteriores: Las cancelaciones en el mismo período del año pasado fueron del 8%, indicando un problema nuevo. Análisis de causas raíz: Los cambios en el proceso de onboarding implementados en septiembre (simplificación de pasos de 7 a 4) parecen haber reducido la comprensión del producto. Recomendación: Implementar un programa de onboarding mejorado con sesiones de capacitación personalizadas, con un objetivo de reducir cancelaciones en un 40% en 60 días."]

            ### 🛠️ Plan de Limpieza y Normalización de Datos (si aplica)
            [Si se detectan inconsistencias o problemas de calidad de datos, propone un plan DETALLADO para limpiarlos y normalizarlos, con pasos específicos, timeline, responsables sugeridos, y ROI estimado.]

            ### 💡 Propuesta de Dashboard de KPIs DETALLADA
            [Sugiere un dashboard COMPLETO con los KPIs más críticos, incluyendo:
            - Métrica: [Nombre del KPI]
            - Fórmula: [Cómo se calcula con ejemplos]
            - Periodicidad: [Diario/Semanal/Mensual/Trimestral] con justificación
            - Segmentación sugerida: [Por producto, región, cliente, etc.] con análisis de valor
            - Gráfico sugerido: [Líneas, barras, pastel, etc.] con justificación
            - Alertas y umbrales: [Cuándo alertar y a quién]
            - Integración con sistemas: [Cómo integrar con sistemas existentes]
            ]

            ### 🚀 Próximas Acciones y Recomendaciones Estratégicas EXTENSAS
            [Recomendaciones de negocio concretas y accionables, estilo consultor, para mejorar los resultados basados en el análisis. Cada recomendación debe incluir:
            - Descripción detallada de la acción
            - Justificación basada en datos
            - Timeline estimado
            - Responsable sugerido
            - ROI estimado cuando sea posible
            - Riesgos y mitigación
            - Métricas de éxito
            Ej: "Basado en los datos de tráfico y conversiones, la estrategia más rentable es escalar Google Ads un 20%
            mientras optimizas la landing page X con un test A/B. Análisis detallado: Los datos muestran que Google Ads tiene un ROI de 4.2x, comparado con 2.8x de Facebook Ads y 3.1x de LinkedIn Ads. El análisis de conversión por landing page muestra que la landing page X tiene una tasa de conversión del 8.5%, comparado con el promedio de 5.2%, pero solo recibe el 12% del tráfico. Un aumento del 20% en el presupuesto de Google Ads ($50K adicionales) podría generar $210K en ingresos adicionales, con un ROI neto de 3.2x. El test A/B en la landing page X podría mejorar la tasa de conversión del 8.5% al 11% (basado en mejores prácticas de la industria), generando $85K adicionales en ingresos con una inversión de $15K en desarrollo y testing. Timeline: 30 días para implementar el aumento de presupuesto, 45 días para completar el test A/B. Responsable: Equipo de Marketing Digital. Métricas de éxito: Aumento del 20% en conversiones de Google Ads, mejora del 30% en tasa de conversión de landing page X."]

            ### 📊 Análisis de Segmentación Profundo
            [Análisis detallado de los datos segmentados por diferentes dimensiones (canal, producto, región, cliente, período, etc.) cuando los datos lo permitan, con insights específicos por segmento.]

            ### 🔍 Análisis de Correlaciones y Causalidad
            [Identifica correlaciones significativas entre diferentes métricas y proporciona análisis de causalidad cuando sea posible, con recomendaciones basadas en estas relaciones.]

            ### 📈 Proyecciones y Forecasting
            [Proyecciones de tendencias futuras basadas en los datos históricos, con diferentes escenarios (best case, worst case, most likely) y recomendaciones para cada escenario.]

            Información de las apps conectadas:
            {context_block}

            Tarea original: {task_description}

            Genera un reporte de análisis de datos de MÁXIMA CALIDAD SUPREMA (mínimo 3000-5000 palabras, sin límite superior), con análisis exhaustivo, insights profundos, y recomendaciones accionables detalladas.
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
    
    async def _detect_conflicts_between_sources(
        self,
        results: List[Any],
        query: str
    ) -> Dict[str, Any]:
        """
        Detecta conflictos y discrepancias entre diferentes fuentes usando LLM.
        
        OPTIMIZACIÓN CRÍTICA: Usa LLM para detectar contradicciones semánticas,
        no solo keywords simples.
        
        Returns:
            Dict con:
            - has_conflicts: bool
            - conflicts: List[Dict] con detalles de conflictos
            - consensus_level: float (0-1, 1 = total consenso)
        """
        if len(results) < 2:
            return {
                "has_conflicts": False,
                "conflicts": [],
                "consensus_level": 1.0
            }
        
        # OPTIMIZACIÓN: Usar LLM para detectar conflictos semánticos
        try:
            # Preparar contexto de resultados para análisis
            sources_text = ""
            for i, result in enumerate(results[:10], 1):  # Limitar a top 10 para eficiencia
                app_name = result.app_name
                source_name = result.source_name
                content = (result.snippet or result.content or "")[:1000]  # Primeros 1000 chars
                sources_text += f"\n--- Fuente {i} ---\n"
                sources_text += f"App: {app_name}\n"
                sources_text += f"Documento: {source_name}\n"
                sources_text += f"Contenido: {content}\n"
            
            # Prompt para LLM de detección de conflictos
            conflict_prompt = f"""Eres un analista experto en detectar contradicciones y discrepancias entre fuentes de información.

QUERY DEL USUARIO: {query}

FUENTES ENCONTRADAS:
{sources_text}

INSTRUCCIONES:
1. Analiza si hay CONTRADICCIONES, DISCREPANCIAS o INFORMACIÓN CONFLICTIVA entre las fuentes.
2. Busca:
   - Información que se contradice directamente (ej: "X aumentó" vs "X disminuyó")
   - Números o datos que no coinciden
   - Conclusiones opuestas sobre el mismo tema
   - Información que una fuente afirma y otra niega
3. NO consideres diferencias menores de redacción o perspectivas complementarias como conflictos.

RESPONDE EN FORMATO JSON:
{{
    "has_conflicts": true/false,
    "conflicts": [
        {{
            "type": "contradiction" | "discrepancy" | "opposing_views",
            "description": "Descripción clara del conflicto",
            "source1_index": 1,
            "source2_index": 2,
            "source1_claim": "Lo que dice la fuente 1",
            "source2_claim": "Lo que dice la fuente 2"
        }}
    ],
    "consensus_level": 0.0-1.0 (1.0 = total consenso, 0.0 = conflicto total)
}}

IMPORTANTE: Responde SOLO con JSON válido, sin texto adicional."""
            
            from langchain_core.messages import HumanMessage
            response_obj = self.llm.invoke([HumanMessage(content=conflict_prompt)])
            response = response_obj.content if hasattr(response_obj, 'content') else str(response_obj)
            
            # Extraer JSON de la respuesta
            import json
            import re
            
            # Buscar JSON en la respuesta (puede tener texto antes/después)
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                conflict_data = json.loads(json_str)
                
                # Mapear índices a fuentes reales
                conflicts_detailed = []
                for conflict in conflict_data.get("conflicts", [])[:5]:  # Limitar a top 5
                    idx1 = conflict.get("source1_index", 1) - 1
                    idx2 = conflict.get("source2_index", 2) - 1
                    
                    if 0 <= idx1 < len(results) and 0 <= idx2 < len(results):
                        result1 = results[idx1]
                        result2 = results[idx2]
                        
                        conflicts_detailed.append({
                            "type": conflict.get("type", "contradiction"),
                            "description": conflict.get("description", "Conflicto detectado"),
                            "source1": {
                                "app": result1.app_name,
                                "name": result1.source_name,
                                "claim": conflict.get("source1_claim", "")
                            },
                            "source2": {
                                "app": result2.app_name,
                                "name": result2.source_name,
                                "claim": conflict.get("source2_claim", "")
                            }
                        })
                
                return {
                    "has_conflicts": conflict_data.get("has_conflicts", False),
                    "conflicts": conflicts_detailed,
                    "consensus_level": float(conflict_data.get("consensus_level", 1.0))
                }
            else:
                # Fallback si no se puede parsear JSON
                raise ValueError("No se pudo extraer JSON de la respuesta del LLM")
                
        except Exception as e:
            print(f"⚠️ [Company Knowledge] Error en detección de conflictos con LLM: {e}")
            # Fallback a detección básica con keywords
            return self._detect_conflicts_basic(results, query)
    
    async def _resolve_conflicts_with_additional_searches(
        self,
        conflicts: List[Dict[str, Any]],
        original_query: str,
        original_results: List[Any],
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        OPTIMIZACIÓN CRÍTICA (9/10): Resuelve conflictos automáticamente haciendo
        búsquedas adicionales para encontrar información que aclare las discrepancias.
        
        Similar a ChatGPT Enterprise: "can run multiple searches to resolve conflicting details"
        
        Returns:
            Dict con:
            - resolved: bool (si se pudo resolver)
            - resolution: str (explicación de la resolución)
            - additional_results: List[AppSearchResult] (resultados de búsquedas adicionales)
            - resolved_conflicts: List[Dict] (conflictos resueltos)
        """
        if not conflicts or not self.app_integrations:
            return {
                "resolved": False,
                "resolution": "",
                "additional_results": [],
                "resolved_conflicts": []
            }
        
        print(f"🔍 [Company Knowledge] Resolviendo {len(conflicts)} conflictos con búsquedas adicionales...")
        
        # Generar queries específicas para cada conflicto
        resolution_queries = []
        for conflict in conflicts[:3]:  # Limitar a top 3 conflictos para eficiencia
            description = conflict.get("description", "")
            source1_claim = conflict.get("source1", {}).get("claim", "")
            source2_claim = conflict.get("source2", {}).get("claim", "")
            
            # Generar queries específicas usando LLM
            query_generation_prompt = f"""Se detectó un conflicto entre fuentes:

CONFLICTO: {description}
Fuente 1 dice: {source1_claim}
Fuente 2 dice: {source2_claim}

QUERY ORIGINAL: {original_query}

Genera 2-3 queries de búsqueda específicas que ayudarían a resolver este conflicto.
Las queries deben buscar información oficial, reportes, o fuentes autoritativas que puedan aclarar la discrepancia.

RESPONDE EN FORMATO JSON:
{{
    "queries": [
        "query 1 específica",
        "query 2 específica",
        "query 3 específica"
    ]
}}

IMPORTANTE: Responde SOLO con JSON válido."""
            
            try:
                from langchain_core.messages import HumanMessage
                response_obj = self.llm.invoke([HumanMessage(content=query_generation_prompt)])
                response = response_obj.content if hasattr(response_obj, 'content') else str(response_obj)
                
                import json
                import re
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    query_data = json.loads(json_match.group(0))
                    queries = query_data.get("queries", [])
                    resolution_queries.extend(queries)
            except Exception as e:
                print(f"⚠️ [Company Knowledge] Error generando queries de resolución: {e}")
                # Fallback: generar queries básicas
                resolution_queries.append(f"{original_query} reporte oficial")
                resolution_queries.append(f"{original_query} datos confirmados")
        
        if not resolution_queries:
            return {
                "resolved": False,
                "resolution": "No se pudieron generar queries de resolución.",
                "additional_results": [],
                "resolved_conflicts": []
            }
        
        # Ejecutar búsquedas adicionales
        additional_results = []
        print(f"🔍 [Company Knowledge] Ejecutando {len(resolution_queries)} búsquedas adicionales...")
        
        for resolution_query in resolution_queries[:5]:  # Limitar a 5 queries
            try:
                results = await self.app_integrations.search_across_apps(
                    query=resolution_query,
                    filters=filters
                )
                additional_results.extend(results)
                print(f"✅ [Company Knowledge] Búsqueda adicional: '{resolution_query}' → {len(results)} resultados")
            except Exception as e:
                print(f"⚠️ [Company Knowledge] Error en búsqueda adicional: {e}")
                continue
        
        if not additional_results:
            return {
                "resolved": False,
                "resolution": "No se encontraron resultados adicionales para resolver el conflicto.",
                "additional_results": [],
                "resolved_conflicts": []
            }
        
        # Analizar resultados adicionales para resolver conflictos
        print(f"🔍 [Company Knowledge] Analizando {len(additional_results)} resultados adicionales para resolver conflictos...")
        
        # Preparar contexto para análisis de resolución
        conflicts_text = ""
        for i, conflict in enumerate(conflicts[:3], 1):
            conflicts_text += f"\n--- Conflicto {i} ---\n"
            conflicts_text += f"Descripción: {conflict.get('description', '')}\n"
            conflicts_text += f"Fuente 1: {conflict.get('source1', {}).get('claim', '')}\n"
            conflicts_text += f"Fuente 2: {conflict.get('source2', {}).get('claim', '')}\n"
        
        additional_sources_text = ""
        for i, result in enumerate(additional_results[:10], 1):
            app_name = result.app_name
            source_name = result.source_name
            content = (result.snippet or result.content or "")[:800]
            additional_sources_text += f"\n--- Fuente Adicional {i} ---\n"
            additional_sources_text += f"App: {app_name}\n"
            additional_sources_text += f"Documento: {source_name}\n"
            additional_sources_text += f"Contenido: {content}\n"
        
        # Prompt para LLM de resolución de conflictos
        resolution_prompt = f"""Eres un analista experto en resolver conflictos entre fuentes de información usando información adicional.

QUERY ORIGINAL: {original_query}

CONFLICTOS DETECTADOS:
{conflicts_text}

FUENTES ADICIONALES ENCONTRADAS (para resolver conflictos):
{additional_sources_text}

INSTRUCCIONES:
1. Analiza las fuentes adicionales para determinar cuál versión de cada conflicto es correcta.
2. Si las fuentes adicionales confirman una versión, indícalo claramente.
3. Si las fuentes adicionales muestran que ambas versiones pueden ser correctas en diferentes contextos, explícalo.
4. Si no hay suficiente información para resolver, indícalo.

RESPONDE EN FORMATO JSON:
{{
    "resolved": true/false,
    "resolution": "Explicación clara de cómo se resolvió el conflicto o por qué no se pudo resolver",
    "resolved_conflicts": [
        {{
            "conflict_index": 1,
            "resolved": true/false,
            "correct_source": 1 o 2 o "both" o "unclear",
            "explanation": "Explicación de la resolución"
        }}
    ]
}}

IMPORTANTE: Responde SOLO con JSON válido, sin texto adicional."""
        
        try:
            from langchain_core.messages import HumanMessage
            response_obj = self.llm.invoke([HumanMessage(content=resolution_prompt)])
            response = response_obj.content if hasattr(response_obj, 'content') else str(response_obj)
            
            import json
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                resolution_data = json.loads(json_match.group(0))
                
                resolved_conflicts = []
                for resolved_conflict in resolution_data.get("resolved_conflicts", []):
                    conflict_idx = resolved_conflict.get("conflict_index", 1) - 1
                    if 0 <= conflict_idx < len(conflicts):
                        resolved_conflicts.append({
                            "conflict": conflicts[conflict_idx],
                            "resolved": resolved_conflict.get("resolved", False),
                            "correct_source": resolved_conflict.get("correct_source", "unclear"),
                            "explanation": resolved_conflict.get("explanation", "")
                        })
                
                return {
                    "resolved": resolution_data.get("resolved", False),
                    "resolution": resolution_data.get("resolution", ""),
                    "additional_results": additional_results,
                    "resolved_conflicts": resolved_conflicts
                }
            else:
                return {
                    "resolved": False,
                    "resolution": "No se pudo analizar la resolución de conflictos.",
                    "additional_results": additional_results,
                    "resolved_conflicts": []
                }
        except Exception as e:
            print(f"⚠️ [Company Knowledge] Error analizando resolución de conflictos: {e}")
            return {
                "resolved": False,
                "resolution": f"Error al analizar resolución: {str(e)}",
                "additional_results": additional_results,
                "resolved_conflicts": []
            }
    
    def _detect_conflicts_basic(
        self,
        results: List[Any],
        query: str
    ) -> Dict[str, Any]:
        """
        Detección básica de conflictos (fallback si LLM falla).
        """
        conflicts = []
        
        for i, result1 in enumerate(results[:10]):
            content1 = (result1.snippet or result1.content or "").lower()
            for j, result2 in enumerate(results[i+1:10], start=i+1):
                content2 = (result2.snippet or result2.content or "").lower()
                
                contradiction_keywords = [
                    ("increase", "decrease"), ("up", "down"), ("yes", "no"),
                    ("approved", "rejected"), ("success", "failure"),
                    ("high", "low"), ("more", "less"), ("better", "worse")
                ]
                
                for pos, neg in contradiction_keywords:
                    if pos in content1 and neg in content2:
                        conflicts.append({
                            "type": "contradiction",
                            "source1": {"app": result1.app_name, "name": result1.source_name},
                            "source2": {"app": result2.app_name, "name": result2.source_name},
                            "issue": f"Conflicting information: '{pos}' vs '{neg}'"
                        })
        
        has_conflicts = len(conflicts) > 0
        consensus_level = max(0.0, 1.0 - (len(conflicts) * 0.2))
        
        return {
            "has_conflicts": has_conflicts,
            "conflicts": conflicts[:5],
            "consensus_level": consensus_level
        }
    
    def _generate_enhanced_citations(
        self,
        results: List[Any],
        max_citations: int = 15
    ) -> str:
        """
        Genera citas mejoradas con snippets exactos y links clickeables.
        
        Returns:
            Markdown formateado con citas mejoradas
        """
        if not results:
            return ""
        
        citations_text = "\n\n---\n\n### 📚 Fuentes Consultadas\n\n"
        citations_text += f"**Total:** {len(results)} fuentes encontradas\n\n"
        
        for i, result in enumerate(results[:max_citations], 1):
            app_name = result.app_name
            source_name = result.source_name
            url = result.url or ""
            snippet = (result.snippet or result.content or "")[:300]  # Snippet de 300 chars
            
            citations_text += f"#### {i}. **[{app_name}]** {source_name}\n\n"
            
            if snippet:
                citations_text += f"> *{snippet}...*\n\n"
            
            if url:
                citations_text += f"🔗 [Abrir fuente original]({url})\n\n"
            else:
                citations_text += f"*Fuente: {source_name}*\n\n"
            
            citations_text += "---\n\n"
        
        if len(results) > max_citations:
            citations_text += f"\n*... y {len(results) - max_citations} fuentes adicionales*\n"
        
        return citations_text
    
    def _generate_realtime_sidebar_status(
        self,
        apps_searched: List[Any],
        results_found: Dict[str, int],
        current_app: Optional[str] = None,
        is_searching: bool = True
    ) -> str:
        """
        Genera estado del sidebar en tiempo real.
        
        Returns:
            Markdown formateado para el sidebar
        """
        status_text = "**🔍 Búsqueda en Tiempo Real**\n\n"
        
        if is_searching:
            status_text += "⏳ *Buscando en apps conectadas...*\n\n"
        
        if current_app:
            status_text += f"**Buscando ahora:** {current_app}\n\n"
        
        status_text += "**📱 Apps consultadas:**\n\n"
        
        for app in apps_searched:
            app_name = app.app_name if hasattr(app, 'app_name') else str(app)
            count = results_found.get(app_name, 0)
            status_icon = "✅" if count > 0 else "⏳"
            status_text += f"{status_icon} **{app_name}** ({count} resultados)\n"
        
        total_results = sum(results_found.values())
        status_text += f"\n**Total:** {total_results} resultados encontrados"
        
        return status_text
        
        return status_text
    
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

