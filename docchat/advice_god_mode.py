"""ADVICE GOD Mode - Procesamiento automático con Agentic AI avanzado."""

from __future__ import annotations

from typing import List, Dict, Any, Optional, Iterator, TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

from datetime import datetime
from pathlib import Path
import json
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

from langchain_core.documents import Document
from langgraph.graph import StateGraph, END
from langchain_core.messages import SystemMessage, HumanMessage
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
    EmailTool,
    ReportTool,
    DatabaseTool,
    PresentationTool,
    IntegrationTool,
    TableAnalysisTool,
    SchedulerTool,
)

from .advice_god.orchestrator import DecisionOrchestrator
from .advice_god.actions import ActionLayer
from .advice_god_schemas import (
    validate_data_for_type,
    build_success_result,
    build_error_result,
)


class AdviceGodMode:
    """
    Modo ADVICE GOD: Procesamiento automático con detección inteligente.
    
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
        
        # Memoria y contexto (no se usa en el nuevo modo PDF -> JSON,
        # pero se mantiene para compatibilidad con otras partes del sistema)
        self.memory_store = MemoryStore(config.memory_dir, config.memory_retention_days) if config.enable_memory else None
        self.context_manager = ContextManager(self.memory_store, config) if self.memory_store else None
        
        # LLM pequeño (SLM) para clasificación + extracción estructurada desde PDFs.
        # Reglas: temperature 0, max_tokens limitado, salida JSON ONLY vía prompt.
        from docchat.utils.llm_factory import create_llm
        slm_model = "gpt-4o-mini" if provider == "openai" else "claude-haiku-4-5-20251001"
        self.slm_llm = create_llm(
            provider=provider,
            model=slm_model,
            temperature=0.0,
            api_key=config.openai_api_key if provider == "openai" else config.anthropic_api_key,
            max_tokens=512,
            request_timeout=60,
            max_retries=2,
        )

        # NOTA IMPORTANTE:
        # Ya NO usamos workflows agentic, RAG, memoria ni multi-agents para ADVICE GOD.
        # Este modo se convierte en un servicio backend determinista: PDF -> JSON.
    
    def process_enterprise_documents_streaming(
        self,
        files: List,
        auto_detect: bool = True,  # legacy, ignorado
        rules: Optional[List[Dict]] = None,  # legacy, ignorado
        use_workflows: bool = True,  # legacy, ignorado
        dry_run: bool = False,  # legacy, ignorado
    ) -> Iterator[str]:
        """
        NUEVA LÓGICA: Servicio PDF -> JSON estructurado, determinista y listo para producción.

        - NO chatea
        - NO usa RAG
        - NO usa multi-agents
        - NO usa LLM grande

        Solo:
        PDF → extracción de texto → chunking → SLM → JSON validado → output.
        """
        yield "## 🤖 ADVICE GOD - PDF → JSON Structured Extraction\n\n"

        if not files:
            yield json.dumps(
                build_error_result("other", "No files provided for processing."),
                ensure_ascii=False,
            )
            return
        
        try:
            # 1. Extracción de texto usando el DocumentProcessor existente
            docs = self.processor.process(files)
            if not docs:
                yield json.dumps(
                    build_error_result(
                        "other",
                        "No se pudieron extraer textos de los PDFs. El archivo puede estar encriptado o corrupto.",
                    ),
                    ensure_ascii=False,
                )
                return

            # 2. Agrupar por archivo de origen
            docs_by_file: Dict[str, List[Document]] = defaultdict(list)
            for doc in docs:
                source = doc.metadata.get("source", "") or getattr(doc, "source", "")
                if not source:
                    source = "unknown"
                docs_by_file[source].append(doc)

            # 3. Procesar cada archivo de forma independiente
            results: Dict[str, Dict[str, Any]] = {}

            for source, file_docs in docs_by_file.items():
                file_name = Path(source).name

                # 3.1 Chunking: máx. 2 páginas por chunk (aprox. por documento)
                sorted_docs = sorted(
                    file_docs,
                    key=lambda d: d.metadata.get("page", d.metadata.get("page_number", 0)),
                )
                chunks: List[str] = []
                for i in range(0, len(sorted_docs), 2):
                    sub_docs = sorted_docs[i : i + 2]
                    chunk_text = "\n\n".join(d.page_content for d in sub_docs if d.page_content)
                    if chunk_text.strip():
                        chunks.append(chunk_text)

                if not chunks:
                    results[file_name] = build_error_result(
                        "other",
                        "No se encontró texto legible en el documento.",
                    )
                    continue

                # 3.2 Clasificación del documento (usando el primer chunk)
                classification = self._classify_document(chunks[0])
                document_type = classification.get("document_type", "other")
                doc_confidence = classification.get("confidence", 0.0)

                # 3.3 Extracción estructurada según schema (con posible retry si la validación falla)
                extraction_result = self._extract_structured_data(
                    document_type=document_type,
                    chunks=chunks,
                )

                final_result: Dict[str, Any]
                if extraction_result.get("status") == "success":
                    extraction_conf = float(extraction_result.get("confidence", 0.0))
                    combined_conf = max(0.0, min(1.0, (float(doc_confidence) + extraction_conf) / 2.0))
                    data = extraction_result.get("data", {})

                    # Primer intento de validación Pydantic
                    try:
                        validated_data = validate_data_for_type(document_type, data)
                        final_result = build_success_result(
                            document_type=document_type,
                            data=validated_data,
                            confidence=combined_conf,
                        )
                    except Exception as ve:
                        # Retry ÚNICO: informar al modelo que el JSON no coincide con el schema
                        retry_extraction = self._extract_structured_data(
                            document_type=document_type,
                            chunks=chunks,
                            retry_error=str(ve),
                        )
                        if retry_extraction.get("status") == "success":
                            try:
                                retry_data = retry_extraction.get("data", {})
                                validated_retry_data = validate_data_for_type(document_type, retry_data)
                                final_result = build_success_result(
                                    document_type=document_type,
                                    data=validated_retry_data,
                                    confidence=combined_conf,
                                )
                            except Exception as ve2:
                                final_result = build_error_result(
                                    document_type,
                                    f"validation_error: {str(ve2)}",
                                )
                        else:
                            final_result = build_error_result(
                                document_type,
                                extraction_result.get("data", {}).get("error", "Unknown extraction error."),
                            )
                else:
                    final_result = build_error_result(
                        document_type,
                        extraction_result.get("data", {}).get("error", "Unknown extraction error."),
                    )

                results[file_name] = final_result

                # Emitir resultado por archivo como JSON puro
                yield f"### 📄 {file_name}\n\n"
                yield "```json\n"
                yield json.dumps(final_result, ensure_ascii=False, indent=2)
                yield "\n```\n\n"

            # 4. Resumen global en JSON (útil si se usa como servicio backend)
            yield "### 🧾 Global Result (all files)\n\n"
            yield "```json\n"
            yield json.dumps(results, ensure_ascii=False, indent=2)
            yield "\n```\n"
            
        except Exception as e:
            error_payload = build_error_result("other", f"Unexpected error: {str(e)}")
            yield json.dumps(error_payload, ensure_ascii=False)
    
    def process_documents_with_workflows(
        self,
        files: List,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        [LEGACY] Sistema de workflows agentic.
        Ya no se usa en el nuevo modo PDF -> JSON; se mantiene solo por compatibilidad.
        """
        try:
            # 1. Procesar documentos (extraer texto)
            print("📄 Procesando documentos...")
            docs = self.processor.process(files)
            
            if not docs or len(docs) == 0:
                return {
                    "status": "error",
                    "error": "No se pudieron procesar los documentos",
                    "timestamp": datetime.now().isoformat()
                }
            
            print(f"✅ {len(docs)} documentos procesados")
            
            # 2. Usar orquestador para clasificar y ejecutar workflows
            print("🤖 Clasificando y ejecutando workflows...")
            result = self.orchestrator.process_documents(docs, dry_run=dry_run)
            
            return result
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    # ------------------------------------------------------------------
    # NUEVOS HELPERS: CLASIFICACIÓN + EXTRACCIÓN ESTRUCTURADA (SLM)
    # ------------------------------------------------------------------

    def _classify_document(self, text_chunk: str) -> Dict[str, Any]:
        """
        Clasifica el documento en uno de los tipos soportados usando el SLM.
        Prompt EXACTO (system + user) y salida JSON ONLY.
        """
        system_prompt = (
            "You are a document classification system.\n\n"
            "You must classify the document into ONE of the following types:\n"
            "- contract\n"
            "- invoice\n"
            "- resume\n"
            "- report\n"
            "- policy\n"
            "- legal_notice\n"
            "- other\n\n"
            "Return ONLY valid JSON.\n"
            "Do not explain.\n"
            "Do not add extra text.\n"
        )

        user_prompt = (
            "Classify the following document text.\n\n"
            "Return JSON in this exact format:\n"
            "{\n"
            '  "document_type": "one_of_the_allowed_types",\n'
            '  "confidence": number_between_0_and_1\n'
            "}\n\n"
            "Document text:\n"
            "<<<\n"
            f"{text_chunk}\n"
            ">>>\n"
        )

        try:
            response = self.slm_llm.invoke(
                [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
            )
            raw = response.content if hasattr(response, "content") else str(response)
            raw = raw.strip()
            # Intentar limpiar code fences si las hubiera
            if raw.startswith("```"):
                raw = raw.strip("`")
                # Quitar posible "json" al inicio
                if raw.lower().startswith("json"):
                    raw = raw[4:].lstrip()
            data = json.loads(raw)
        except Exception:
            # Fallback seguro
            return {"document_type": "other", "confidence": 0.0}

        doc_type = str(data.get("document_type", "other")).strip()
        allowed = {
            "contract",
            "invoice",
            "resume",
            "report",
            "policy",
            "legal_notice",
            "other",
        }
        if doc_type not in allowed:
            doc_type = "other"

        try:
            conf = float(data.get("confidence", 0.0))
        except Exception:
            conf = 0.0
        conf = max(0.0, min(1.0, conf))

        return {"document_type": doc_type, "confidence": conf}

    def _extract_structured_data(
        self,
        document_type: str,
        chunks: List[str],
        retry_error: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Extrae datos estructurados para un tipo de documento dado.
        - Procesa chunk por chunk con el SLM.
        - Fusiona resultados en código.
        - No realiza validación Pydantic (se hace fuera); pero soporta un mensaje
          adicional `retry_error` para el retry cuando falle la validación externa.
        """
        # Seleccionar schema textual según tipo
        if document_type == "contract":
            schema_text = (
                '{\n'
                '  "parties": ["string"],\n'
                '  "start_date": "YYYY-MM-DD | null",\n'
                '  "end_date": "YYYY-MM-DD | null",\n'
                '  "payment_terms": "string | null",\n'
                '  "termination_clause": "boolean",\n'
                '  "jurisdiction": "string | null"\n'
                "}\n"
            )
        elif document_type == "invoice":
            schema_text = (
                '{\n'
                '  "invoice_number": "string",\n'
                '  "issuer": "string",\n'
                '  "recipient": "string",\n'
                '  "total_amount": "number",\n'
                '  "currency": "string",\n'
                '  "due_date": "YYYY-MM-DD | null"\n'
                "}\n"
            )
        elif document_type == "resume":
            schema_text = (
                '{\n'
                '  "name": "string",\n'
                '  "email": "string | null",\n'
                '  "skills": ["string"],\n'
                '  "years_experience": "number | null"\n'
                "}\n"
            )
        else:
            # Para otros tipos, devolvemos data vacía (schema genérico)
            return {
                "status": "success",
                "data": {},
                "confidence": 0.0,
            }

        system_prompt = (
            "You are an information extraction system.\n\n"
            "Return ONLY valid JSON.\n"
            "Do not explain.\n"
            "Do not infer missing information.\n"
            "If a field is not explicitly present in the text, use null.\n"
            "Follow the schema EXACTLY.\n"
        )

        if retry_error:
            # Mensaje adicional para el retry
            system_prompt += (
                "\nThe previous JSON did not match the schema.\n"
                "Fix the JSON.\n"
                "Return ONLY valid JSON.\n"
            )

        merged: Dict[str, Any] = {}

        for chunk_text in chunks:
            if not chunk_text.strip():
                continue

            user_prompt = (
                f"Extract structured data for a document of type: {document_type}.\n\n"
                "Use this schema:\n"
                f"{schema_text}\n\n"
                "Text:\n"
                "<<<\n"
                f"{chunk_text}\n"
                ">>>\n"
            )

            try:
                response = self.slm_llm.invoke(
                    [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
                )
                raw = response.content if hasattr(response, "content") else str(response)
                raw = raw.strip()
                if raw.startswith("```"):
                    raw = raw.strip("`")
                    if raw.lower().startswith("json"):
                        raw = raw[4:].lstrip()
                partial = json.loads(raw)
            except Exception as e:
                # Si falla un chunk, continuar con los que sí funcionen
                continue

            # Fusionar resultados (listas se unen, strings/números se rellenan si están vacíos)
            for key, value in partial.items():
                if key not in merged or merged.get(key) in (None, "", [], {}):
                    merged[key] = value
                else:
                    # Si ambos son listas -> concatenar y deduplicar
                    if isinstance(merged[key], list) and isinstance(value, list):
                        merged[key] = list({*merged[key], *value})
                    # Si es boolean -> OR lógico
                    elif isinstance(merged[key], bool) and isinstance(value, bool):
                        merged[key] = merged[key] or value
                    # Si es número y el existente es None o 0 -> reemplazar
                    elif isinstance(merged[key], (int, float)) and isinstance(value, (int, float)):
                        if merged[key] == 0 and value != 0:
                            merged[key] = value
                    # Para strings ya presentes, mantenemos el primero (no sobrescribir)

        # Si no pudimos extraer nada, devolver error controlado
        if not merged:
            return {
                "status": "error",
                "data": {"error": "No se pudo extraer información estructurada del documento."},
                "confidence": 0.0,
            }

        return {
            "status": "success",
            "data": merged,
            "confidence": 1.0,
        }

    # ------------------------------------------------------------------
    # VERSIÓN NO STREAMING: PDF -> JSON POR ARCHIVO (BACKEND / API)
    # ------------------------------------------------------------------

    def process_enterprise_documents(
        self,
        files: List,
        auto_detect: bool = True,
        rules: Optional[List[Dict]] = None,
        stream: bool = False,
    ) -> Dict[str, Any]:
        """
        Versión NO streaming del servicio PDF → JSON.
        Devuelve un diccionario por archivo, listo para API / webhooks / DB.

        Formato:
        {
          "file_1.pdf": { ... },
          "file_2.pdf": { ... }
        }
        """
        backend_results: Dict[str, Any] = {}

        # 1. Procesar documentos (extracción de texto)
        docs = self.processor.process(files)
        if not docs:
            return {
                "status": "error",
                "reason": "no_text_extracted",
            }

        # 2. Agrupar por archivo de origen
        docs_by_file: Dict[str, List[Document]] = defaultdict(list)
        for doc in docs:
            source = doc.metadata.get("source", "") or getattr(doc, "source", "")
            if not source:
                source = "unknown"
            docs_by_file[source].append(doc)

        # 3. Procesar cada archivo de forma independiente
        for source, file_docs in docs_by_file.items():
            file_name = Path(source).name

            # Chunking 2 páginas
            sorted_docs = sorted(
                file_docs,
                key=lambda d: d.metadata.get("page", d.metadata.get("page_number", 0)),
            )
            chunks: List[str] = []
            for i in range(0, len(sorted_docs), 2):
                sub_docs = sorted_docs[i : i + 2]
                chunk_text = "\n\n".join(d.page_content for d in sub_docs if d.page_content)
                if chunk_text.strip():
                    chunks.append(chunk_text)

            if not chunks:
                backend_results[file_name] = build_error_result(
                    "other",
                    "No se encontró texto legible en el documento.",
                )
                continue

            # Clasificación
            classification = self._classify_document(chunks[0])
            document_type = classification.get("document_type", "other")
            doc_confidence = classification.get("confidence", 0.0)

            # Extracción estructurada + validación (mismo flujo que streaming)
            extraction_result = self._extract_structured_data(
                document_type=document_type,
                chunks=chunks,
            )

            if extraction_result.get("status") == "success":
                extraction_conf = float(extraction_result.get("confidence", 0.0))
                combined_conf = max(0.0, min(1.0, (float(doc_confidence) + extraction_conf) / 2.0))
                data = extraction_result.get("data", {})

                try:
                    validated_data = validate_data_for_type(document_type, data)
                    final_result = build_success_result(
                        document_type=document_type,
                        data=validated_data,
                        confidence=combined_conf,
                    )
                except Exception as ve:
                    # Retry único con mensaje de error para el modelo
                    retry_extraction = self._extract_structured_data(
                        document_type=document_type,
                        chunks=chunks,
                        retry_error=str(ve),
                    )
                    if retry_extraction.get("status") == "success":
                        try:
                            retry_data = retry_extraction.get("data", {})
                            validated_retry_data = validate_data_for_type(document_type, retry_data)
                            final_result = build_success_result(
                                document_type=document_type,
                                data=validated_retry_data,
                                confidence=combined_conf,
                            )
                        except Exception as ve2:
                            final_result = build_error_result(
                                document_type,
                                f"validation_error: {str(ve2)}",
                            )
                    else:
                        final_result = build_error_result(
                            document_type,
                            extraction_result.get("data", {}).get("error", "Unknown extraction error."),
                        )
            else:
                final_result = build_error_result(
                    document_type,
                    extraction_result.get("data", {}).get("error", "Unknown extraction error."),
                )

            backend_results[file_name] = final_result

        return backend_results
    
    def process_enterprise_documents_api(
        self,
        files: List,
        auto_detect: bool = True,
        rules: Optional[List[Dict]] = None,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        Función pública de API que procesa documentos y devuelve JSON puro.
        Simplemente llama a process_enterprise_documents y devuelve el resultado tal cual.
        
        Args:
            files: Lista de archivos a procesar
            auto_detect: Ignorado (mantenido para compatibilidad)
            rules: Ignorado (mantenido para compatibilidad)
            stream: Ignorado (mantenido para compatibilidad)
        
        Returns:
            Dict con formato: { "file.pdf": { "status": "...", "document_type": "...", "data": {...}, "confidence": 0.0-1.0 } }
        """
        return self.process_enterprise_documents(files=files, auto_detect=auto_detect, rules=rules, stream=stream)
    
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
        
        # Construir contexto optimizado para soportar documentos grandes
        # OPTIMIZADO para aprovechar context windows grandes (128k OpenAI, 200k Claude)
        context_parts = []
        total_chars = 0
        # Aumentado significativamente para aprovechar context windows grandes
        # 128k tokens = ~512k caracteres, 200k tokens = ~800k caracteres
        max_chars = 50000 if self.provider == "openai" else 80000  # Claude puede manejar más
        
        # Aumentar número de chunks para documentos grandes
        max_chunks = 50 if self.provider == "openai" else 80  # Claude puede procesar más
        
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
            # Usar LLM rápido para detección (optimización de velocidad)
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
                    "summary": "Reporte automático generado por ADVICE GOD",
                    "timestamp": datetime.now().isoformat(),
                    "documents_analyzed": len(docs),
                    "problems": results.get("problems_detected", []),
                    "opportunities": results.get("opportunities_detected", [])
                }
                result = report_tool.execute(
                    data=report_data,
                    format="excel",
                    title="Reporte Automático ADVICE GOD"
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


# Instancia global
_advice_god_mode_instance: Optional[AdviceGodMode] = None


def get_advice_god_mode(
    config: AppConfig,
    provider: str = "openai"
) -> AdviceGodMode:
    """Obtiene o crea la instancia global de ADVICE GOD Mode."""
    global _advice_god_mode_instance
    
    if _advice_god_mode_instance is None:
        _advice_god_mode_instance = AdviceGodMode(
            config=config,
            provider=provider
        )
    
    return _advice_god_mode_instance


def run_advice_god_mode(
    files: List[Any],
    auto_detect: bool = True,
    rules: Optional[List[Dict]] = None,
    stream: bool = False,
    config: Optional[AppConfig] = None,
    provider: str = "openai"
) -> Any:
    """Ejecuta ADVICE GOD Mode con los archivos proporcionados."""
    if config is None:
        from .config import load_config
        config = load_config()
    
    advice_god = get_advice_god_mode(config=config, provider=provider)
    
    if stream:
        return advice_god.process_enterprise_documents_streaming(
            files=files,
            auto_detect=auto_detect,
            rules=rules
        )
    else:
        return advice_god.process_enterprise_documents(
            files=files,
            auto_detect=auto_detect,
            rules=rules,
            stream=False
        )
