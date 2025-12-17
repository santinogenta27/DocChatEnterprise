"""Intelligence Contract Mode - Procesamiento automático con Agentic AI avanzado."""

from __future__ import annotations

from typing import List, Dict, Any, Optional, Iterator
from datetime import datetime
from pathlib import Path
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

from langchain_core.documents import Document
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI

from .config import AppConfig
from .document_processor import DocumentProcessor
try:
    from docling.document_converter import DocumentConverter
    DOCLING_AVAILABLE = True
except ImportError:
    DOCLING_AVAILABLE = False
    DocumentConverter = None
from .retriever_builder import RetrieverBuilder
from .workflow import AgentWorkflow
from .memory import MemoryStore, ContextManager
from .advanced_agent import AdvancedAutonomousAgent
from .tools import (
    EmailTool, ReportTool, DatabaseTool, PresentationTool,
    IntegrationTool, TableAnalysisTool, SchedulerTool
)


class IntelligenceContractMode:
    """
    Modo Intelligence Contract: Procesamiento automático con detección inteligente.
    
    Funcionalidades:
    - Procesa documentos automáticamente
    - Detecta problemas, oportunidades y patrones
    - Ejecuta acciones según reglas
    - Aprende continuamente
    """
    
    def __init__(self, config: AppConfig, provider: str = "openai"):
        self.config = config
        self.provider = provider
        self.processor = DocumentProcessor(config)
        self.retriever_builder = RetrieverBuilder(config)
        self.workflow = AgentWorkflow(config)
        self.advanced_agent = AdvancedAutonomousAgent(config) if config.enable_autonomous_agents else None
        
        # Memoria y contexto
        self.memory_store = MemoryStore(config.memory_dir, config.memory_retention_days) if config.enable_memory else None
        self.context_manager = ContextManager(self.memory_store, config) if self.memory_store else None
        
        # LLM para detección automática - SIN LÍMITE DE TOKENS (la API decide)
        from docchat.utils.llm_factory import create_llm
        self.llm = create_llm(
            provider=provider,
            model=config.agentic_model,
            temperature=0.2,
            api_key=config.openai_api_key if provider == "openai" else config.anthropic_api_key,
            # max_tokens REMOVIDO - dejar que la API decida la longitud de respuesta
            request_timeout=300  # Timeout más largo para respuestas largas
        )
        
        # LLM rápido para tareas simples (detección, insights)
        # ACTUALIZADO: Usar Claude Haiku 4.5 (más rápido y económico)
        fast_model = "gpt-4o-mini" if provider == "openai" else "claude-haiku-4-5-20251001"
        self.fast_llm = create_llm(
            provider=provider,
            model=fast_model,
            temperature=0.2,
            api_key=config.openai_api_key if provider == "openai" else config.anthropic_api_key,
            # max_tokens REMOVIDO - dejar que la API decida la longitud de respuesta
            request_timeout=180  # Timeout más largo para respuestas largas
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
    
    def process_documents_streaming(
        self,
        files: List,
        auto_detect: bool = True,
        rules: Optional[List[Dict]] = None
    ) -> Iterator[str]:
        """Procesa documentos con streaming de resultados (generador) usando Intelligence Contract."""
        yield "## 🚀 Procesamiento Intelligence Contract Iniciado\n\n"
        yield "📄 Procesando documentos...\n\n"
        
        try:
            # 1. Procesar documentos
            docs = self.processor.process(files)
            yield f"✅ **Documentos procesados**: {len(files)}\n"
            yield f"✅ **Chunks generados**: {len(docs)}\n\n"
            
            # 2. Generar resúmenes automáticos con streaming
            yield "### 📄 Generando Resúmenes Automáticos...\n\n"
            import uuid
            session_namespace = f"intelligence_contract_{uuid.uuid4().hex[:8]}"
            retriever = self.retriever_builder.build_hybrid_retriever(docs, namespace=session_namespace)
            
            # Agrupar documentos por archivo
            from collections import defaultdict
            docs_by_file = defaultdict(list)
            file_key_to_original_name = {}
            
            for doc in docs:
                source = doc.metadata.get("source", "")
                if source:
                    doc_hash = doc.metadata.get("hash", "")
                    if doc_hash:
                        file_key = f"hash_{doc_hash}"
                    else:
                        source_path = Path(source)
                        file_key = source_path.name
                    docs_by_file[file_key].append(doc)
                    if file_key not in file_key_to_original_name:
                        file_key_to_original_name[file_key] = source
            
            # Generar resúmenes en paralelo y emitir mientras se completan
            processed_clean_names = set()
            summary_tasks = []
            for file_key, file_docs_list in docs_by_file.items():
                original_file_name = file_key_to_original_name.get(file_key, file_docs_list[0].metadata.get("source", ""))
                clean_file_name = Path(original_file_name).name
                if clean_file_name in processed_clean_names:
                    continue
                processed_clean_names.add(clean_file_name)
                summary_tasks.append((original_file_name, file_docs_list, clean_file_name))
            
            summaries = {}
            max_workers = min(3, len(summary_tasks))
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_file = {
                    executor.submit(self._generate_automatic_summary, original_file_name, file_docs_list, retriever): 
                    (original_file_name, clean_file_name) 
                    for original_file_name, file_docs_list, clean_file_name in summary_tasks
                }
                
                for future in as_completed(future_to_file):
                    original_file_name, clean_file_name = future_to_file[future]
                    try:
                        summary = future.result()
                        summaries[original_file_name] = summary
                        # Emitir resumen inmediatamente
                        yield f"#### {clean_file_name}\n\n"
                        yield f"**Tipo de Documento**: {summary.get('document_type', 'N/A')}\n\n"
                        yield f"**Resumen Ejecutivo**:\n{summary.get('summary', 'N/A')}\n\n"
                        if summary.get('key_points'):
                            yield f"**Puntos Clave** ({len(summary['key_points'])}):\n"
                            for i, point in enumerate(summary['key_points'][:10], 1):
                                yield f"{i}. {point}\n"
                            yield "\n"
                        if summary.get('topics'):
                            yield f"**Temas**: {', '.join(summary['topics'][:5])}\n\n"
                        if summary.get('business_value'):
                            yield f"**Valor para el Negocio**: {summary.get('business_value')}\n\n"
                        if summary.get('entities'):
                            yield f"**Entidades Principales**: {', '.join(summary['entities'][:5])}\n\n"
                        yield "---\n\n"
                    except Exception as e:
                        yield f"❌ Error en {clean_file_name}: {str(e)[:100]}\n\n"
            
            # 3. Detección automática (si está habilitada)
            detection_results = {"problems": [], "opportunities": [], "patterns": []}
            if auto_detect:
                yield "### 🔍 Detectando Problemas, Oportunidades y Patrones...\n\n"
                detection_results = self._auto_detect_issues_opportunities(docs, retriever)
                
                if detection_results.get('problems'):
                    yield "### ⚠️ Problemas Detectados\n\n"
                    for problem in detection_results['problems']:
                        yield f"- **{problem.get('type', 'Unknown')}** ({problem.get('severity', 'N/A')}): {problem.get('description', 'N/A')}\n"
                    yield "\n"
                
                if detection_results.get('opportunities'):
                    yield "### 💡 Oportunidades Detectadas\n\n"
                    for opp in detection_results['opportunities']:
                        yield f"- **{opp.get('type', 'Unknown')}** ({opp.get('impact', 'N/A')}): {opp.get('description', 'N/A')}\n"
                    yield "\n"
                
                if detection_results.get('patterns'):
                    yield "### 🔍 Patrones Encontrados\n\n"
                    for pattern in detection_results['patterns']:
                        yield f"- **{pattern.get('type', 'Unknown')}**: {pattern.get('description', 'N/A')}\n"
                    yield "\n"
            
            # 4. Insights generales
            yield "### 💡 Insights Generales\n\n"
            insights = self._generate_insights(docs, retriever, {
                "documents_processed": len(files),
                "chunks_generated": len(docs),
                "problems_detected": detection_results.get('problems', []),
                "opportunities_detected": detection_results.get('opportunities', []),
                "patterns_found": detection_results.get('patterns', []),
                "summaries": summaries
            })
            
            for insight in insights:
                yield f"#### {insight.get('title', 'Insight')}\n"
                yield f"{insight.get('content', 'N/A')}\n\n"
            
            yield "\n✅ **Procesamiento completado exitosamente!**\n"
            
        except Exception as e:
            yield f"\n❌ **Error**: {str(e)}\n"
    
    def process_documents(
        self,
        files: List,
        auto_detect: bool = True,
        rules: Optional[List[Dict]] = None,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        Procesa documentos empresariales con Intelligence Contract.
        
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
            print("Procesando documentos empresariales (Intelligence Contract)...")
            docs = self.processor.process(files)
            results["documents_processed"] = len(files)
            results["chunks_generated"] = len(docs)
            
            # Si no se generaron chunks, intentar procesar directamente con MultiFormatProcessor como último recurso
            if not docs or len(docs) == 0:
                print("⚠️ El procesador estándar no generó chunks.")
                print("   💡 Posibles causas: PDF encriptado, formato no soportado, o error en procesamiento.")
                print("   🔄 Intentando procesamiento directo con MultiFormatProcessor (Docling)...")
                try:
                    from docchat.multi_format_processor import MultiFormatProcessor
                    direct_processor = MultiFormatProcessor(self.config)
                    # Procesar archivos directamente
                    direct_docs = direct_processor.process(files)
                    if direct_docs and len(direct_docs) > 0:
                        docs = direct_docs
                        results["chunks_generated"] = len(docs)
                        print(f"   ✅ Procesamiento directo exitoso: {len(docs)} chunks generados")
                        results["status"] = "success"  # Actualizar estado a success si el fallback funcionó
                    else:
                        print("   ⚠️ Procesamiento directo tampoco generó chunks")
                except Exception as e:
                    print(f"   ⚠️ Error en procesamiento directo: {str(e)[:200]}")
                    import traceback
                    traceback.print_exc()
            
            # 2. Generar resúmenes automáticos
            if not docs or len(docs) == 0:
                results["status"] = "error"
                results["error"] = "No se pudieron procesar los documentos. El PDF puede estar encriptado o corrupto."
                print("ERROR en procesamiento Intelligence Contract: No hay documentos procesados para indexar.")
                return results
            
            print("Generando resúmenes automáticos (Intelligence Contract)...")
            # Usar un namespace único para esta sesión para evitar mezclar con documentos previos
            import uuid
            session_namespace = f"intelligence_contract_{uuid.uuid4().hex[:8]}"
            retriever = self.retriever_builder.build_hybrid_retriever(docs, namespace=session_namespace)
            
            # Obtener todos los archivos únicos procesados desde los documentos
            from collections import defaultdict
            
            def normalize_filename(name):
                """Normaliza el nombre del archivo removiendo variaciones comunes de duplicados."""
                name_lower = name.lower()
                variations = [" - copia", "- copia", " - copy", "- copy", " (copia)", "(copia)", " (copy)", "(copy)", " - copia.pdf", "- copia.pdf"]
                for variation in variations:
                    if name_lower.endswith(variation):
                        base = name[:-len(variation)]
                        ext = Path(name).suffix
                        return base + ext
                return name
            
            file_hash_to_original_name: Dict[str, str] = {}
            normalized_name_to_original: Dict[str, str] = {}
            
            for file_obj in files:
                original_name = getattr(file_obj, "original_name", None)
                if not original_name:
                    original_name = getattr(file_obj, "name", "documento")
                
                normalized = normalize_filename(Path(original_name).name)
                
                if normalized not in normalized_name_to_original:
                    normalized_name_to_original[normalized] = original_name
                else:
                    existing = normalized_name_to_original[normalized]
                    existing_lower = existing.lower()
                    original_lower = original_name.lower()
                    if ("copia" in existing_lower or "copy" in existing_lower) and ("copia" not in original_lower and "copy" not in original_lower):
                        normalized_name_to_original[normalized] = original_name
                    elif "drive_" in existing and "drive_" not in original_name:
                        normalized_name_to_original[normalized] = original_name
                
                try:
                    from docchat.utils import read_bytes, sha256_bytes
                    data = read_bytes(file_obj)
                    file_hash = sha256_bytes(data)
                    if file_hash not in file_hash_to_original_name:
                        file_hash_to_original_name[file_hash] = original_name
                    else:
                        existing = file_hash_to_original_name[file_hash]
                        existing_lower = existing.lower()
                        original_lower = original_name.lower()
                        if ("copia" in existing_lower or "copy" in existing_lower) and ("copia" not in original_lower and "copy" not in original_lower):
                            file_hash_to_original_name[file_hash] = original_name
                        elif "drive_" in existing and "drive_" not in original_name:
                            file_hash_to_original_name[file_hash] = original_name
                except:
                    pass
            
            docs_by_file: Dict[str, List[Document]] = defaultdict(list)
            file_key_to_original_name: Dict[str, str] = {}
            
            for doc in docs:
                source = doc.metadata.get("source", "")
                if source:
                    source_path = Path(source)
                    source_name = source_path.name
                    
                    doc_hash = doc.metadata.get("hash", "")
                    if doc_hash and doc_hash in file_hash_to_original_name:
                        file_key = f"hash_{doc_hash}"
                        original_name = file_hash_to_original_name[doc_hash]
                    else:
                        normalized_source = normalize_filename(source_name)
                        file_key = f"normalized_{normalized_source}"
                        
                        if normalized_source in normalized_name_to_original:
                            original_name = normalized_name_to_original[normalized_source]
                        else:
                            original_name = None
                            for file_obj in files:
                                temp_name = getattr(file_obj, "name", "")
                                temp_normalized = normalize_filename(Path(temp_name).name)
                                if temp_normalized == normalized_source:
                                    original_name = getattr(file_obj, "original_name", None) or temp_name
                                    break
                            if not original_name:
                                original_name = source
                            normalized_name_to_original[normalized_source] = original_name
                    
                    docs_by_file[file_key].append(doc)
                    if file_key not in file_key_to_original_name:
                        file_key_to_original_name[file_key] = original_name
                    else:
                        existing = file_key_to_original_name[file_key]
                        existing_lower = existing.lower()
                        original_lower = original_name.lower()
                        if ("copia" in existing_lower or "copy" in existing_lower) and ("copia" not in original_lower and "copy" not in original_lower):
                            file_key_to_original_name[file_key] = original_name
                        elif "drive_" in existing and "drive_" not in original_name:
                            file_key_to_original_name[file_key] = original_name
            
            print(f"   Encontrados {len(docs_by_file)} archivos únicos en los documentos procesados")
            
            processed_clean_names = set()
            summary_tasks = []
            for file_key, file_docs_list in docs_by_file.items():
                original_file_name = file_key_to_original_name.get(file_key, file_docs_list[0].metadata.get("source", ""))
                clean_file_name = Path(original_file_name).name
                
                if clean_file_name in processed_clean_names:
                    print(f"   ⚠️ Saltando {clean_file_name} (ya procesado como duplicado)")
                    continue
                processed_clean_names.add(clean_file_name)
                
                summary_tasks.append((original_file_name, file_docs_list, clean_file_name))
            
            max_workers = min(3, len(summary_tasks))
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_file = {
                    executor.submit(self._generate_automatic_summary, original_file_name, file_docs_list, retriever): 
                    (original_file_name, clean_file_name) 
                    for original_file_name, file_docs_list, clean_file_name in summary_tasks
                }
                
                for future in as_completed(future_to_file):
                    original_file_name, clean_file_name = future_to_file[future]
                    try:
                        summary = future.result()
                        results["summaries"][original_file_name] = summary
                        print(f"   ✅ Resumen completado: {clean_file_name}")
                    except Exception as e:
                        print(f"   ❌ Error generando resumen para {clean_file_name}: {str(e)[:100]}")
                        results["summaries"][original_file_name] = {
                            "summary": f"Error generando resumen: {str(e)[:200]}",
                            "key_points": [],
                            "document_type": "unknown",
                            "relevant_date": "N/A",
                            "entities": [],
                            "topics": [],
                            "business_value": "N/A"
                        }
            
            missing_summaries = []
            for file_obj in files:
                original_name = getattr(file_obj, "original_name", None)
                file_name = original_name if original_name else getattr(file_obj, "name", "documento")
                clean_name = Path(file_name).name
                
                temp_name = getattr(file_obj, "name", "")
                temp_clean_name = Path(temp_name).name if temp_name else None
                
                found = False
                if clean_name in processed_clean_names:
                    found = True
                else:
                    for summary_file_name in results["summaries"].keys():
                        if Path(summary_file_name).name == clean_name:
                            found = True
                            processed_clean_names.add(clean_name)
                            break
                
                if not found:
                    missing_summaries.append(file_name)
                    file_docs = [d for d in docs if Path(d.metadata.get("source", "")).name == clean_name]
                    
                    if not file_docs and temp_clean_name and temp_clean_name != clean_name:
                        file_docs = [d for d in docs if Path(d.metadata.get("source", "")).name == temp_clean_name]
                    
                    if not file_docs:
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
            
            if auto_detect:
                print("Detectando problemas, oportunidades y patrones (Intelligence Contract)...")
                detection_results = self._auto_detect_issues_opportunities(docs, retriever)
                results["problems_detected"] = detection_results.get("problems", [])
                results["opportunities_detected"] = detection_results.get("opportunities", [])
                results["patterns_found"] = detection_results.get("patterns", [])
            
            if rules:
                print("Ejecutando reglas y automatizaciones (Intelligence Contract)...")
                actions = self._apply_rules(docs, retriever, rules, results)
                results["actions_taken"] = actions
            
            print("Generando insights generales (Intelligence Contract)...")
            insights = self._generate_insights(docs, retriever, results)
            results["insights"] = insights
            
            if self.context_manager:
                self._save_to_memory(docs, results)
            
            results["status"] = "completed"
            print("✅ Procesamiento Intelligence Contract completado exitosamente!")
            print(f"   - Documentos: {results.get('documents_processed', 0)}")
            print(f"   - Chunks: {results.get('chunks_generated', 0)}")
            print(f"   - Problemas detectados: {len(results.get('problems_detected', []))}")
            print(f"   - Oportunidades detectadas: {len(results.get('opportunities_detected', []))}")
            print(f"   - Patrones encontrados: {len(results.get('patterns_found', []))}")
            
        except Exception as e:
            results["status"] = "error"
            results["error"] = str(e)
            print(f"ERROR en procesamiento Intelligence Contract: {e}")
        
        return results
    
    def _generate_automatic_summary(
        self,
        file_name: str,
        docs: List[Document],
        retriever
    ) -> Dict[str, Any]:
        """Genera resumen automático profesional y extenso de un documento."""
        from pathlib import Path
        clean_file_name = Path(file_name).name
        
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
        
        context_parts = []
        total_chars = 0
        max_chars = 50000 if self.provider == "openai" else 80000
        max_chunks = 50 if self.provider == "openai" else 80
        
        for doc in file_docs[:max_chunks]:
            content = doc.page_content[:2000]
            if total_chars + len(content) <= max_chars:
                context_parts.append(content)
                total_chars += len(content)
            else:
                remaining = max_chars - total_chars
                if remaining > 200:
                    context_parts.append(content[:remaining])
                break
        
        context = "\n\n---\n\n".join(context_parts)
        
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
            if response.startswith("```json"):
                response = response.replace("```json", "").replace("```", "").strip()
            elif response.startswith("```"):
                response = response.replace("```", "").strip()
            
            summary_data = json.loads(response)
            
            summary_text = summary_data.get("summary", "")
            generic_phrases = [
                "contiene información relevante sobre múltiples temas",
                "se identificaron",
                "secciones principales con contenido sustancial",
                "análisis del documento",
                "documento procesado"
            ]
            
            is_generic = any(phrase.lower() in summary_text.lower() for phrase in generic_phrases)
            
            if is_generic or len(summary_text) < 300:
                if len(file_docs) > 10:
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
            
            if is_generic:
                summary_data["_is_generic"] = True
            
            return summary_data
        except Exception as e:
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
        sample_docs = docs[:50]
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
            response = self.fast_llm.invoke(prompt).content.strip()
            if response.startswith("```json"):
                response = response.replace("```json", "").replace("```", "").strip()
            elif response.startswith("```"):
                response = response.replace("```", "").strip()
            
            detection_data = json.loads(response)
            return detection_data
        except Exception as e:
            print(f"ERROR en deteccion automatica (Intelligence Contract): {e}")
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
            
            if self._evaluate_condition(condition, docs, results):
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
            return {"status": "notified", "channel": action.get("channel")}
        
        elif action_type == "generate_report":
            report_tool = self.tools.get("report")
            if report_tool:
                report_data = {
                    "summary": "Reporte automático generado por Intelligence Contract",
                    "timestamp": datetime.now().isoformat(),
                    "documents_analyzed": len(docs),
                    "problems": results.get("problems_detected", []),
                    "opportunities": results.get("opportunities_detected", [])
                }
                result = report_tool.execute(
                    data=report_data,
                    format="excel",
                    title="Reporte Automático Intelligence Contract"
                )
                if result.success:
                    return {"status": "report_generated", "path": str(result.data) if result.data else None}
                return {"status": "report_failed", "error": result.message}
            return {"status": "report_failed", "error": "Report tool not available"}
        
        elif action_type == "flag_for_review":
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
        
        insights.append({
            "type": "summary",
            "title": "Resumen General",
            "content": f"Se procesaron {results['documents_processed']} documentos generando {results['chunks_generated']} chunks de información."
        })
        
        critical_problems = [p for p in results.get("problems_detected", []) if p.get("severity") == "alta"]
        if critical_problems:
            insights.append({
                "type": "alert",
                "title": "Problemas Críticos Detectados",
                "content": f"Se detectaron {len(critical_problems)} problemas de alta severidad que requieren atención inmediata.",
                "items": critical_problems[:5]
            })
        
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

"""Intelligence Contract Mode - Procesamiento automático con Agentic AI avanzado."""

from __future__ import annotations

from typing import List, Dict, Any, Optional, Iterator
from datetime import datetime
from pathlib import Path
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

from langchain_core.documents import Document
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI

from .config import AppConfig
from .document_processor import DocumentProcessor
try:
    from docling.document_converter import DocumentConverter
    DOCLING_AVAILABLE = True
except ImportError:
    DOCLING_AVAILABLE = False
    DocumentConverter = None
from .retriever_builder import RetrieverBuilder
from .workflow import AgentWorkflow
from .memory import MemoryStore, ContextManager
from .advanced_agent import AdvancedAutonomousAgent
from .tools import (
    EmailTool, ReportTool, DatabaseTool, PresentationTool,
    IntegrationTool, TableAnalysisTool, SchedulerTool
)


class IntelligenceContractMode:
    """
    Modo Intelligence Contract: Procesamiento automático con detección inteligente.
    
    Funcionalidades:
    - Procesa documentos automÃ¡ticamente
    - Detecta problemas, oportunidades y patrones
    - Ejecuta acciones segÃºn reglas
    - Aprende continuamente
    """
    
    def __init__(self, config: AppConfig, provider: str = "openai"):
        self.config = config
        self.provider = provider
        self.processor = DocumentProcessor(config)
        self.retriever_builder = RetrieverBuilder(config)
        self.workflow = AgentWorkflow(config)
        self.advanced_agent = AdvancedAutonomousAgent(config) if config.enable_autonomous_agents else None
        
        # Memoria y contexto
        self.memory_store = MemoryStore(config.memory_dir, config.memory_retention_days) if config.enable_memory else None
        self.context_manager = ContextManager(self.memory_store, config) if self.memory_store else None
        
        # LLM para detecciÃ³n automÃ¡tica - SIN LÃMITE DE TOKENS (la API decide)
        from docchat.utils.llm_factory import create_llm
        self.llm = create_llm(
            provider=provider,
            model=config.agentic_model,
            temperature=0.2,
            api_key=config.openai_api_key if provider == "openai" else config.anthropic_api_key,
            # max_tokens REMOVIDO - dejar que la API decida la longitud de respuesta
            request_timeout=300  # Timeout mÃ¡s largo para respuestas largas
        )
        
        # LLM rÃ¡pido para tareas simples (detecciÃ³n, insights)
        # ACTUALIZADO: Usar Claude Haiku 4.5 (mÃ¡s rÃ¡pido y econÃ³mico)
        fast_model = "gpt-4o-mini" if provider == "openai" else "claude-haiku-4-5-20251001"
        self.fast_llm = create_llm(
            provider=provider,
            model=fast_model,
            temperature=0.2,
            api_key=config.openai_api_key if provider == "openai" else config.anthropic_api_key,
            # max_tokens REMOVIDO - dejar que la API decida la longitud de respuesta
            request_timeout=180  # Timeout mÃ¡s largo para respuestas largas
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
    
    def process_intelligence_contract_documents_streaming(
        self,
        files: List,
        auto_detect: bool = True,
        rules: Optional[List[Dict]] = None
    ) -> Iterator[str]:
        """Procesa documentos con streaming de resultados (generador)."""
        yield "## 🚀 Procesamiento Intelligence Contract Iniciado\n\n"
        yield "ðŸ“„ Procesando documentos...\n\n"
        
        try:
            # 1. Procesar documentos
            docs = self.processor.process(files)
            yield f"âœ… **Documentos procesados**: {len(files)}\n"
            yield f"âœ… **Chunks generados**: {len(docs)}\n\n"
            
            # 2. Generar resÃºmenes automÃ¡ticos con streaming
            yield "### ðŸ“„ Generando ResÃºmenes AutomÃ¡ticos...\n\n"
            import uuid
            session_namespace = f"intelligence_contract_{uuid.uuid4().hex[:8]}"
            retriever = self.retriever_builder.build_hybrid_retriever(docs, namespace=session_namespace)
            
            # Agrupar documentos por archivo (cÃ³digo similar al mÃ©todo original)
            from collections import defaultdict
            docs_by_file = defaultdict(list)
            file_key_to_original_name = {}
            
            for doc in docs:
                source = doc.metadata.get("source", "")
                if source:
                    doc_hash = doc.metadata.get("hash", "")
                    if doc_hash:
                        file_key = f"hash_{doc_hash}"
                    else:
                        source_path = Path(source)
                        file_key = source_path.name
                    docs_by_file[file_key].append(doc)
                    if file_key not in file_key_to_original_name:
                        file_key_to_original_name[file_key] = source
            
            # Generar resÃºmenes en paralelo y emitir mientras se completan
            processed_clean_names = set()
            summary_tasks = []
            for file_key, file_docs_list in docs_by_file.items():
                original_file_name = file_key_to_original_name.get(file_key, file_docs_list[0].metadata.get("source", ""))
                clean_file_name = Path(original_file_name).name
                if clean_file_name in processed_clean_names:
                    continue
                processed_clean_names.add(clean_file_name)
                summary_tasks.append((original_file_name, file_docs_list, clean_file_name))
            
            summaries = {}
            max_workers = min(3, len(summary_tasks))
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_file = {
                    executor.submit(self._generate_automatic_summary, original_file_name, file_docs_list, retriever): 
                    (original_file_name, clean_file_name) 
                    for original_file_name, file_docs_list, clean_file_name in summary_tasks
                }
                
                for future in as_completed(future_to_file):
                    original_file_name, clean_file_name = future_to_file[future]
                    try:
                        summary = future.result()
                        summaries[original_file_name] = summary
                        # Emitir resumen inmediatamente
                        yield f"#### {clean_file_name}\n\n"
                        yield f"**Tipo de Documento**: {summary.get('document_type', 'N/A')}\n\n"
                        yield f"**Resumen Ejecutivo**:\n{summary.get('summary', 'N/A')}\n\n"
                        if summary.get('key_points'):
                            yield f"**Puntos Clave** ({len(summary['key_points'])}):\n"
                            for i, point in enumerate(summary['key_points'][:10], 1):
                                yield f"{i}. {point}\n"
                            yield "\n"
                        if summary.get('topics'):
                            yield f"**Temas**: {', '.join(summary['topics'][:5])}\n\n"
                        if summary.get('business_value'):
                            yield f"**Valor para el Negocio**: {summary.get('business_value')}\n\n"
                        if summary.get('entities'):
                            yield f"**Entidades Principales**: {', '.join(summary['entities'][:5])}\n\n"
                        yield "---\n\n"
                    except Exception as e:
                        yield f"âŒ Error en {clean_file_name}: {str(e)[:100]}\n\n"
            
            # 3. DetecciÃ³n automÃ¡tica (si estÃ¡ habilitada)
            detection_results = {"problems": [], "opportunities": [], "patterns": []}
            if auto_detect:
                yield "### ðŸ” Detectando Problemas, Oportunidades y Patrones...\n\n"
                detection_results = self._auto_detect_issues_opportunities(docs, retriever)
                
                if detection_results.get('problems'):
                    yield "### âš ï¸ Problemas Detectados\n\n"
                    for problem in detection_results['problems']:
                        yield f"- **{problem.get('type', 'Unknown')}** ({problem.get('severity', 'N/A')}): {problem.get('description', 'N/A')}\n"
                    yield "\n"
                
                if detection_results.get('opportunities'):
                    yield "### ðŸ’¡ Oportunidades Detectadas\n\n"
                    for opp in detection_results['opportunities']:
                        yield f"- **{opp.get('type', 'Unknown')}** ({opp.get('impact', 'N/A')}): {opp.get('description', 'N/A')}\n"
                    yield "\n"
                
                if detection_results.get('patterns'):
                    yield "### ðŸ” Patrones Encontrados\n\n"
                    for pattern in detection_results['patterns']:
                        yield f"- **{pattern.get('type', 'Unknown')}**: {pattern.get('description', 'N/A')}\n"
                    yield "\n"
            
            # 4. Insights generales
            yield "### ðŸ’¡ Insights Generales\n\n"
            insights = self._generate_insights(docs, retriever, {
                "documents_processed": len(files),
                "chunks_generated": len(docs),
                "problems_detected": detection_results.get('problems', []),
                "opportunities_detected": detection_results.get('opportunities', []),
                "patterns_found": detection_results.get('patterns', []),
                "summaries": summaries
            })
            
            for insight in insights:
                yield f"#### {insight.get('title', 'Insight')}\n"
                yield f"{insight.get('content', 'N/A')}\n\n"
            
            yield "\nâœ… **Procesamiento completado exitosamente!**\n"
            
        except Exception as e:
            yield f"\nâŒ **Error**: {str(e)}\n"
    
    def process_enterprise_documents(
        self,
        files: List,
        auto_detect: bool = True,
        rules: Optional[List[Dict]] = None,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        Procesa documentos empresariales con detecciÃ³n automÃ¡tica.
        
        Args:
            files: Lista de archivos a procesar
            auto_detect: Si True, detecta problemas/oportunidades automÃ¡ticamente
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
            print("Procesando documentos con Intelligence Contract...")
            docs = self.processor.process(files)
            results["documents_processed"] = len(files)
            results["chunks_generated"] = len(docs)
            
            # Si no se generaron chunks, intentar procesar directamente con MultiFormatProcessor como Ãºltimo recurso
            if not docs or len(docs) == 0:
                print("âš ï¸ El procesador estÃ¡ndar no generÃ³ chunks.")
                print("   ðŸ’¡ Posibles causas: PDF encriptado, formato no soportado, o error en procesamiento.")
                print("   ðŸ”„ Intentando procesamiento directo con MultiFormatProcessor (Docling)...")
                try:
                    from docchat.multi_format_processor import MultiFormatProcessor
                    direct_processor = MultiFormatProcessor(self.config)
                    # Procesar archivos directamente
                    direct_docs = direct_processor.process(files)
                    if direct_docs and len(direct_docs) > 0:
                        docs = direct_docs
                        results["chunks_generated"] = len(docs)
                        print(f"   âœ… Procesamiento directo exitoso: {len(docs)} chunks generados")
                        results["status"] = "success"  # Actualizar estado a success si el fallback funcionÃ³
                    else:
                        print("   âš ï¸ Procesamiento directo tampoco generÃ³ chunks")
                except Exception as e:
                    print(f"   âš ï¸ Error en procesamiento directo: {str(e)[:200]}")
                    import traceback
                    traceback.print_exc()
            
            # 2. Generar resÃºmenes automÃ¡ticos
            if not docs or len(docs) == 0:
                results["status"] = "error"
                results["error"] = "No se pudieron procesar los documentos. El PDF puede estar encriptado o corrupto."
                print("ERROR en procesamiento Intelligence Contract: No hay documentos procesados para indexar.")
                return results
            
            print("Generando resumenes automaticos...")
            # Usar un namespace Ãºnico para esta sesiÃ³n para evitar mezclar con documentos previos
            import uuid
            session_namespace = f"intelligence_contract_{uuid.uuid4().hex[:8]}"
            retriever = self.retriever_builder.build_hybrid_retriever(docs, namespace=session_namespace)
            
            # Obtener todos los archivos Ãºnicos procesados desde los documentos
            from pathlib import Path
            from collections import defaultdict
            
            # FunciÃ³n para normalizar nombres de archivo (remover variaciones como "- copia", " - copy", etc.)
            def normalize_filename(name):
                """Normaliza el nombre del archivo removiendo variaciones comunes de duplicados."""
                name_lower = name.lower()
                # Remover variaciones comunes de "copia"
                variations = [" - copia", "- copia", " - copy", "- copy", " (copia)", "(copia)", " (copy)", "(copy)", " - copia.pdf", "- copia.pdf"]
                for variation in variations:
                    if name_lower.endswith(variation):
                        # Remover la variaciÃ³n pero mantener la extensiÃ³n
                        base = name[:-len(variation)]
                        ext = Path(name).suffix
                        return base + ext
                return name
            
            # Crear mapeo de archivos: hash -> nombre original preferido
            # Esto permite detectar archivos duplicados con diferentes nombres
            file_hash_to_original_name = {}
            normalized_name_to_original = {}  # Mapeo de nombre normalizado a nombre original preferido
            
            for file_obj in files:
                # Obtener nombre original de Google Drive si estÃ¡ disponible
                original_name = getattr(file_obj, "original_name", None)
                if not original_name:
                    original_name = getattr(file_obj, "name", "documento")
                
                # Normalizar el nombre
                normalized = normalize_filename(Path(original_name).name)
                
                # Guardar mapeo de nombre normalizado a original (preferir nombres sin "- copia")
                if normalized not in normalized_name_to_original:
                    normalized_name_to_original[normalized] = original_name
                else:
                    # Preferir nombres sin variaciones de "copia" o "copy"
                    existing = normalized_name_to_original[normalized]
                    existing_lower = existing.lower()
                    original_lower = original_name.lower()
                    if ("copia" in existing_lower or "copy" in existing_lower) and ("copia" not in original_lower and "copy" not in original_lower):
                        normalized_name_to_original[normalized] = original_name
                    elif "drive_" in existing and "drive_" not in original_name:
                        normalized_name_to_original[normalized] = original_name
                
                # Intentar obtener hash del archivo para detectar duplicados
                try:
                    from docchat.utils import read_bytes, sha256_bytes
                    data = read_bytes(file_obj)
                    file_hash = sha256_bytes(data)
                    # Siempre preferir el nombre original sobre el temporal
                    if file_hash not in file_hash_to_original_name:
                        file_hash_to_original_name[file_hash] = original_name
                    else:
                        # Si ya existe, mantener el que tiene nombre mÃ¡s descriptivo (no drive_xxx, sin "- copia")
                        existing = file_hash_to_original_name[file_hash]
                        existing_lower = existing.lower()
                        original_lower = original_name.lower()
                        if ("copia" in existing_lower or "copy" in existing_lower) and ("copia" not in original_lower and "copy" not in original_lower):
                            file_hash_to_original_name[file_hash] = original_name
                        elif "drive_" in existing and "drive_" not in original_name:
                            file_hash_to_original_name[file_hash] = original_name
                except:
                    pass
            
            # Agrupar documentos por hash del archivo (mejor) o por nombre (fallback)
            docs_by_file = defaultdict(list)
            file_key_to_original_name = {}  # Mapeo de clave de agrupaciÃ³n a nombre original
            
            for doc in docs:
                source = doc.metadata.get("source", "")
                if source:
                    source_path = Path(source)
                    source_name = source_path.name
                    
                    # Intentar usar hash primero para detectar duplicados
                    doc_hash = doc.metadata.get("hash", "")
                    if doc_hash and doc_hash in file_hash_to_original_name:
                        # Agrupar por hash para detectar archivos duplicados
                        file_key = f"hash_{doc_hash}"
                        original_name = file_hash_to_original_name[doc_hash]
                    else:
                        # Fallback: agrupar por nombre normalizado del archivo
                        normalized_source = normalize_filename(source_name)
                        file_key = f"normalized_{normalized_source}"
                        
                        # Buscar nombre original en el mapeo de nombres normalizados
                        if normalized_source in normalized_name_to_original:
                            original_name = normalized_name_to_original[normalized_source]
                        else:
                            # Buscar en los archivos originales
                            original_name = None
                            for file_obj in files:
                                temp_name = getattr(file_obj, "name", "")
                                temp_normalized = normalize_filename(Path(temp_name).name)
                                if temp_normalized == normalized_source:
                                    original_name = getattr(file_obj, "original_name", None) or temp_name
                                    break
                            if not original_name:
                                original_name = source
                            # Guardar en el mapeo
                            normalized_name_to_original[normalized_source] = original_name
                    
                    docs_by_file[file_key].append(doc)
                    # Guardar el nombre original preferido para esta clave
                    if file_key not in file_key_to_original_name:
                        file_key_to_original_name[file_key] = original_name
                    else:
                        # Preferir nombres descriptivos sobre nombres temporales (drive_xxx) y sin "- copia"
                        existing = file_key_to_original_name[file_key]
                        existing_lower = existing.lower()
                        original_lower = original_name.lower()
                        if ("copia" in existing_lower or "copy" in existing_lower) and ("copia" not in original_lower and "copy" not in original_lower):
                            file_key_to_original_name[file_key] = original_name
                        elif "drive_" in existing and "drive_" not in original_name:
                            file_key_to_original_name[file_key] = original_name
            
            # Generar resumen para CADA archivo Ãºnico encontrado en los documentos
            print(f"   Encontrados {len(docs_by_file)} archivos Ãºnicos en los documentos procesados")
            
            # Track de archivos ya procesados por nombre limpio para evitar duplicados
            processed_clean_names = set()
            
            # Preparar lista de tareas para paralelizaciÃ³n
            summary_tasks = []
            for file_key, file_docs_list in docs_by_file.items():
                # Obtener nombre original preferido para este archivo
                original_file_name = file_key_to_original_name.get(file_key, file_docs_list[0].metadata.get("source", ""))
                clean_file_name = Path(original_file_name).name
                
                # Evitar duplicados: si ya procesamos este archivo por nombre limpio, saltarlo
                if clean_file_name in processed_clean_names:
                    print(f"   âš ï¸ Saltando {clean_file_name} (ya procesado como duplicado)")
                    continue
                processed_clean_names.add(clean_file_name)
                
                summary_tasks.append((original_file_name, file_docs_list, clean_file_name))
            
            # Paralelizar generaciÃ³n de resÃºmenes para mayor velocidad
            max_workers = min(3, len(summary_tasks))  # MÃ¡ximo 3 workers para no sobrecargar API
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_file = {
                    executor.submit(self._generate_automatic_summary, original_file_name, file_docs_list, retriever): 
                    (original_file_name, clean_file_name) 
                    for original_file_name, file_docs_list, clean_file_name in summary_tasks
                }
                
                for future in as_completed(future_to_file):
                    original_file_name, clean_file_name = future_to_file[future]
                    try:
                        summary = future.result()
                        results["summaries"][original_file_name] = summary
                        print(f"   âœ… Resumen completado: {clean_file_name}")
                    except Exception as e:
                        print(f"   âŒ Error generando resumen para {clean_file_name}: {str(e)[:100]}")
                        results["summaries"][original_file_name] = {
                            "summary": f"Error generando resumen: {str(e)[:200]}",
                            "key_points": [],
                            "document_type": "unknown",
                            "relevant_date": "N/A",
                            "entities": [],
                            "topics": [],
                            "business_value": "N/A"
                        }
            
            # Verificar que todos los archivos subidos tengan resumen
            missing_summaries = []
            for file_obj in files:
                # Obtener nombre original de Google Drive si estÃ¡ disponible
                original_name = getattr(file_obj, "original_name", None)
                file_name = original_name if original_name else getattr(file_obj, "name", "documento")
                clean_name = Path(file_name).name
                
                # TambiÃ©n obtener el nombre temporal (puede ser diferente del original)
                temp_name = getattr(file_obj, "name", "")
                temp_clean_name = Path(temp_name).name if temp_name else None
                
                # Verificar si ya tenemos un resumen para este archivo (por nombre limpio)
                found = False
                if clean_name in processed_clean_names:
                    found = True
                else:
                    # Verificar tambiÃ©n en los resÃºmenes ya generados
                    for summary_file_name in results["summaries"].keys():
                        if Path(summary_file_name).name == clean_name:
                            found = True
                            processed_clean_names.add(clean_name)
                            break
                
                if not found:
                    missing_summaries.append(file_name)
                    # Intentar encontrar documentos por nombre limpio (original)
                    file_docs = [d for d in docs if Path(d.metadata.get("source", "")).name == clean_name]
                    
                    # Si no se encuentra por nombre original, intentar por nombre temporal
                    if not file_docs and temp_clean_name and temp_clean_name != clean_name:
                        file_docs = [d for d in docs if Path(d.metadata.get("source", "")).name == temp_clean_name]
                    
                    # TambiÃ©n buscar por cualquier variaciÃ³n del nombre (sin espacios, con/sin extensiones)
                    if not file_docs:
                        # Buscar por hash del archivo si estÃ¡ disponible
                        try:
                            from docchat.utils import read_bytes, sha256_bytes
                            data = read_bytes(file_obj)
                            file_hash = sha256_bytes(data)
                            file_docs = [d for d in docs if d.metadata.get("hash", "") == file_hash]
                        except:
                            pass
                    
                    if file_docs:
                        print(f"   Generando resumen tardÃ­o para: {clean_name} ({len(file_docs)} chunks)")
                        summary = self._generate_automatic_summary(file_name, file_docs, retriever)
                        results["summaries"][file_name] = summary
                    else:
                        # Si no hay documentos, crear resumen bÃ¡sico
                        print(f"   ADVERTENCIA: No se encontraron chunks para {clean_name}")
                        results["summaries"][file_name] = {
                            "summary": f"Documento '{clean_name}' procesado pero no se encontraron chunks para anÃ¡lisis detallado. Puede ser un archivo vacÃ­o o con formato no soportado.",
                            "key_points": [],
                            "document_type": "unknown",
                            "relevant_date": "N/A",
                            "entities": [],
                            "topics": [],
                            "business_value": "Documento procesado pero sin contenido extraÃ­ble"
                        }
            
            print(f"   âœ… ResÃºmenes generados: {len(results['summaries'])}/{len(files)} archivos")
            
            # 3. DetecciÃ³n automÃ¡tica (si estÃ¡ habilitada)
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
            print("✅ Procesamiento Intelligence Contract completado exitosamente!")
            print(f"   - Documentos: {results.get('documents_processed', 0)}")
            print(f"   - Chunks: {results.get('chunks_generated', 0)}")
            print(f"   - Problemas detectados: {len(results.get('problems_detected', []))}")
            print(f"   - Oportunidades detectadas: {len(results.get('opportunities_detected', []))}")
            print(f"   - Patrones encontrados: {len(results.get('patterns_found', []))}")
            
        except Exception as e:
            results["status"] = "error"
            results["error"] = str(e)
            print(f"ERROR en procesamiento Intelligence Contract: {e}")
        
        return results
    
    def _generate_automatic_summary(
        self,
        file_name: str,
        docs: List[Document],
        retriever
    ) -> Dict[str, Any]:
        """Genera resumen automÃ¡tico profesional y extenso de un documento."""
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
        
        # Construir contexto optimizado para soportar documentos grandes
        # OPTIMIZADO para aprovechar context windows grandes (128k OpenAI, 200k Claude)
        context_parts = []
        total_chars = 0
        # Aumentado significativamente para aprovechar context windows grandes
        # 128k tokens = ~512k caracteres, 200k tokens = ~800k caracteres
        max_chars = 50000 if self.provider == "openai" else 80000  # Claude puede manejar mÃ¡s
        
        # Aumentar nÃºmero de chunks para documentos grandes
        max_chunks = 50 if self.provider == "openai" else 80  # Claude puede procesar mÃ¡s
        
        for doc in file_docs[:max_chunks]:
            content = doc.page_content[:2000]  # Aumentado a 2000 chars por chunk
            if total_chars + len(content) <= max_chars:
                context_parts.append(content)
                total_chars += len(content)
            else:
                remaining = max_chars - total_chars
                if remaining > 200:
                    context_parts.append(content[:remaining])
                break
        
        context = "\n\n---\n\n".join(context_parts)
        
        # Extraer nombre del archivo limpio
        from pathlib import Path
        clean_file_name = Path(file_name).name
        
        prompt = f"""Eres un analista experto de documentos empresariales. Analiza este documento en profundidad y genera un resumen ejecutivo profesional, extenso y altamente Ãºtil.

DOCUMENTO: {clean_file_name}

CONTENIDO DEL DOCUMENTO:
{context}

INSTRUCCIONES:
Genera un anÃ¡lisis completo y profesional que incluya:

1. RESUMEN EJECUTIVO (4-6 pÃ¡rrafos extensos):
   - Contexto y propÃ³sito del documento
   - Ideas principales y argumentos centrales
   - Conclusiones y recomendaciones clave
   - Valor e importancia del contenido
   - Aplicaciones prÃ¡cticas y relevancia empresarial

2. PUNTOS CLAVE (8-12 puntos detallados):
   - Conceptos fundamentales explicados
   - Hallazgos importantes
   - Recomendaciones especÃ­ficas
   - Insights valiosos para el negocio

3. TIPO DE DOCUMENTO:
   - ClasificaciÃ³n precisa (libro, artÃ­culo acadÃ©mico, informe, guÃ­a, whitepaper, etc.)
   - GÃ©nero y categorÃ­a temÃ¡tica

4. FECHA/PERÃODO RELEVANTE:
   - Fecha de publicaciÃ³n si estÃ¡ disponible
   - PerÃ­odo temporal relevante
   - Contexto histÃ³rico si aplica

5. ENTIDADES PRINCIPALES:
   - Autores, organizaciones, empresas mencionadas
   - Personas clave citadas
   - Instituciones relevantes

6. TEMAS Y ÃREAS DE CONOCIMIENTO:
   - Temas principales cubiertos
   - Disciplinas o Ã¡reas de conocimiento
   - Industrias o sectores relevantes

7. VALOR PARA EL NEGOCIO:
   - Aplicaciones prÃ¡cticas
   - Insights accionables
   - Oportunidades identificadas

IMPORTANTE:
- SÃ© especÃ­fico y detallado
- Incluye informaciÃ³n concreta del documento
- Evita generalidades
- Proporciona valor real para la toma de decisiones
- Usa lenguaje profesional pero claro

Responde ÃšNICAMENTE en formato JSON vÃ¡lido:
{{
    "summary": "resumen ejecutivo extenso y profesional de 4-6 pÃ¡rrafos con informaciÃ³n valiosa y especÃ­fica",
    "key_points": ["punto clave 1 detallado", "punto clave 2 detallado", ...],
    "document_type": "tipo especÃ­fico del documento",
    "relevant_date": "fecha o perÃ­odo si existe",
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
            
            # Validar que el resumen no sea genÃ©rico
            summary_text = summary_data.get("summary", "")
            generic_phrases = [
                "contiene informaciÃ³n relevante sobre mÃºltiples temas",
                "se identificaron",
                "secciones principales con contenido sustancial",
                "anÃ¡lisis del documento",
                "documento procesado"
            ]
            
            is_generic = any(phrase.lower() in summary_text.lower() for phrase in generic_phrases)
            
            # Si el resumen es genÃ©rico o muy corto, intentar mejorarlo con mÃ¡s contexto
            if is_generic or len(summary_text) < 300:
                # Intentar generar un resumen mejor con mÃ¡s chunks
                if len(file_docs) > 10:
                    # Usar mÃ¡s contexto para generar mejor resumen
                    extended_context = []
                    for doc in file_docs[:30]:
                        content = doc.page_content[:800]
                        if content.strip():
                            extended_context.append(content)
                    
                    if extended_context:
                        extended_prompt = f"""Genera un resumen ejecutivo profesional y especÃ­fico para el documento '{clean_file_name}'.

CONTENIDO EXTENDIDO:
{chr(10).join(extended_context[:20])}

IMPORTANTE: 
- SÃ© ESPECÃFICO sobre el contenido real del documento
- NO uses frases genÃ©ricas como "contiene informaciÃ³n relevante" o "mÃºltiples temas"
- Incluye detalles concretos, nombres, conceptos, ideas especÃ­ficas del documento
- Si es un libro, menciona el autor, temas principales, argumentos clave
- Si es un artÃ­culo, menciona el tema especÃ­fico, hallazgos, conclusiones

Responde en JSON:
{{
    "summary": "resumen especÃ­fico y detallado de 4-6 pÃ¡rrafos",
    "key_points": ["punto especÃ­fico 1", "punto especÃ­fico 2", ...],
    "document_type": "tipo especÃ­fico",
    "relevant_date": "fecha si existe",
    "entities": ["entidad1", "entidad2"],
    "topics": ["tema1", "tema2"],
    "business_value": "valor especÃ­fico"
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
            
            # Si aÃºn es genÃ©rico, marcar como tal pero retornar
            if is_generic:
                summary_data["_is_generic"] = True
            
            return summary_data
        except Exception as e:
            # Si hay un error pero tenemos documentos, intentar generar resumen bÃ¡sico
            if not file_docs:
                return {
                    "summary": f"No se pudo generar resumen para '{clean_file_name}'. No se encontraron chunks extraÃ­bles del documento.",
                    "key_points": [],
                    "document_type": "unknown",
                    "relevant_date": "N/A",
                    "entities": [],
                    "topics": [],
                    "business_value": "Documento procesado pero sin contenido extraÃ­ble"
                }
            
            # Fallback: generar resumen bÃ¡sico pero mÃ¡s completo
            key_points = []
            for doc in file_docs[:10]:
                content = doc.page_content.strip()
                if len(content) > 50:
                    key_points.append(content[:200])
            
            return {
                "summary": f"AnÃ¡lisis del documento '{clean_file_name}'. El documento contiene informaciÃ³n relevante sobre mÃºltiples temas. Se identificaron {len(file_docs)} secciones principales con contenido sustancial.",
                "key_points": key_points[:8],
                "document_type": "documento",
                "relevant_date": "N/A",
                "entities": [],
                "topics": [],
                "business_value": "Documento procesado para anÃ¡lisis empresarial",
                "error": str(e)
            }
    
    def _auto_detect_issues_opportunities(
        self,
        docs: List[Document],
        retriever
    ) -> Dict[str, List]:
        """Detecta automÃ¡ticamente problemas, oportunidades y patrones."""
        # Obtener contexto representativo
        sample_docs = docs[:50]  # Muestra representativa
        context = "\n\n".join([d.page_content[:300] for d in sample_docs])
        
        prompt = f"""Analiza estos documentos empresariales y detecta automÃ¡ticamente:

1. PROBLEMAS POTENCIALES:
   - Riesgos legales, financieros, operacionales
   - Contradicciones o inconsistencias
   - Fechas vencidas o prÃ³ximas a vencer
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
            "description": "descripciÃ³n",
            "source": "documento origen",
            "recommendation": "recomendaciÃ³n"
        }}
    ],
    "opportunities": [
        {{
            "type": "tipo de oportunidad",
            "impact": "alto/medio/bajo",
            "description": "descripciÃ³n",
            "source": "documento origen",
            "action": "acciÃ³n sugerida"
        }}
    ],
    "patterns": [
        {{
            "type": "tipo de patrÃ³n",
            "description": "descripciÃ³n del patrÃ³n",
            "frequency": "alta/media/baja",
            "implication": "implicaciÃ³n"
        }}
    ]
}}"""
        
        try:
            # Usar LLM rÃ¡pido para detecciÃ³n (optimizaciÃ³n de velocidad)
            response = self.fast_llm.invoke(prompt).content.strip()
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
            
            # Evaluar condiciÃ³n
            if self._evaluate_condition(condition, docs, results):
                # Ejecutar acciÃ³n
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
        """EvalÃºa una condiciÃ³n de regla."""
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
        """Ejecuta una acciÃ³n de automatizaciÃ³n."""
        action_type = action.get("type")
        
        if action_type == "notify":
            # Notificar (email, Slack, etc.)
            return {"status": "notified", "channel": action.get("channel")}
        
        elif action_type == "generate_report":
            # Generar reporte automÃ¡tico usando herramienta avanzada
            report_tool = self.tools.get("report")
            if report_tool:
                from datetime import datetime
                report_data = {
                    "summary": "Reporte automático generado por Intelligence Contract",
                    "timestamp": datetime.now().isoformat(),
                    "documents_analyzed": len(docs),
                    "problems": results.get("problems_detected", []),
                    "opportunities": results.get("opportunities_detected", [])
                }
                result = report_tool.execute(
                    data=report_data,
                    format="excel",
                    title="Reporte Automático Intelligence Contract"
                )
                if result.success:
                    return {"status": "report_generated", "path": str(result.data) if result.data else None}
                return {"status": "report_failed", "error": result.message}
            return {"status": "report_failed", "error": "Report tool not available"}
        
        elif action_type == "flag_for_review":
            # Marcar para revisiÃ³n
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
            "content": f"Se procesaron {results['documents_processed']} documentos generando {results['chunks_generated']} chunks de informaciÃ³n."
        })
        
        # Insight 2: Problemas crÃ­ticos
        critical_problems = [p for p in results.get("problems_detected", []) if p.get("severity") == "alta"]
        if critical_problems:
            insights.append({
                "type": "alert",
                "title": "Problemas CrÃ­ticos Detectados",
                "content": f"Se detectaron {len(critical_problems)} problemas de alta severidad que requieren atenciÃ³n inmediata.",
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
        """Guarda informaciÃ³n en memoria para aprendizaje continuo."""
        if not self.context_manager:
            return
        
        # Guardar resÃºmenes
        for file_name, summary in results.get("summaries", {}).items():
            self.context_manager.add_query(
                query=f"Resumen automÃ¡tico de {file_name}",
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
    
    def _auto_detect_issues_opportunities(
        self,
        docs: List[Document],
        retriever
    ) -> Dict[str, List]:
        """Detecta automÃ¡ticamente problemas, oportunidades y patrones."""
        # Obtener contexto representativo
        sample_docs = docs[:50]  # Muestra representativa
        context = "\n\n".join([d.page_content[:300] for d in sample_docs])
        
        prompt = f"""Analiza estos documentos empresariales y detecta automÃ¡ticamente:

1. PROBLEMAS POTENCIALES:
   - Riesgos legales, financieros, operacionales
   - Contradicciones o inconsistencias
   - Fechas vencidas o prÃ³ximas a vencer
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
            "description": "descripciÃ³n",
            "source": "documento origen",
            "recommendation": "recomendaciÃ³n"
        }}
    ],
    "opportunities": [
        {{
            "type": "tipo de oportunidad",
            "impact": "alto/medio/bajo",
            "description": "descripciÃ³n",
            "source": "documento origen",
            "action": "acciÃ³n sugerida"
        }}
    ],
    "patterns": [
        {{
            "type": "tipo de patrÃ³n",
            "description": "descripciÃ³n del patrÃ³n",
            "frequency": "alta/media/baja",
            "implication": "implicaciÃ³n"
        }}
    ]
}}"""
        
        try:
            # Usar LLM rÃ¡pido para detecciÃ³n (optimizaciÃ³n de velocidad)
            response = self.fast_llm.invoke(prompt).content.strip()
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
            
            # Evaluar condiciÃ³n
            if self._evaluate_condition(condition, docs, results):
                # Ejecutar acciÃ³n
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
        """EvalÃºa una condiciÃ³n de regla."""
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
        """Ejecuta una acciÃ³n de automatizaciÃ³n."""
        action_type = action.get("type")
        
        if action_type == "notify":
            # Notificar (email, Slack, etc.)
            return {"status": "notified", "channel": action.get("channel")}
        
        elif action_type == "generate_report":
            # Generar reporte automÃ¡tico usando herramienta avanzada
            report_tool = self.tools.get("report")
            if report_tool:
                from datetime import datetime
                report_data = {
                    "summary": "Reporte automático generado por Intelligence Contract",
                    "timestamp": datetime.now().isoformat(),
                    "documents_analyzed": len(docs),
                    "problems": results.get("problems_detected", []),
                    "opportunities": results.get("opportunities_detected", [])
                }
                result = report_tool.execute(
                    data=report_data,
                    format="excel",
                    title="Reporte Automático Intelligence Contract"
                )
                if result.success:
                    return {"status": "report_generated", "path": str(result.data) if result.data else None}
                return {"status": "report_failed", "error": result.message}
            return {"status": "report_failed", "error": "Report tool not available"}
        
        elif action_type == "flag_for_review":
            # Marcar para revisiÃ³n
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
            "content": f"Se procesaron {results['documents_processed']} documentos generando {results['chunks_generated']} chunks de informaciÃ³n."
        })
        
        # Insight 2: Problemas crÃ­ticos
        critical_problems = [p for p in results.get("problems_detected", []) if p.get("severity") == "alta"]
        if critical_problems:
            insights.append({
                "type": "alert",
                "title": "Problemas CrÃ­ticos Detectados",
                "content": f"Se detectaron {len(critical_problems)} problemas de alta severidad que requieren atenciÃ³n inmediata.",
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
        """Guarda informaciÃ³n en memoria para aprendizaje continuo."""
        if not self.context_manager:
            return
        
        # Guardar resÃºmenes
        for file_name, summary in results.get("summaries", {}).items():
            self.context_manager.add_query(
                query=f"Resumen automÃ¡tico de {file_name}",
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

