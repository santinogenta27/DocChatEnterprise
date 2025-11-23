"""Enterprise API Mode - Procesamiento automático con Agentic AI avanzado."""

from __future__ import annotations

from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import json

from langchain_core.documents import Document
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI

from .config import AppConfig
from .document_processor import DocumentProcessor
from .retriever_builder import RetrieverBuilder
from .workflow import AgentWorkflow
from .memory import MemoryStore, ContextManager
from .advanced_agent import AdvancedAutonomousAgent
from .tools import (
    EmailTool, ReportTool, DatabaseTool, PresentationTool,
    IntegrationTool, TableAnalysisTool, SchedulerTool
)


class EnterpriseAPIMode:
    """
    Modo Enterprise API: Procesamiento automático con detección inteligente.
    
    Funcionalidades:
    - Procesa documentos automáticamente
    - Detecta problemas, oportunidades y patrones
    - Ejecuta acciones según reglas
    - Aprende continuamente
    """
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.processor = DocumentProcessor(config)
        self.retriever_builder = RetrieverBuilder(config)
        self.workflow = AgentWorkflow(config)
        self.advanced_agent = AdvancedAutonomousAgent(config) if config.enable_autonomous_agents else None
        
        # Memoria y contexto
        self.memory_store = MemoryStore(config.memory_dir, config.memory_retention_days) if config.enable_memory else None
        self.context_manager = ContextManager(self.memory_store, config) if self.memory_store else None
        
        # LLM para detección automática
        self.llm = ChatOpenAI(
            model=config.agentic_model,
            temperature=0.2,
            api_key=config.openai_api_key
        )
        
        # Herramientas Agentic AI avanzadas
        self.tools = {
            "email": EmailTool(config),
            "report": ReportTool(config),
            "database": DatabaseTool(config),
            "presentation": PresentationTool(config),
            "integration": IntegrationTool(config),
            "table_analysis": TableAnalysisTool(config),
            "scheduler": SchedulerTool(config),
        }
    
    def process_enterprise_documents(
        self,
        files: List,
        auto_detect: bool = True,
        rules: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Procesa documentos empresariales con detección automática.
        
        Args:
            files: Lista de archivos a procesar
            auto_detect: Si True, detecta problemas/oportunidades automáticamente
            rules: Lista de reglas/automatizaciones a aplicar
        
        Returns:
            Dict con resultados completos del procesamiento
        """
        results = {
            "status": "processing",
            "timestamp": datetime.now().isoformat(),
            "documents_processed": 0,
            "chunks_generated": 0,
            "insights": [],
            "problems_detected": [],
            "opportunities_detected": [],
            "patterns_found": [],
            "actions_taken": [],
            "summaries": {}
        }
        
        try:
            # 1. Procesar documentos
            print("Procesando documentos empresariales...")
            docs = self.processor.process(files)
            results["documents_processed"] = len(files)
            results["chunks_generated"] = len(docs)
            
            # 2. Generar resúmenes automáticos
            print("Generando resumenes automaticos...")
            retriever = self.retriever_builder.build_hybrid_retriever(docs)
            
            # Obtener todos los archivos únicos procesados desde los documentos
            from pathlib import Path
            from collections import defaultdict
            
            # Agrupar documentos por archivo fuente
            docs_by_file = defaultdict(list)
            for doc in docs:
                source = doc.metadata.get("source", "")
                if source:
                    # Normalizar el nombre del archivo
                    source_path = Path(source)
                    file_key = source_path.name  # Solo el nombre, sin ruta completa
                    docs_by_file[file_key].append(doc)
            
            # También crear un mapeo desde los archivos originales a sus nombres limpios
            # Priorizar el nombre original de Google Drive si está disponible
            file_name_mapping = {}
            for file_obj in files:
                # Obtener nombre original de Google Drive si está disponible
                original_name = getattr(file_obj, "original_name", None)
                if not original_name:
                    original_name = getattr(file_obj, "name", "documento")
                clean_name = Path(original_name).name
                file_name_mapping[clean_name] = original_name
                
                # También mapear el nombre temporal al original (para archivos de Drive)
                temp_name = getattr(file_obj, "name", "")
                if temp_name and temp_name != original_name:
                    temp_clean = Path(temp_name).name
                    file_name_mapping[temp_clean] = original_name
            
            # Generar resumen para CADA archivo único encontrado en los documentos
            print(f"   Encontrados {len(docs_by_file)} archivos únicos en los documentos procesados")
            
            for file_key, file_docs_list in docs_by_file.items():
                print(f"   Generando resumen para: {file_key} ({len(file_docs_list)} chunks)")
                
                # Usar el source del primer documento como referencia
                source_path = file_docs_list[0].metadata.get("source", "")
                original_file_name = file_name_mapping.get(file_key, source_path)
                
                # Generar resumen usando los documentos de este archivo
                summary = self._generate_automatic_summary(original_file_name, file_docs_list, retriever)
                results["summaries"][original_file_name] = summary
            
            # Verificar que todos los archivos subidos tengan resumen
            missing_summaries = []
            for file_obj in files:
                # Obtener nombre original de Google Drive si está disponible
                original_name = getattr(file_obj, "original_name", None)
                file_name = original_name if original_name else getattr(file_obj, "name", "documento")
                clean_name = Path(file_name).name
                
                # También obtener el nombre temporal (puede ser diferente del original)
                temp_name = getattr(file_obj, "name", "")
                temp_clean_name = Path(temp_name).name if temp_name else None
                
                # Verificar si ya tenemos un resumen para este archivo
                found = False
                for summary_file_name in results["summaries"].keys():
                    if Path(summary_file_name).name == clean_name:
                        found = True
                        break
                
                if not found:
                    missing_summaries.append(file_name)
                    # Intentar encontrar documentos por nombre limpio (original)
                    file_docs = [d for d in docs if Path(d.metadata.get("source", "")).name == clean_name]
                    
                    # Si no se encuentra por nombre original, intentar por nombre temporal
                    if not file_docs and temp_clean_name and temp_clean_name != clean_name:
                        file_docs = [d for d in docs if Path(d.metadata.get("source", "")).name == temp_clean_name]
                    
                    # También buscar por cualquier variación del nombre (sin espacios, con/sin extensiones)
                    if not file_docs:
                        # Buscar por hash del archivo si está disponible
                        try:
                            from docchat.utils import read_bytes, sha256_bytes
                            data = read_bytes(file_obj)
                            file_hash = sha256_bytes(data)
                            file_docs = [d for d in docs if d.metadata.get("hash", "") == file_hash]
                        except:
                            pass
                    
                    if file_docs:
                        print(f"   Generando resumen tardío para: {clean_name} ({len(file_docs)} chunks)")
                        summary = self._generate_automatic_summary(file_name, file_docs, retriever)
                        results["summaries"][file_name] = summary
                    else:
                        # Si no hay documentos, crear resumen básico
                        print(f"   ADVERTENCIA: No se encontraron chunks para {clean_name}")
                        results["summaries"][file_name] = {
                            "summary": f"Documento '{clean_name}' procesado pero no se encontraron chunks para análisis detallado. Puede ser un archivo vacío o con formato no soportado.",
                            "key_points": [],
                            "document_type": "unknown",
                            "relevant_date": "N/A",
                            "entities": [],
                            "topics": [],
                            "business_value": "Documento procesado pero sin contenido extraíble"
                        }
            
            print(f"   ✅ Resúmenes generados: {len(results['summaries'])}/{len(files)} archivos")
            
            # 3. Detección automática (si está habilitada)
            if auto_detect:
                print("Detectando problemas, oportunidades y patrones...")
                detection_results = self._auto_detect_issues_opportunities(docs, retriever)
                results["problems_detected"] = detection_results.get("problems", [])
                results["opportunities_detected"] = detection_results.get("opportunities", [])
                results["patterns_found"] = detection_results.get("patterns", [])
            
            # 4. Aplicar reglas/automatizaciones
            if rules:
                print("Ejecutando reglas y automatizaciones...")
                actions = self._apply_rules(docs, retriever, rules, results)
                results["actions_taken"] = actions
            
            # 5. Generar insights generales
            print("Generando insights generales...")
            insights = self._generate_insights(docs, retriever, results)
            results["insights"] = insights
            
            # 6. Guardar en memoria para aprendizaje continuo
            if self.context_manager:
                self._save_to_memory(docs, results)
            
            results["status"] = "completed"
            print("✅ Procesamiento Enterprise API completado exitosamente!")
            print(f"   - Documentos: {results.get('documents_processed', 0)}")
            print(f"   - Chunks: {results.get('chunks_generated', 0)}")
            print(f"   - Problemas detectados: {len(results.get('problems_detected', []))}")
            print(f"   - Oportunidades detectadas: {len(results.get('opportunities_detected', []))}")
            print(f"   - Patrones encontrados: {len(results.get('patterns_found', []))}")
            
        except Exception as e:
            results["status"] = "error"
            results["error"] = str(e)
            print(f"ERROR en procesamiento enterprise: {e}")
        
        return results
    
    def _generate_automatic_summary(
        self,
        file_name: str,
        docs: List[Document],
        retriever
    ) -> Dict[str, Any]:
        """Genera resumen automático profesional y extenso de un documento."""
        # docs ya viene filtrado por archivo desde el llamador
        from pathlib import Path
        clean_file_name = Path(file_name).name
        
        # Verificar que tengamos documentos
        if not docs:
            return {
                "summary": f"No se pudo generar resumen para '{clean_file_name}'. No se encontraron chunks.",
                "key_points": [],
                "document_type": "unknown",
                "relevant_date": "N/A",
                "entities": [],
                "topics": [],
                "business_value": "N/A"
            }
        
        file_docs = docs
        
        # Construir contexto más completo (más chunks, más contenido)
        # Tomar hasta 20 chunks y hasta 1000 caracteres por chunk
        context_parts = []
        total_chars = 0
        max_chars = 15000  # Aumentar contexto para resúmenes mejores
        
        for doc in file_docs[:25]:  # Más chunks
            content = doc.page_content[:1000]  # Más contenido por chunk
            if total_chars + len(content) <= max_chars:
                context_parts.append(content)
                total_chars += len(content)
            else:
                remaining = max_chars - total_chars
                if remaining > 100:
                    context_parts.append(content[:remaining])
                break
        
        context = "\n\n---\n\n".join(context_parts)
        
        # Extraer nombre del archivo limpio
        from pathlib import Path
        clean_file_name = Path(file_name).name
        
        prompt = f"""Eres un analista experto de documentos empresariales. Analiza este documento en profundidad y genera un resumen ejecutivo profesional, extenso y altamente útil.

DOCUMENTO: {clean_file_name}

CONTENIDO DEL DOCUMENTO:
{context}

INSTRUCCIONES:
Genera un análisis completo y profesional que incluya:

1. RESUMEN EJECUTIVO (4-6 párrafos extensos):
   - Contexto y propósito del documento
   - Ideas principales y argumentos centrales
   - Conclusiones y recomendaciones clave
   - Valor e importancia del contenido
   - Aplicaciones prácticas y relevancia empresarial

2. PUNTOS CLAVE (8-12 puntos detallados):
   - Conceptos fundamentales explicados
   - Hallazgos importantes
   - Recomendaciones específicas
   - Insights valiosos para el negocio

3. TIPO DE DOCUMENTO:
   - Clasificación precisa (libro, artículo académico, informe, guía, whitepaper, etc.)
   - Género y categoría temática

4. FECHA/PERÍODO RELEVANTE:
   - Fecha de publicación si está disponible
   - Período temporal relevante
   - Contexto histórico si aplica

5. ENTIDADES PRINCIPALES:
   - Autores, organizaciones, empresas mencionadas
   - Personas clave citadas
   - Instituciones relevantes

6. TEMAS Y ÁREAS DE CONOCIMIENTO:
   - Temas principales cubiertos
   - Disciplinas o áreas de conocimiento
   - Industrias o sectores relevantes

7. VALOR PARA EL NEGOCIO:
   - Aplicaciones prácticas
   - Insights accionables
   - Oportunidades identificadas

IMPORTANTE:
- Sé específico y detallado
- Incluye información concreta del documento
- Evita generalidades
- Proporciona valor real para la toma de decisiones
- Usa lenguaje profesional pero claro

Responde ÚNICAMENTE en formato JSON válido:
{{
    "summary": "resumen ejecutivo extenso y profesional de 4-6 párrafos con información valiosa y específica",
    "key_points": ["punto clave 1 detallado", "punto clave 2 detallado", ...],
    "document_type": "tipo específico del documento",
    "relevant_date": "fecha o período si existe",
    "entities": ["entidad1", "entidad2", ...],
    "topics": ["tema1", "tema2", ...],
    "business_value": "valor e importancia para el negocio"
}}"""
        
        try:
            response = self.llm.invoke(prompt).content.strip()
            # Intentar parsear JSON
            if response.startswith("```json"):
                response = response.replace("```json", "").replace("```", "").strip()
            elif response.startswith("```"):
                response = response.replace("```", "").strip()
            
            summary_data = json.loads(response)
            
            # Validar que el resumen no sea genérico
            summary_text = summary_data.get("summary", "")
            generic_phrases = [
                "contiene información relevante sobre múltiples temas",
                "se identificaron",
                "secciones principales con contenido sustancial",
                "análisis del documento",
                "documento procesado"
            ]
            
            is_generic = any(phrase.lower() in summary_text.lower() for phrase in generic_phrases)
            
            # Si el resumen es genérico o muy corto, intentar mejorarlo con más contexto
            if is_generic or len(summary_text) < 300:
                # Intentar generar un resumen mejor con más chunks
                if len(file_docs) > 10:
                    # Usar más contexto para generar mejor resumen
                    extended_context = []
                    for doc in file_docs[:30]:
                        content = doc.page_content[:800]
                        if content.strip():
                            extended_context.append(content)
                    
                    if extended_context:
                        extended_prompt = f"""Genera un resumen ejecutivo profesional y específico para el documento '{clean_file_name}'.

CONTENIDO EXTENDIDO:
{chr(10).join(extended_context[:20])}

IMPORTANTE: 
- Sé ESPECÍFICO sobre el contenido real del documento
- NO uses frases genéricas como "contiene información relevante" o "múltiples temas"
- Incluye detalles concretos, nombres, conceptos, ideas específicas del documento
- Si es un libro, menciona el autor, temas principales, argumentos clave
- Si es un artículo, menciona el tema específico, hallazgos, conclusiones

Responde en JSON:
{{
    "summary": "resumen específico y detallado de 4-6 párrafos",
    "key_points": ["punto específico 1", "punto específico 2", ...],
    "document_type": "tipo específico",
    "relevant_date": "fecha si existe",
    "entities": ["entidad1", "entidad2"],
    "topics": ["tema1", "tema2"],
    "business_value": "valor específico"
}}"""
                        try:
                            improved_response = self.llm.invoke(extended_prompt).content.strip()
                            if improved_response.startswith("```json"):
                                improved_response = improved_response.replace("```json", "").replace("```", "").strip()
                            elif improved_response.startswith("```"):
                                improved_response = improved_response.replace("```", "").strip()
                            improved_data = json.loads(improved_response)
                            if len(improved_data.get("summary", "")) > 300 and not any(phrase.lower() in improved_data.get("summary", "").lower() for phrase in generic_phrases):
                                return improved_data
                        except:
                            pass
            
            # Si aún es genérico, marcar como tal pero retornar
            if is_generic:
                summary_data["_is_generic"] = True
            
            return summary_data
        except Exception as e:
            # Si hay un error pero tenemos documentos, intentar generar resumen básico
            if not file_docs:
                return {
                    "summary": f"No se pudo generar resumen para '{clean_file_name}'. No se encontraron chunks extraíbles del documento.",
                    "key_points": [],
                    "document_type": "unknown",
                    "relevant_date": "N/A",
                    "entities": [],
                    "topics": [],
                    "business_value": "Documento procesado pero sin contenido extraíble"
                }
            
            # Fallback: generar resumen básico pero más completo
            key_points = []
            for doc in file_docs[:10]:
                content = doc.page_content.strip()
                if len(content) > 50:
                    key_points.append(content[:200])
            
            return {
                "summary": f"Análisis del documento '{clean_file_name}'. El documento contiene información relevante sobre múltiples temas. Se identificaron {len(file_docs)} secciones principales con contenido sustancial.",
                "key_points": key_points[:8],
                "document_type": "documento",
                "relevant_date": "N/A",
                "entities": [],
                "topics": [],
                "business_value": "Documento procesado para análisis empresarial",
                "error": str(e)
            }
    
    def _auto_detect_issues_opportunities(
        self,
        docs: List[Document],
        retriever
    ) -> Dict[str, List]:
        """Detecta automáticamente problemas, oportunidades y patrones."""
        # Obtener contexto representativo
        sample_docs = docs[:50]  # Muestra representativa
        context = "\n\n".join([d.page_content[:300] for d in sample_docs])
        
        prompt = f"""Analiza estos documentos empresariales y detecta automáticamente:

1. PROBLEMAS POTENCIALES:
   - Riesgos legales, financieros, operacionales
   - Contradicciones o inconsistencias
   - Fechas vencidas o próximas a vencer
   - Valores fuera de rango esperado

2. OPORTUNIDADES:
   - Mejoras sugeridas
   - Optimizaciones posibles
   - Sinergias identificadas
   - Oportunidades de negocio

3. PATRONES:
   - Tendencias identificadas
   - Correlaciones entre documentos
   - Comportamientos recurrentes

Contenido a analizar:
{context[:10000]}

Responde en formato JSON:
{{
    "problems": [
        {{
            "type": "tipo de problema",
            "severity": "alta/media/baja",
            "description": "descripción",
            "source": "documento origen",
            "recommendation": "recomendación"
        }}
    ],
    "opportunities": [
        {{
            "type": "tipo de oportunidad",
            "impact": "alto/medio/bajo",
            "description": "descripción",
            "source": "documento origen",
            "action": "acción sugerida"
        }}
    ],
    "patterns": [
        {{
            "type": "tipo de patrón",
            "description": "descripción del patrón",
            "frequency": "alta/media/baja",
            "implication": "implicación"
        }}
    ]
}}"""
        
        try:
            response = self.llm.invoke(prompt).content.strip()
            if response.startswith("```json"):
                response = response.replace("```json", "").replace("```", "").strip()
            elif response.startswith("```"):
                response = response.replace("```", "").strip()
            
            detection_data = json.loads(response)
            return detection_data
        except Exception as e:
            print(f"ERROR en deteccion automatica: {e}")
            return {"problems": [], "opportunities": [], "patterns": []}
    
    def _apply_rules(
        self,
        docs: List[Document],
        retriever,
        rules: List[Dict],
        results: Dict
    ) -> List[Dict]:
        """Aplica reglas y automatizaciones definidas."""
        actions_taken = []
        
        for rule in rules:
            rule_type = rule.get("type", "condition")
            condition = rule.get("condition")
            action = rule.get("action")
            
            # Evaluar condición
            if self._evaluate_condition(condition, docs, results):
                # Ejecutar acción
                action_result = self._execute_action(action, docs, results)
                actions_taken.append({
                    "rule": rule.get("name", "unnamed"),
                    "condition_met": True,
                    "action_executed": action_result
                })
        
        return actions_taken
    
    def _evaluate_condition(
        self,
        condition: Dict,
        docs: List[Document],
        results: Dict
    ) -> bool:
        """Evalúa una condición de regla."""
        condition_type = condition.get("type")
        
        if condition_type == "keyword":
            keyword = condition.get("keyword", "").lower()
            for doc in docs:
                if keyword in doc.page_content.lower():
                    return True
        
        elif condition_type == "problem_detected":
            problem_type = condition.get("problem_type")
            for problem in results.get("problems_detected", []):
                if problem.get("type") == problem_type:
                    return True
        
        elif condition_type == "pattern":
            pattern_name = condition.get("pattern_name")
            for pattern in results.get("patterns_found", []):
                if pattern.get("type") == pattern_name:
                    return True
        
        return False
    
    def _execute_action(
        self,
        action: Dict,
        docs: List[Document],
        results: Dict
    ) -> Dict:
        """Ejecuta una acción de automatización."""
        action_type = action.get("type")
        
        if action_type == "notify":
            # Notificar (email, Slack, etc.)
            return {"status": "notified", "channel": action.get("channel")}
        
        elif action_type == "generate_report":
            # Generar reporte automático usando herramienta avanzada
            report_tool = self.tools.get("report")
            if report_tool:
                from datetime import datetime
                report_data = {
                    "summary": "Reporte automático generado por Enterprise API",
                    "timestamp": datetime.now().isoformat(),
                    "documents_analyzed": len(docs),
                    "problems": results.get("problems_detected", []),
                    "opportunities": results.get("opportunities_detected", [])
                }
                result = report_tool.execute(
                    data=report_data,
                    format="excel",
                    title="Reporte Automático Enterprise API"
                )
                if result.success:
                    return {"status": "report_generated", "path": str(result.data) if result.data else None}
                return {"status": "report_failed", "error": result.message}
            return {"status": "report_failed", "error": "Report tool not available"}
        
        elif action_type == "flag_for_review":
            # Marcar para revisión
            return {"status": "flagged", "priority": action.get("priority", "medium")}
        
        return {"status": "executed", "action_type": action_type}
    
    def _generate_insights(
        self,
        docs: List[Document],
        retriever,
        results: Dict
    ) -> List[Dict]:
        """Genera insights generales del procesamiento."""
        insights = []
        
        # Insight 1: Resumen general
        insights.append({
            "type": "summary",
            "title": "Resumen General",
            "content": f"Se procesaron {results['documents_processed']} documentos generando {results['chunks_generated']} chunks de información."
        })
        
        # Insight 2: Problemas críticos
        critical_problems = [p for p in results.get("problems_detected", []) if p.get("severity") == "alta"]
        if critical_problems:
            insights.append({
                "type": "alert",
                "title": "Problemas Críticos Detectados",
                "content": f"Se detectaron {len(critical_problems)} problemas de alta severidad que requieren atención inmediata.",
                "items": critical_problems[:5]
            })
        
        # Insight 3: Oportunidades
        high_impact_opps = [o for o in results.get("opportunities_detected", []) if o.get("impact") == "alto"]
        if high_impact_opps:
            insights.append({
                "type": "opportunity",
                "title": "Oportunidades de Alto Impacto",
                "content": f"Se identificaron {len(high_impact_opps)} oportunidades con alto potencial de impacto.",
                "items": high_impact_opps[:5]
            })
        
        return insights
    
    def _save_to_memory(
        self,
        docs: List[Document],
        results: Dict
    ):
        """Guarda información en memoria para aprendizaje continuo."""
        if not self.context_manager:
            return
        
        # Guardar resúmenes
        for file_name, summary in results.get("summaries", {}).items():
            self.context_manager.add_query(
                query=f"Resumen automático de {file_name}",
                answer=summary.get("summary", ""),
                sources=[file_name],
                metadata={
                    "type": "auto_summary",
                    "key_points": summary.get("key_points", []),
                    "document_type": summary.get("document_type", "unknown")
                }
            )
        
        # Guardar problemas y oportunidades detectados
        for problem in results.get("problems_detected", []):
            self.context_manager.add_query(
                query=f"Problema detectado: {problem.get('type', 'unknown')}",
                answer=problem.get("description", ""),
                sources=[],
                metadata={
                    "type": "auto_detection",
                    "detection_type": "problem",
                    "severity": problem.get("severity", "media")
                }
            )

