"""Enterprise API Supreme Mode - Optimizado según principios de Eric Schmidt.

Este modo integra las mejores prácticas de:
- MDP (Model-Document Protocol) para procesamiento masivo
- Gist memories persistentes para filtrado agresivo
- Extracción estructurada (semantic ETL) para contratos, finanzas, etc.
- NL2SQL/NL2Query para consultas precisas sobre datos estructurados
- Agentes especializados (contratos, financiero, comparativo)
- Análisis comparativo por defecto
- Verificación de IA por IA
- Procesamiento masivo en paralelo (scale computing)
- Map-reduce synthesis para contexto compacto LLM-ready

Optimizado para procesar 100-500+ PDFs con máxima eficiencia y precisión.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional, Iterator, Tuple
from datetime import datetime
from pathlib import Path
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

from langchain_core.documents import Document

from .config import AppConfig
from .document_processor import DocumentProcessor
from .mass_processor import MassDocumentProcessor, DocumentMetadata, ComparativeAnalysis
from .retriever_builder import RetrieverBuilder
from .memory import MemoryStore, ContextManager


@dataclass
class DocumentGist:
    """Gist/memoria ligera por documento (MDP-style)."""
    file_name: str
    file_hash: str
    text_sample: str
    chunk_count: int
    size_mb: float
    document_type: str = "unknown"
    key_entities: List[str] = None
    key_topics: List[str] = None
    
    def __post_init__(self):
        if self.key_entities is None:
            self.key_entities = []
        if self.key_topics is None:
            self.key_topics = []


@dataclass
class StructuredData:
    """Datos estructurados extraídos de documentos (semantic ETL)."""
    document_id: str
    document_type: str  # "contract", "invoice", "report", "financial_statement", etc.
    extracted_fields: Dict[str, Any]  # Campos específicos según tipo
    entities: List[Dict[str, str]]  # Entidades con tipo y valor
    dates: List[Dict[str, str]]  # Fechas con tipo (inicio, fin, vencimiento, etc.)
    amounts: List[Dict[str, Any]]  # Montos con moneda y tipo
    risk_flags: List[str] = None
    opportunity_flags: List[str] = None
    
    def __post_init__(self):
        if self.risk_flags is None:
            self.risk_flags = []
        if self.opportunity_flags is None:
            self.opportunity_flags = []


class EnterpriseAPISupremeMode:
    """
    Modo Enterprise API Supreme - Optimizado según principios de Eric Schmidt.
    
    Características principales:
    - Procesamiento masivo paralelo (100-500+ PDFs)
    - Gist memories persistentes para filtrado rápido
    - Extracción estructurada (semantic ETL) por dominio
    - NL2SQL/NL2Query para consultas precisas
    - Agentes especializados trabajando en paralelo
    - Análisis comparativo por defecto
    - Verificación de IA por IA
    - Map-reduce synthesis para contexto compacto
    """
    
    def __init__(self, config: AppConfig, provider: str = "openai"):
        self.config = config
        self.provider = provider
        
        # Procesadores
        self.processor = DocumentProcessor(config)
        self.mass_processor = MassDocumentProcessor(config)
        self.retriever_builder = RetrieverBuilder(config)
        
        # Memoria y contexto
        self.memory_store = MemoryStore(config.memory_dir, config.memory_retention_days) if config.enable_memory else None
        self.context_manager = ContextManager(self.memory_store, config) if self.memory_store else None
        
        # Sistema de Consultas Estratégicas Enterprise
        self.query_history_file = Path(config.memory_dir) / "enterprise_query_history.json"
        self.query_history = self._load_query_history()
        
        # Directorio para gist memories persistentes
        self.gist_memories_dir = Path(config.memory_dir) / "gist_memories" if config.memory_dir else Path("semantic_data")
        self.gist_memories_dir.mkdir(parents=True, exist_ok=True)
        self.gist_memories_file = self.gist_memories_dir / "gist_memories.json"
        
        # Directorio para datos estructurados
        self.structured_data_dir = Path(config.memory_dir) / "structured_data" if config.memory_dir else Path("semantic_data")
        self.structured_data_dir.mkdir(parents=True, exist_ok=True)
        
        # LLMs
        from docchat.utils.llm_factory import create_llm
        
        # LLM fuerte para razonamiento final
        self.reasoning_llm = create_llm(
            provider=provider,
            model=config.agentic_model,
            temperature=0.2,
            api_key=config.openai_api_key if provider == "openai" else config.anthropic_api_key,
            max_tokens=8000,
            request_timeout=120,
        )
        
        # LLM rápido para gists, filtrado, extracción (optimización de costos)
        fast_model = "gpt-4o-mini" if provider == "openai" else "claude-haiku-4-5-20251001"
        self.fast_llm = create_llm(
            provider=provider,
            model=fast_model,
            temperature=0.2,
            api_key=config.openai_api_key if provider == "openai" else config.anthropic_api_key,
            max_tokens=4000,
            request_timeout=60,
        )
        
        # LLM para resúmenes de documentos (necesita más tokens para resúmenes completos)
        self.summary_llm = create_llm(
            provider=provider,
            model=fast_model,
            temperature=0.2,
            api_key=config.openai_api_key if provider == "openai" else config.anthropic_api_key,
            max_tokens=2000,  # Suficiente para resúmenes completos de 3-5 párrafos
            request_timeout=90,
        )
        
        # LLM verificador (para IA verificando IA)
        self.verifier_llm = create_llm(
            provider=provider,
            model=fast_model,  # Usar modelo rápido para verificación
            temperature=0.1,  # Más determinista
            api_key=config.openai_api_key if provider == "openai" else config.anthropic_api_key,
            max_tokens=2000,
            request_timeout=60,
        )
        
        # Cargar gist memories existentes
        self.gist_memories = self._load_gist_memories()
        
        # Almacén de datos estructurados en memoria (para consultas rápidas)
        self.structured_data_store: Dict[str, StructuredData] = {}
    
    def _load_gist_memories(self) -> Dict[str, Dict[str, Any]]:
        """Carga gist memories persistentes desde disco."""
        if self.gist_memories_file.exists():
            try:
                with open(self.gist_memories_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️ Error cargando gist memories: {e}")
        return {}
    
    def _save_gist_memories(self):
        """Guarda gist memories persistentes en disco."""
        try:
            with open(self.gist_memories_file, 'w', encoding='utf-8') as f:
                json.dump(self.gist_memories, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️ Error guardando gist memories: {e}")
    
    def _save_structured_data(self, structured_data_list: List[StructuredData]):
        """Guarda datos estructurados persistentemente para consultas."""
        try:
            structured_data_file = self.structured_data_dir / "structured_data.json"
            data_to_save = [asdict(sd) for sd in structured_data_list]
            with open(structured_data_file, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            print(f"⚠️ Error guardando datos estructurados: {e}")
    
    def _load_structured_data(self) -> List[StructuredData]:
        """Carga datos estructurados persistentes."""
        try:
            structured_data_file = self.structured_data_dir / "structured_data.json"
            if structured_data_file.exists():
                with open(structured_data_file, 'r', encoding='utf-8') as f:
                    data_list = json.load(f)
                    return [StructuredData(**sd) for sd in data_list]
        except Exception as e:
            print(f"⚠️ Error cargando datos estructurados: {e}")
        return []
    
    def _load_gists_from_memory(self) -> List[DocumentGist]:
        """Carga gists desde memoria persistente y los convierte a objetos DocumentGist."""
        gists = []
        for gist_data in self.gist_memories.values():
            gist = DocumentGist(
                file_name=gist_data.get("file_name", ""),
                file_hash=gist_data.get("file_hash", ""),
                text_sample=gist_data.get("text_sample", ""),
                chunk_count=gist_data.get("chunk_count", 0),
                size_mb=gist_data.get("size_mb", 0.0),
                document_type=gist_data.get("document_type", "unknown"),
                key_entities=gist_data.get("key_entities", []),
                key_topics=gist_data.get("key_topics", []),
            )
            gists.append(gist)
        return gists
    
    def process_enterprise_documents_streaming(
        self,
        files: List,
        auto_detect: bool = True,
        rules: Optional[List[Dict]] = None,
        enable_comparative: bool = True,  # Análisis comparativo por defecto
        enable_structured_extraction: bool = True,  # Extracción estructurada por defecto
    ) -> Iterator[str]:
        """
        Procesa documentos con streaming de resultados (pipeline optimizado tipo Eric Schmidt).
        
        Pipeline:
        1. Procesamiento masivo paralelo (ingestión)
        2. Construcción de gist memories persistentes
        3. Filtrado agresivo usando gists + LLM rápido
        4. Extracción estructurada en paralelo (semantic ETL)
        5. Análisis comparativo automático
        6. Map-reduce synthesis en contexto compacto
        7. Verificación de IA por IA
        8. Resumen ejecutivo final
        """
        yield "## 👑 Enterprise API Supreme - Pipeline Optimizado (Eric Schmidt Style)\n\n"
        yield f"📄 Documentos recibidos: {len(files)}\n\n"
        
        try:
            # ============================================================
            # FASE 1: PROCESAMIENTO MASIVO PARALELO (Scale Computing)
            # ============================================================
            yield "### ⚙️ FASE 1: Procesamiento Masivo en Paralelo\n\n"
            chunks, metadata_list, comparative = self.mass_processor.process_massive_batch(
                files=files,
                enable_comparison=enable_comparative,
            )
            yield f"- ✅ Chunks generados: {len(chunks)}\n"
            yield f"- ✅ Documentos exitosos: {sum(1 for m in metadata_list if m.chunk_count > 0)}\n"
            if comparative:
                yield f"- ✅ Análisis comparativo: {len(comparative.common_themes)} temas comunes\n"
            yield "\n"
            
            # ============================================================
            # FASE 2: CONSTRUCCIÓN DE GIST MEMORIES PERSISTENTES
            # ============================================================
            yield "### 🧠 FASE 2: Construyendo Gist Memories Persistentes\n\n"
            gists = self._build_enhanced_gists(chunks, metadata_list)
            yield f"- ✅ Gists generadas: {len(gists)}\n\n"
            
            # Guardar gists en memoria persistente
            for gist in gists:
                gist_key = gist.file_hash or Path(gist.file_name).stem
                self.gist_memories[gist_key] = {
                    "file_name": gist.file_name,
                    "file_hash": gist.file_hash,
                    "text_sample": gist.text_sample[:2000],  # Limitar tamaño
                    "chunk_count": gist.chunk_count,
                    "size_mb": gist.size_mb,
                    "document_type": gist.document_type,
                    "key_entities": gist.key_entities[:10],
                    "key_topics": gist.key_topics[:10],
                    "last_updated": datetime.now().isoformat(),
                }
            self._save_gist_memories()
            yield "✅ Gist memories guardadas persistentemente\n\n"
            
            # ============================================================
            # FASE 3: FILTRADO AGRESIVO CON GISTS + LLM RÁPIDO
            # ============================================================
            yield "### 🔍 FASE 3: Filtrado Agresivo (Memory-Guided Filtering)\n\n"
            relevant_gists = self._filter_gists_aggressive(gists)
            yield f"- ✅ Documentos relevantes: {len(relevant_gists)}/{len(gists)} "
            yield f"({len(relevant_gists)/len(gists)*100:.1f}% retención)\n\n"
            
            if not relevant_gists:
                yield "⚠️ Ningún documento fue considerado claramente relevante. Mostrando visión global.\n\n"
                relevant_gists = gists  # Fallback: usar todos
            
            # ============================================================
            # FASE 4: EXTRACCIÓN ESTRUCTURADA EN PARALELO (Semantic ETL)
            # ============================================================
            if enable_structured_extraction:
                yield "### 🏗️ FASE 4: Extracción Estructurada en Paralelo (Semantic ETL)\n\n"
                structured_data_list = self._extract_structured_data_parallel(chunks, relevant_gists)
                yield f"- ✅ Documentos con datos estructurados: {len(structured_data_list)}\n"
                
                # Guardar en almacén interno
                for sd in structured_data_list:
                    self.structured_data_store[sd.document_id] = sd
                
                # Guardar datos estructurados persistentemente para consultas
                if structured_data_list:
                    self._save_structured_data(structured_data_list)
                
                # Mostrar resumen de extracción
                contract_count = sum(1 for sd in structured_data_list if sd.document_type == "contract")
                financial_count = sum(1 for sd in structured_data_list if sd.document_type in ["invoice", "financial_statement", "balance_sheet"])
                yield f"- 📄 Contratos: {contract_count}\n"
                yield f"- 💰 Documentos financieros: {financial_count}\n\n"
            
            # ============================================================
            # FASE 5: ANÁLISIS COMPARATIVO (Por Defecto)
            # ============================================================
            if enable_comparative and comparative:
                yield "### 📊 FASE 5: Análisis Comparativo Automático\n\n"
                comparative_insights = self._generate_comparative_insights(comparative, structured_data_list if enable_structured_extraction else [])
                yield comparative_insights + "\n\n"
            
            # ============================================================
            # FASE 6: MAP-REDUCE SYNTHESIS (Contexto Compacto LLM-Ready)
            # ============================================================
            yield "### 🧩 FASE 6: Síntesis Map-Reduce (Contexto Compacto)\n\n"
            mdp_context, mdp_summary = self._synthesize_mdp_context_enhanced(
                chunks, relevant_gists, 
                structured_data_list if enable_structured_extraction else [],
                comparative
            )
            yield mdp_summary + "\n\n"
            
            # ============================================================
            # FASE 7: DETECCIÓN AUTOMÁTICA (Si está habilitada)
            # ============================================================
            detection_results = {"problems": [], "opportunities": [], "patterns": []}
            if auto_detect:
                yield "### 🔎 FASE 7: Detección Automática sobre Contexto MDP\n\n"
                detection_results = self._auto_detect_from_enhanced_context(
                    mdp_context, structured_data_list if enable_structured_extraction else []
                )
                if detection_results.get("problems"):
                    yield f"- ⚠️ Problemas: {len(detection_results['problems'])}\n"
                if detection_results.get("opportunities"):
                    yield f"- 💡 Oportunidades: {len(detection_results['opportunities'])}\n"
                if detection_results.get("patterns"):
                    yield f"- 🔍 Patrones: {len(detection_results['patterns'])}\n"
                yield "\n"
            
            # ============================================================
            # FASE 8: VERIFICACIÓN DE IA POR IA
            # ============================================================
            yield "### ✅ FASE 8: Verificación de IA por IA\n\n"
            verification_results = self._verify_with_ai(detection_results, mdp_context)
            if verification_results.get("verified"):
                yield f"- ✅ Verificación exitosa: {verification_results.get('confidence', 'N/A')}\n"
            if verification_results.get("inconsistencies"):
                yield f"- ⚠️ Inconsistencias detectadas: {len(verification_results['inconsistencies'])}\n"
            yield "\n"
            
            # ============================================================
            # FASE 8.5: RESPUESTAS POR DOCUMENTO (Análisis Individual)
            # ============================================================
            yield "### 📄 FASE 8.5: Análisis Individual por Documento\n\n"
            per_document_analysis = self._generate_per_document_analysis(
                relevant_gists, 
                structured_data_list if enable_structured_extraction else [],
                chunks
            )
            yield per_document_analysis + "\n\n"
            
            # ============================================================
            # FASE 9: RESUMEN EJECUTIVO FINAL
            # ============================================================
            yield "### 📊 FASE 9: Resumen Ejecutivo Final (Tipo Consultor C-Level)\n\n"
            executive_report = self._generate_executive_report_enhanced(
                mdp_context, detection_results, verification_results,
                structured_data_list if enable_structured_extraction else [],
                comparative
            )
            yield executive_report + "\n\n"
            
            # ============================================================
            # FASE 10: GUARDAR EN MEMORIA PERSISTENTE
            # ============================================================
            if self.context_manager:
                yield "### 💾 Guardando en Memoria Persistente...\n\n"
                self._save_to_memory_enhanced(
                    mdp_context, detection_results, structured_data_list if enable_structured_extraction else []
                )
                yield "✅ Memoria actualizada\n\n"
            
            yield "✅ **Procesamiento Enterprise API Supreme completado exitosamente!**\n"
            yield f"\n📈 **Métricas Finales:**\n"
            yield f"- Documentos enviados: {len(files)}\n"
            yield f"- Documentos procesados exitosamente: {sum(1 for m in metadata_list if m.chunk_count > 0)}\n"
            yield f"- Documentos con errores: {sum(1 for m in metadata_list if m.chunk_count == 0)}\n"
            yield f"- Chunks generados: {len(chunks)}\n"
            yield f"- Gists persistentes: {len(self.gist_memories)}\n"
            if enable_structured_extraction:
                yield f"- Datos estructurados: {len(structured_data_list)}\n"
            yield f"- Problemas detectados: {len(detection_results.get('problems', []))}\n"
            yield f"- Oportunidades detectadas: {len(detection_results.get('opportunities', []))}\n"
            
            # Listar documentos procesados
            yield f"\n📋 **Documentos Procesados:**\n"
            for gist in relevant_gists:
                file_name = Path(gist.file_name).name
                yield f"- ✅ {file_name} ({gist.document_type}, {gist.chunk_count} chunks)\n"
            
            # Listar documentos con errores
            failed_docs = [m for m in metadata_list if m.chunk_count == 0]
            if failed_docs:
                yield f"\n⚠️ **Documentos con Errores:**\n"
                for m in failed_docs:
                    yield f"- ❌ {m.file_name} (no se generaron chunks)\n"
            
        except Exception as e:
            yield f"\n❌ **Error en Enterprise API Supreme**: {str(e)}\n"
            import traceback
            yield f"\n```\n{traceback.format_exc()}\n```\n"
    
    def process_enterprise_documents(
        self,
        files: List,
        auto_detect: bool = True,
        rules: Optional[List[Dict]] = None,
        stream: bool = False,
        enable_comparative: bool = True,
        enable_structured_extraction: bool = True,
    ) -> Dict[str, Any]:
        """
        Versión no streaming: devuelve un dict con resultados completos.
        """
        results: Dict[str, Any] = {
            "status": "processing",
            "timestamp": datetime.now().isoformat(),
            "documents_processed": len(files),
            "chunks_generated": 0,
            "gists": [],
            "relevant_gists": [],
            "structured_data": [],
            "mdp_context": "",
            "mdp_summary": "",
            "comparative_analysis": None,
            "problems_detected": [],
            "opportunities_detected": [],
            "patterns_found": [],
            "verification_results": {},
            "executive_report": "",
        }
        
        try:
            # Procesamiento masivo
            chunks, metadata_list, comparative = self.mass_processor.process_massive_batch(
                files=files,
                enable_comparison=enable_comparative,
            )
            results["chunks_generated"] = len(chunks)
            results["comparative_analysis"] = comparative.__dict__ if comparative else None
            
            # Gists
            gists = self._build_enhanced_gists(chunks, metadata_list)
            results["gists"] = [asdict(g) for g in gists]
            
            # Guardar gists persistentes
            for gist in gists:
                gist_key = gist.file_hash or Path(gist.file_name).stem
                self.gist_memories[gist_key] = {
                    "file_name": gist.file_name,
                    "file_hash": gist.file_hash,
                    "text_sample": gist.text_sample[:2000],
                    "chunk_count": gist.chunk_count,
                    "size_mb": gist.size_mb,
                    "document_type": gist.document_type,
                    "key_entities": gist.key_entities[:10],
                    "key_topics": gist.key_topics[:10],
                    "last_updated": datetime.now().isoformat(),
                }
            self._save_gist_memories()
            
            # Filtrado
            relevant_gists = self._filter_gists_aggressive(gists)
            results["relevant_gists"] = [asdict(g) for g in relevant_gists]
            
            # Extracción estructurada
            structured_data_list = []
            if enable_structured_extraction:
                structured_data_list = self._extract_structured_data_parallel(chunks, relevant_gists)
                results["structured_data"] = [asdict(sd) for sd in structured_data_list]
                for sd in structured_data_list:
                    self.structured_data_store[sd.document_id] = sd
            
            # Síntesis MDP
            mdp_context, mdp_summary = self._synthesize_mdp_context_enhanced(
                chunks, relevant_gists, structured_data_list, comparative
            )
            results["mdp_context"] = mdp_context
            results["mdp_summary"] = mdp_summary
            
            # Detección automática
            if auto_detect:
                detection_results = self._auto_detect_from_enhanced_context(mdp_context, structured_data_list)
                results["problems_detected"] = detection_results.get("problems", [])
                results["opportunities_detected"] = detection_results.get("opportunities", [])
                results["patterns_found"] = detection_results.get("patterns", [])
            else:
                detection_results = {"problems": [], "opportunities": [], "patterns": []}
            
            # Verificación
            verification_results = self._verify_with_ai(detection_results, mdp_context)
            results["verification_results"] = verification_results
            
            # Reporte ejecutivo
            executive_report = self._generate_executive_report_enhanced(
                mdp_context, detection_results, verification_results,
                structured_data_list, comparative
            )
            results["executive_report"] = executive_report
            
            # Guardar en memoria
            if self.context_manager:
                self._save_to_memory_enhanced(mdp_context, detection_results, structured_data_list)
            
            results["status"] = "completed"
            
        except Exception as e:
            results["status"] = "error"
            results["error"] = str(e)
        
        return results
    
    # ============================================================
    # MÉTODOS INTERNOS - PIPELINE OPTIMIZADO
    # ============================================================
    
    def _build_enhanced_gists(
        self,
        chunks: List[Document],
        metadata_list: List[DocumentMetadata],
    ) -> List[DocumentGist]:
        """
        Construye gists mejoradas con más metadata (tipo, entidades, temas).
        """
        from collections import defaultdict
        
        docs_by_file: Dict[str, List[Document]] = defaultdict(list)
        for doc in chunks:
            src = doc.metadata.get("source") or doc.metadata.get("file_name") or "documento"
            docs_by_file[src].append(doc)
        
        meta_by_name: Dict[str, DocumentMetadata] = {m.file_name: m for m in metadata_list}
        
        gists: List[DocumentGist] = []
        for file_name, docs_for_file in docs_by_file.items():
            meta = meta_by_name.get(file_name)
            
            # Muestra de texto
            sample_chunks = docs_for_file[:5]
            sample_text_parts = []
            total_chars = 0
            max_chars = 2000
            for d in sample_chunks:
                if total_chars >= max_chars:
                    break
                piece = d.page_content[:400]
                sample_text_parts.append(piece)
                total_chars += len(piece)
            
            text_sample = "\n\n---\n\n".join(sample_text_parts)
            file_hash = ""
            if docs_for_file and docs_for_file[0].metadata.get("hash"):
                file_hash = docs_for_file[0].metadata["hash"]
            
            # Detectar tipo de documento y entidades clave usando LLM rápido
            doc_type, entities, topics = self._detect_document_type_and_entities(text_sample)
            
            gists.append(
                DocumentGist(
                    file_name=file_name,
                    file_hash=file_hash,
                    text_sample=text_sample,
                    chunk_count=len(docs_for_file),
                    size_mb=(meta.size_mb if meta else 0.0),
                    document_type=doc_type,
                    key_entities=entities,
                    key_topics=topics,
                )
            )
        
        return gists
    
    def _detect_document_type_and_entities(self, text_sample: str) -> Tuple[str, List[str], List[str]]:
        """Detecta tipo de documento, entidades y temas usando LLM rápido."""
        prompt = f"""Analiza rápidamente este fragmento de documento y extrae:

1. TIPO DE DOCUMENTO (uno de: contract, invoice, financial_statement, report, policy, manual, other)
2. ENTIDADES PRINCIPALES (empresas, personas, productos mencionados - máximo 5)
3. TEMAS PRINCIPALES (máximo 5)

FRAGMENTO:
{text_sample[:1500]}

Responde SOLO en JSON:
{{
    "document_type": "tipo",
    "entities": ["entidad1", "entidad2", ...],
    "topics": ["tema1", "tema2", ...]
}}"""
        
        try:
            response = self.fast_llm.invoke(prompt).content.strip()
            if response.startswith("```json"):
                response = response.replace("```json", "").replace("```", "").strip()
            elif response.startswith("```"):
                response = response.replace("```", "").strip()
            
            data = json.loads(response)
            return (
                data.get("document_type", "other"),
                data.get("entities", [])[:5],
                data.get("topics", [])[:5],
            )
        except Exception:
            return ("other", [], [])
    
    def _filter_gists_aggressive(self, gists: List[DocumentGist]) -> List[DocumentGist]:
        """
        Filtrado agresivo usando gists + LLM rápido (filtra 70-90% de documentos irrelevantes).
        """
        if not gists:
            return []
        
        # Construir prompt compacto
        items = []
        for i, gist in enumerate(gists, 1):
            snippet = gist.text_sample[:600].replace("\n", " ")
            items.append(f"{i}. {gist.file_name} [{gist.document_type}] :: {snippet}")
        
        joined = "\n\n".join(items)
        prompt = f"""Eres un sistema de filtrado agresivo para análisis empresarial.

Analiza estas "gists" (resúmenes breves) y selecciona SOLO los documentos
que son claramente relevantes para:
- Detectar riesgos, oportunidades y patrones de negocio
- Análisis comparativo entre documentos
- Extracción de datos estructurados (contratos, facturas, estados financieros)

Documentos:
{joined}

IMPORTANTE: Sé AGRESIVO. Filtra al menos 70-90% de documentos.
Solo mantén los que son claramente relevantes para análisis empresarial.

Devuelve SOLO JSON:
{{
  "relevant_indices": [1, 3, 5],
  "comment": "breve justificación"
}}"""
        
        try:
            raw = self.fast_llm.invoke(prompt).content.strip()
            if raw.startswith("```json"):
                raw = raw.replace("```json", "").replace("```", "").strip()
            elif raw.startswith("```"):
                raw = raw.replace("```", "").strip()
            
            data = json.loads(raw)
            indices = set(int(i) for i in data.get("relevant_indices", []))
        except Exception:
            # Fallback: considerar todos relevantes si hay error
            indices = set(range(1, len(gists) + 1))
        
        return [gists[i - 1] for i in sorted(indices) if 1 <= i <= len(gists)]
    
    def _extract_structured_data_parallel(
        self,
        chunks: List[Document],
        relevant_gists: List[DocumentGist],
    ) -> List[StructuredData]:
        """
        Extracción estructurada en paralelo (semantic ETL).
        Extrae campos específicos según tipo de documento (contratos, facturas, etc.).
        """
        from collections import defaultdict
        
        # Agrupar chunks por archivo
        docs_by_file: Dict[str, List[Document]] = defaultdict(list)
        for doc in chunks:
            src = doc.metadata.get("source") or doc.metadata.get("file_name") or "documento"
            docs_by_file[src].append(doc)
        
        relevant_names = {g.file_name for g in relevant_gists} if relevant_gists else set(docs_by_file.keys())
        
        def _extract_for_file(file_name: str, docs_for_file: List[Document], doc_type: str) -> StructuredData:
            # Construir contexto
            parts = []
            max_chars = 8000
            total_chars = 0
            for d in docs_for_file[:50]:
                if total_chars >= max_chars:
                    break
                piece = d.page_content[:400]
                parts.append(piece)
                total_chars += len(piece)
            context = "\n\n".join(parts)
            
            # Prompt especializado según tipo de documento
            if doc_type == "contract":
                prompt = self._get_contract_extraction_prompt(file_name, context)
            elif doc_type in ["invoice", "financial_statement", "balance_sheet"]:
                prompt = self._get_financial_extraction_prompt(file_name, context, doc_type)
            else:
                prompt = self._get_generic_extraction_prompt(file_name, context, doc_type)
            
            try:
                raw = self.fast_llm.invoke(prompt).content.strip()
                if raw.startswith("```json"):
                    raw = raw.replace("```json", "").replace("```", "").strip()
                elif raw.startswith("```"):
                    raw = raw.replace("```", "").strip()
                
                data = json.loads(raw)
                
                return StructuredData(
                    document_id=file_name,
                    document_type=doc_type,
                    extracted_fields=data.get("extracted_fields", {}),
                    entities=data.get("entities", []),
                    dates=data.get("dates", []),
                    amounts=data.get("amounts", []),
                    risk_flags=data.get("risk_flags", []),
                    opportunity_flags=data.get("opportunity_flags", []),
                )
            except Exception as e:
                # Fallback: datos básicos
                return StructuredData(
                    document_id=file_name,
                    document_type=doc_type,
                    extracted_fields={},
                    entities=[],
                    dates=[],
                    amounts=[],
                    risk_flags=[],
                    opportunity_flags=[],
                )
        
        # Ejecutar extracción en paralelo
        structured_data_list: List[StructuredData] = []
        max_workers = min(8, len(relevant_names) or 1)
        
        # Mapear tipos de documento desde gists
        doc_type_map = {g.file_name: g.document_type for g in relevant_gists}
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    _extract_for_file,
                    name,
                    docs_by_file.get(name, []),
                    doc_type_map.get(name, "other")
                ): name
                for name in relevant_names
                if docs_by_file.get(name)
            }
            
            for future in as_completed(futures):
                try:
                    sd = future.result()
                    structured_data_list.append(sd)
                except Exception as e:
                    print(f"⚠️ Error en extracción estructurada: {e}")
        
        return structured_data_list
    
    def _get_contract_extraction_prompt(self, file_name: str, context: str) -> str:
        """Prompt especializado para extracción de contratos."""
        return f"""Eres un especialista en extracción de datos de contratos.

DOCUMENTO: {file_name}

CONTENIDO:
{context[:6000]}

Extrae los siguientes campos estructurados del contrato:

1. PARTES: partes contratantes (cliente, proveedor, etc.)
2. FECHAS: fecha_inicio, fecha_fin, fecha_firma, fecha_vencimiento
3. MONTO: importe total, moneda, forma_pago
4. TÉRMINOS: plazo, condiciones, cláusulas clave
5. RENOVACIÓN: automática, manual, condiciones
6. ENTIDADES: empresas, personas, productos mencionados
7. RIESGOS: cláusulas de riesgo, penalizaciones, garantías
8. OPORTUNIDADES: beneficios, descuentos, términos favorables

Responde SOLO en JSON:
{{
    "extracted_fields": {{
        "parte_contratante": "...",
        "contraparte": "...",
        "fecha_inicio": "YYYY-MM-DD o texto",
        "fecha_fin": "YYYY-MM-DD o texto",
        "fecha_vencimiento": "YYYY-MM-DD o texto",
        "monto_total": número o null,
        "moneda": "USD/EUR/etc o null",
        "plazo": "texto",
        "renovacion_automatica": true/false/null,
        "clausulas_riesgo": ["cláusula1", ...],
        "garantias": ["garantía1", ...]
    }},
    "entities": [
        {{"type": "empresa|persona|producto", "name": "...", "value": "..."}}
    ],
    "dates": [
        {{"type": "inicio|fin|vencimiento|firma", "value": "...", "parsed": "YYYY-MM-DD o null"}}
    ],
    "amounts": [
        {{"type": "total|parcial|penalizacion", "value": número, "currency": "...", "description": "..."}}
    ],
    "risk_flags": ["riesgo1", "riesgo2", ...],
    "opportunity_flags": ["oportunidad1", ...]
}}"""
    
    def _get_financial_extraction_prompt(self, file_name: str, context: str, doc_type: str) -> str:
        """Prompt especializado para extracción de documentos financieros."""
        return f"""Eres un especialista en extracción de datos financieros.

DOCUMENTO: {file_name} (Tipo: {doc_type})

CONTENIDO:
{context[:6000]}

Extrae los siguientes campos estructurados:

1. CLIENTE: nombre del cliente/deudor
2. DEUDA: monto total, moneda, fecha_corte
3. PAGOS: historial de pagos, fechas, montos
4. VENCIMIENTOS: fechas de vencimiento, montos vencidos
5. ESTADO: estado actual (al día, moroso, etc.)
6. ENTIDADES: empresas, personas, productos
7. RIESGOS: deuda alta, morosidad, concentración
8. OPORTUNIDADES: descuentos, planes de pago, negociaciones

Responde SOLO en JSON:
{{
    "extracted_fields": {{
        "cliente": "...",
        "deuda_total": número o null,
        "moneda": "USD/EUR/etc o null",
        "fecha_corte": "YYYY-MM-DD o texto",
        "estado": "al_dia|moroso|vencido|...",
        "pagos_realizados": número o null,
        "monto_vencido": número o null
    }},
    "entities": [
        {{"type": "cliente|empresa|producto", "name": "...", "value": "..."}}
    ],
    "dates": [
        {{"type": "corte|vencimiento|pago", "value": "...", "parsed": "YYYY-MM-DD o null"}}
    ],
    "amounts": [
        {{"type": "deuda|pago|vencido", "value": número, "currency": "...", "description": "..."}}
    ],
    "risk_flags": ["riesgo1", ...],
    "opportunity_flags": ["oportunidad1", ...]
}}"""
    
    def _get_generic_extraction_prompt(self, file_name: str, context: str, doc_type: str) -> str:
        """Prompt genérico para otros tipos de documentos."""
        return f"""Eres un especialista en extracción de datos estructurados.

DOCUMENTO: {file_name} (Tipo: {doc_type})

CONTENIDO:
{context[:6000]}

Extrae datos estructurados relevantes:
- Entidades principales (empresas, personas, productos)
- Fechas importantes
- Montos/números relevantes
- Campos clave según el tipo de documento
- Riesgos y oportunidades identificados

Responde SOLO en JSON:
{{
    "extracted_fields": {{"campo1": "valor1", ...}},
    "entities": [
        {{"type": "tipo", "name": "...", "value": "..."}}
    ],
    "dates": [
        {{"type": "tipo", "value": "...", "parsed": "YYYY-MM-DD o null"}}
    ],
    "amounts": [
        {{"type": "tipo", "value": número, "currency": "...", "description": "..."}}
    ],
    "risk_flags": ["riesgo1", ...],
    "opportunity_flags": ["oportunidad1", ...]
}}"""
    
    def _generate_comparative_insights(
        self,
        comparative: ComparativeAnalysis,
        structured_data_list: List[StructuredData],
    ) -> str:
        """Genera insights comparativos mejorados usando datos estructurados."""
        insights = []
        
        # Insights de análisis comparativo básico
        if comparative.common_themes:
            insights.append(f"**Temas Comunes:** {', '.join(comparative.common_themes[:5])}")
        
        if comparative.contradictions:
            insights.append(f"**Contradicciones Detectadas:** {len(comparative.contradictions)}")
        
        # Insights de datos estructurados
        if structured_data_list:
            contracts = [sd for sd in structured_data_list if sd.document_type == "contract"]
            if contracts:
                # Análisis de contratos
                vencimientos = []
                for sd in contracts:
                    for date in sd.dates:
                        if date.get("type") in ["vencimiento", "fin"]:
                            vencimientos.append(date.get("parsed") or date.get("value"))
                
                if vencimientos:
                    insights.append(f"**Contratos con Vencimientos:** {len(vencimientos)} fechas identificadas")
                
                # Montos totales
                montos = []
                for sd in contracts:
                    for amount in sd.amounts:
                        if amount.get("type") == "total":
                            montos.append(amount.get("value", 0))
                
                if montos:
                    total = sum(m for m in montos if isinstance(m, (int, float)))
                    insights.append(f"**Monto Total en Contratos:** {total:,.2f}")
            
            # Análisis financiero
            financial = [sd for sd in structured_data_list if sd.document_type in ["invoice", "financial_statement"]]
            if financial:
                deudas = []
                for sd in financial:
                    for amount in sd.amounts:
                        if amount.get("type") == "deuda":
                            deudas.append(amount.get("value", 0))
                
                if deudas:
                    total_deuda = sum(d for d in deudas if isinstance(d, (int, float)))
                    insights.append(f"**Deuda Total Identificada:** {total_deuda:,.2f}")
        
        return "\n".join(f"- {insight}" for insight in insights) if insights else "No se identificaron insights comparativos específicos."
    
    def _synthesize_mdp_context_enhanced(
        self,
        chunks: List[Document],
        relevant_gists: List[DocumentGist],
        structured_data_list: List[StructuredData],
        comparative: Optional[ComparativeAnalysis],
    ) -> Tuple[str, str]:
        """
        Síntesis map-reduce mejorada que incluye datos estructurados.
        """
        # Construir representación compacta
        items = []
        for gist in relevant_gists:
            # Buscar datos estructurados correspondientes
            sd = next((s for s in structured_data_list if s.document_id == gist.file_name), None)
            
            item = {
                "file_name": gist.file_name,
                "document_type": gist.document_type,
                "key_entities": gist.key_entities,
                "key_topics": gist.key_topics,
            }
            
            if sd:
                item["structured_data"] = {
                    "extracted_fields": sd.extracted_fields,
                    "entities": sd.entities[:5],
                    "dates": sd.dates,
                    "amounts": sd.amounts,
                    "risk_flags": sd.risk_flags,
                    "opportunity_flags": sd.opportunity_flags,
                }
            
            items.append(item)
        
        mdp_context = json.dumps(
            {
                "documents": items,
                "comparative": (
                    {
                        "common_themes": comparative.common_themes,
                        "statistics": comparative.statistics,
                        "contradictions": comparative.contradictions[:5],
                    }
                    if comparative
                    else None
                ),
            },
            ensure_ascii=False,
        )
        
        # Resumen compacto
        prompt = f"""Genera un resumen ULTRA compacto (5-7 bullets) del contexto MDP mejorado.

CONTEXTO MDP (JSON):
{mdp_context[:4000]}

Resumen debe incluir:
- Número de documentos procesados
- Tipos principales de documentos
- Datos estructurados clave (contratos, deudas, etc.)
- Temas comunes y contradicciones

Devuelve SOLO texto en Markdown (sin JSON)."""
        
        try:
            summary = self.fast_llm.invoke(prompt).content.strip()
        except Exception:
            summary = "- Contexto MDP mejorado generado (no se pudo producir resumen breve)."
        
        return mdp_context, summary
    
    def _auto_detect_from_enhanced_context(
        self,
        mdp_context: str,
        structured_data_list: List[StructuredData],
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Detección automática mejorada usando datos estructurados."""
        # Construir contexto enriquecido
        structured_summary = []
        for sd in structured_data_list:
            if sd.risk_flags:
                structured_summary.append(f"Documento {sd.document_id}: Riesgos: {', '.join(sd.risk_flags[:3])}")
            if sd.opportunity_flags:
                structured_summary.append(f"Documento {sd.document_id}: Oportunidades: {', '.join(sd.opportunity_flags[:3])}")
        
        enhanced_context = mdp_context
        if structured_summary:
            enhanced_context += "\n\nDATOS ESTRUCTURADOS:\n" + "\n".join(structured_summary)
        
        prompt = f"""Eres un motor de detección automática de riesgos y oportunidades.

Analiza el CONTEXTO MDP mejorado (incluye datos estructurados) y detecta:
- problemas relevantes
- oportunidades de negocio
- patrones/transversalidades

Responde SOLO en JSON:
{{
  "problems": [
    {{
      "type": "tipo de problema",
      "severity": "alta|media|baja",
      "description": "...",
      "source": "documento o conjunto",
      "recommendation": "acción recomendada"
    }}
  ],
  "opportunities": [
    {{
      "type": "tipo de oportunidad",
      "impact": "alto|medio|bajo",
      "description": "...",
      "source": "documento o conjunto",
      "action": "acción sugerida"
    }}
  ],
  "patterns": [
    {{
      "type": "tipo de patrón",
      "description": "...",
      "frequency": "alta|media|baja",
      "implication": "qué implica"
    }}
  ]
}}

CONTEXTO MDP MEJORADO:
{enhanced_context[:8000]}"""
        
        try:
            raw = self.fast_llm.invoke(prompt).content.strip()
            if raw.startswith("```json"):
                raw = raw.replace("```json", "").replace("```", "").strip()
            elif raw.startswith("```"):
                raw = raw.replace("```", "").strip()
            return json.loads(raw)
        except Exception:
            return {"problems": [], "opportunities": [], "patterns": []}
    
    def _verify_with_ai(
        self,
        detection_results: Dict[str, Any],
        mdp_context: str,
    ) -> Dict[str, Any]:
        """
        Verificación de IA por IA: un segundo modelo verifica consistencia y reglas de negocio.
        """
        prompt = f"""Eres un verificador de IA. Tu tarea es verificar la consistencia y validez
de los resultados de detección automática.

RESULTADOS A VERIFICAR:
{json.dumps(detection_results, ensure_ascii=False, indent=2)}

CONTEXTO MDP:
{mdp_context[:4000]}

Verifica:
1. ¿Los problemas detectados son consistentes con el contexto?
2. ¿Hay contradicciones entre problemas y oportunidades?
3. ¿Los niveles de severidad/impacto son apropiados?
4. ¿Faltan problemas u oportunidades obvias?

Responde SOLO en JSON:
{{
    "verified": true/false,
    "confidence": "alta|media|baja",
    "inconsistencies": ["inconsistencia1", ...],
    "missing_items": ["item que falta", ...],
    "recommendations": ["recomendación1", ...]
}}"""
        
        try:
            raw = self.verifier_llm.invoke(prompt).content.strip()
            if raw.startswith("```json"):
                raw = raw.replace("```json", "").replace("```", "").strip()
            elif raw.startswith("```"):
                raw = raw.replace("```", "").strip()
            return json.loads(raw)
        except Exception:
            return {
                "verified": False,
                "confidence": "baja",
                "inconsistencies": [],
                "missing_items": [],
                "recommendations": [],
            }
    
    def _generate_executive_report_enhanced(
        self,
        mdp_context: str,
        detection_results: Dict[str, Any],
        verification_results: Dict[str, Any],
        structured_data_list: List[StructuredData],
        comparative: Optional[ComparativeAnalysis],
    ) -> str:
        """Informe ejecutivo mejorado tipo consultor C-level."""
        # Construir resumen de datos estructurados
        structured_summary = []
        if structured_data_list:
            contracts = [sd for sd in structured_data_list if sd.document_type == "contract"]
            financial = [sd for sd in structured_data_list if sd.document_type in ["invoice", "financial_statement"]]
            
            if contracts:
                structured_summary.append(f"- **Contratos procesados:** {len(contracts)}")
                # Contar vencimientos próximos
                vencimientos_proximos = 0
                for sd in contracts:
                    for date in sd.dates:
                        if date.get("type") in ["vencimiento", "fin"]:
                            # Lógica simple: si tiene fecha, contar
                            vencimientos_proximos += 1
                            break
                if vencimientos_proximos > 0:
                    structured_summary.append(f"- **Contratos con vencimientos identificados:** {vencimientos_proximos}")
            
            if financial:
                structured_summary.append(f"- **Documentos financieros procesados:** {len(financial)}")
                # Calcular deuda total
                total_deuda = 0
                for sd in financial:
                    for amount in sd.amounts:
                        if amount.get("type") == "deuda" and isinstance(amount.get("value"), (int, float)):
                            total_deuda += amount.get("value", 0)
                if total_deuda > 0:
                    structured_summary.append(f"- **Deuda total identificada:** ${total_deuda:,.2f}")
        
        structured_text = "\n".join(structured_summary) if structured_summary else "No se extrajeron datos estructurados específicos."
        
        prompt = f"""Actúa como consultor senior para empresas (nivel board/C-level).

Se te entrega:
- Un CONTEXTO MDP mejorado (JSON) con evidencias y análisis comparativo
- Resultados de detección automática de problemas y oportunidades
- Resultados de verificación de IA por IA
- Resumen de datos estructurados extraídos

Tu tarea:
- Redactar un INFORME EJECUTIVO profesional en español para CEO/C-level
- Estructura sugerida:
  1. Resumen ejecutivo (2-3 párrafos)
  2. Datos estructurados clave (contratos, deudas, etc.)
  3. Principales riesgos y problemas (bullets con severidad)
  4. Principales oportunidades (bullets con impacto)
  5. Patrones y aprendizajes transversales
  6. Recomendaciones accionables en 30/60/90 días
  7. Nota sobre verificación de IA (si hay inconsistencias)

CONTEXTO MDP:
{mdp_context[:6000]}

DETECCIONES:
{json.dumps(detection_results, ensure_ascii=False, indent=2)}

VERIFICACIÓN:
{json.dumps(verification_results, ensure_ascii=False, indent=2)}

DATOS ESTRUCTURADOS:
{structured_text}
"""
        
        try:
            report = self.reasoning_llm.invoke(prompt).content.strip()
        except Exception as e:
            report = f"⚠️ No se pudo generar informe ejecutivo completo. Error: {str(e)}"
        
        return report
    
    def _save_to_memory_enhanced(
        self,
        mdp_context: str,
        detection_results: Dict[str, Any],
        structured_data_list: List[StructuredData],
    ) -> None:
        """Guarda contexto MDP mejorado y datos estructurados en memoria persistente."""
        if not self.context_manager:
            return
        
        # Guardar snapshot del contexto MDP
        self.context_manager.add_query(
            query="Snapshot contexto MDP Enterprise API Supreme",
            answer=mdp_context[:8000],
            sources=[],
            metadata={"type": "mdp_snapshot_supreme"},
        )
        
        # Guardar datos estructurados como memorias discretas
        for sd in structured_data_list:
            self.context_manager.add_query(
                query=f"Datos estructurados: {sd.document_id}",
                answer=json.dumps(sd.extracted_fields, ensure_ascii=False),
                sources=[sd.document_id],
                metadata={
                    "type": "structured_data",
                    "document_type": sd.document_type,
                    "entities": sd.entities[:5],
                },
            )
        
        # Guardar problemas y oportunidades
        for problem in detection_results.get("problems", []):
            self.context_manager.add_query(
                query=f"Problema Supreme: {problem.get('type', 'desconocido')}",
                answer=problem.get("description", ""),
                sources=[problem.get("source", "")] if problem.get("source") else [],
                metadata={
                    "type": "supreme_detection",
                    "detection_type": "problem",
                    "severity": problem.get("severity", "media"),
                },
            )
        
        for opp in detection_results.get("opportunities", []):
            self.context_manager.add_query(
                query=f"Oportunidad Supreme: {opp.get('type', 'desconocido')}",
                answer=opp.get("description", ""),
                sources=[opp.get("source", "")] if opp.get("source") else [],
                metadata={
                    "type": "supreme_detection",
                    "detection_type": "opportunity",
                    "impact": opp.get("impact", "medio"),
                },
            )
    
    def _generate_per_document_analysis(
        self,
        relevant_gists: List[DocumentGist],
        structured_data_list: List[StructuredData],
        chunks: List[Document],
    ) -> str:
        """
        Genera análisis individual por cada documento procesado.
        Esto responde a la pregunta: "¿Una sola pregunta puede devolver respuesta de cada PDF?"
        """
        from collections import defaultdict
        
        # Agrupar chunks por archivo
        docs_by_file: Dict[str, List[Document]] = defaultdict(list)
        for doc in chunks:
            src = doc.metadata.get("source") or doc.metadata.get("file_name") or "documento"
            docs_by_file[src].append(doc)
        
        analysis_parts = []
        analysis_parts.append("**Análisis Individual por Documento:**\n\n")
        
        for gist in relevant_gists:
            file_name = Path(gist.file_name).name
            analysis_parts.append(f"#### 📄 {file_name}\n\n")
            
            # Información básica del documento
            analysis_parts.append(f"- **Tipo de Documento**: {gist.document_type}\n")
            analysis_parts.append(f"- **Chunks**: {gist.chunk_count}\n")
            analysis_parts.append(f"- **Tamaño**: {gist.size_mb:.2f} MB\n")
            
            # Entidades y temas
            if gist.key_entities:
                analysis_parts.append(f"- **Entidades Principales**: {', '.join(gist.key_entities[:5])}\n")
            if gist.key_topics:
                analysis_parts.append(f"- **Temas**: {', '.join(gist.key_topics[:5])}\n")
            
            # Datos estructurados si están disponibles
            sd = next((s for s in structured_data_list if s.document_id == gist.file_name), None)
            if sd:
                analysis_parts.append(f"\n**📊 Datos Estructurados Extraídos:**\n")
                
                # Mostrar campos extraídos según tipo
                if sd.document_type == "contract":
                    if sd.extracted_fields.get("parte_contratante"):
                        analysis_parts.append(f"- **Parte Contratante**: {sd.extracted_fields.get('parte_contratante')}\n")
                    if sd.extracted_fields.get("contraparte"):
                        analysis_parts.append(f"- **Contraparte**: {sd.extracted_fields.get('contraparte')}\n")
                    if sd.extracted_fields.get("fecha_vencimiento"):
                        analysis_parts.append(f"- **Fecha Vencimiento**: {sd.extracted_fields.get('fecha_vencimiento')}\n")
                    if sd.extracted_fields.get("monto_total"):
                        analysis_parts.append(f"- **Monto Total**: {sd.extracted_fields.get('monto_total')} {sd.extracted_fields.get('moneda', '')}\n")
                    if sd.risk_flags:
                        analysis_parts.append(f"- **⚠️ Riesgos**: {', '.join(sd.risk_flags[:3])}\n")
                    if sd.opportunity_flags:
                        analysis_parts.append(f"- **💡 Oportunidades**: {', '.join(sd.opportunity_flags[:3])}\n")
                
                elif sd.document_type in ["invoice", "financial_statement"]:
                    if sd.extracted_fields.get("cliente"):
                        analysis_parts.append(f"- **Cliente**: {sd.extracted_fields.get('cliente')}\n")
                    if sd.extracted_fields.get("deuda_total"):
                        analysis_parts.append(f"- **Deuda Total**: {sd.extracted_fields.get('deuda_total')} {sd.extracted_fields.get('moneda', '')}\n")
                    if sd.extracted_fields.get("estado"):
                        analysis_parts.append(f"- **Estado**: {sd.extracted_fields.get('estado')}\n")
                    if sd.extracted_fields.get("fecha_corte"):
                        analysis_parts.append(f"- **Fecha Corte**: {sd.extracted_fields.get('fecha_corte')}\n")
                    if sd.risk_flags:
                        analysis_parts.append(f"- **⚠️ Riesgos**: {', '.join(sd.risk_flags[:3])}\n")
                    if sd.opportunity_flags:
                        analysis_parts.append(f"- **💡 Oportunidades**: {', '.join(sd.opportunity_flags[:3])}\n")
                
                else:
                    # Tipo genérico
                    if sd.extracted_fields:
                        for key, value in list(sd.extracted_fields.items())[:5]:
                            analysis_parts.append(f"- **{key.replace('_', ' ').title()}**: {value}\n")
            
            # Resumen completo del contenido
            file_docs = docs_by_file.get(gist.file_name, [])
            if file_docs:
                # Generar resumen completo usando LLM rápido
                # Usar más chunks para mejor contexto (hasta 5 chunks o 3000 caracteres)
                sample_chunks = []
                total_chars = 0
                for doc in file_docs[:5]:
                    if total_chars < 3000:
                        chunk_text = doc.page_content[:1000]
                        sample_chunks.append(chunk_text)
                        total_chars += len(chunk_text)
                    else:
                        break
                sample_text = "\n\n".join(sample_chunks)
                brief_summary = self._generate_brief_document_summary(file_name, sample_text, gist.document_type)
                if brief_summary:
                    analysis_parts.append(f"\n**📝 Resumen Ejecutivo Completo:**\n\n{brief_summary}\n")
            
            analysis_parts.append("\n---\n\n")
        
        return "".join(analysis_parts)
    
    def _generate_brief_document_summary(
        self,
        file_name: str,
        sample_text: str,
        document_type: str,
    ) -> str:
        """Genera un resumen ejecutivo completo de un documento usando LLM rápido."""
        prompt = f"""Genera un resumen ejecutivo COMPLETO y detallado (mínimo 3-5 párrafos, máximo 8 párrafos) del siguiente documento.

DOCUMENTO: {file_name}
TIPO: {document_type}

CONTENIDO (muestra):
{sample_text[:3000]}

INSTRUCCIONES PARA EL RESUMEN:
1. Propósito principal del documento (1 párrafo)
2. Información clave extraída con detalles específicos (nombres, fechas, montos, entidades importantes) - 1-2 párrafos
3. Hallazgos principales y datos relevantes - 1-2 párrafos
4. Relevancia para análisis empresarial - 1 párrafo
5. Conclusiones o recomendaciones si las hay - 1 párrafo

REQUISITOS CRÍTICOS:
- DEBES completar TODOS los párrafos completamente
- NO cortes frases a la mitad
- NO uses puntos suspensivos (...)
- Incluye información concreta (números exactos, nombres completos, fechas específicas)
- Sé específico y detallado, evita frases genéricas
- El resumen debe tener un final claro y completo

IMPORTANTE: Genera el resumen COMPLETO sin truncar. Si el documento tiene información limitada, explica claramente qué información está disponible.

Responde SOLO en texto plano (sin JSON, sin markdown especial, sin formato)."""
        
        try:
            # Usar summary_llm que tiene más tokens disponibles
            summary = self.summary_llm.invoke(prompt).content.strip()
            # No truncar - mostrar resumen completo (el LLM ya está limitado por max_tokens)
            # Solo limpiar espacios en blanco excesivos
            summary = "\n".join([line.strip() for line in summary.split("\n") if line.strip()])
            return summary
        except Exception as e:
            # Fallback a fast_llm si summary_llm falla
            try:
                summary = self.fast_llm.invoke(prompt).content.strip()
                summary = "\n".join([line.strip() for line in summary.split("\n") if line.strip()])
                return summary
            except Exception as e2:
                return f"⚠️ No se pudo generar resumen ejecutivo: {str(e2)[:100]}"
    
    # ============================================================
    # MÉTODO PARA CONSULTAS NL2SQL/NL2Query (Futuro)
    # ============================================================
    
    def query_structured_data(self, natural_language_query: str) -> Dict[str, Any]:
        """
        Convierte consultas en lenguaje natural a consultas sobre datos estructurados.
        
        Ejemplos:
        - "¿Cuáles son los contratos que vencen en febrero?"
        - "Listame todos los clientes con deuda > USD 10.000"
        """
        # Construir índice de datos estructurados
        contracts = [sd for sd in self.structured_data_store.values() if sd.document_type == "contract"]
        financial = [sd for sd in self.structured_data_store.values() if sd.document_type in ["invoice", "financial_statement"]]
        
        # Prompt para convertir NL a consulta estructurada
        prompt = f"""Eres un sistema NL2Query. Convierte la pregunta del usuario en una consulta
sobre los datos estructurados disponibles.

PREGUNTA DEL USUARIO:
{natural_language_query}

DATOS ESTRUCTURADOS DISPONIBLES:
- Contratos: {len(contracts)} documentos
- Documentos financieros: {len(financial)} documentos

Para cada tipo de documento, los campos disponibles son:
- Contratos: parte_contratante, contraparte, fecha_inicio, fecha_fin, fecha_vencimiento, monto_total, moneda, renovacion_automatica
- Financieros: cliente, deuda_total, moneda, fecha_corte, estado, monto_vencido

Tu tarea:
1. Identificar qué tipo de consulta es (filtrado por fecha, monto, entidad, etc.)
2. Generar una "consulta estructurada" en formato JSON que pueda ejecutarse sobre los datos

Responde SOLO en JSON:
{{
    "query_type": "contracts|financial|both",
    "filters": {{
        "field": "nombre_campo",
        "operator": "equals|greater_than|less_than|contains|in",
        "value": "valor o lista"
    }},
    "description": "descripción de lo que la consulta busca"
}}"""
        
        try:
            raw = self.fast_llm.invoke(prompt).content.strip()
            if raw.startswith("```json"):
                raw = raw.replace("```json", "").replace("```", "").strip()
            elif raw.startswith("```"):
                raw = raw.replace("```", "").strip()
            
            query_spec = json.loads(raw)
            
            # Ejecutar consulta sobre datos estructurados
            results = self._execute_structured_query(query_spec, contracts, financial)
            
            return {
                "query": natural_language_query,
                "query_spec": query_spec,
                "results": results,
                "total_matches": len(results),
            }
        except Exception as e:
            return {
                "query": natural_language_query,
                "error": str(e),
                "results": [],
                "total_matches": 0,
            }
    
    def _execute_structured_query(
        self,
        query_spec: Dict[str, Any],
        contracts: List[StructuredData],
        financial: List[StructuredData],
    ) -> List[Dict[str, Any]]:
        """Ejecuta una consulta estructurada sobre los datos."""
        results = []
        query_type = query_spec.get("query_type", "both")
        filters = query_spec.get("filters", {})
        
        # Aplicar filtros según tipo
        if query_type in ["contracts", "both"]:
            for contract in contracts:
                if self._matches_filters(contract, filters):
                    results.append({
                        "document_id": contract.document_id,
                        "document_type": "contract",
                        "data": contract.extracted_fields,
                    })
        
        if query_type in ["financial", "both"]:
            for fin in financial:
                if self._matches_filters(fin, filters):
                    results.append({
                        "document_id": fin.document_id,
                        "document_type": fin.document_type,
                        "data": fin.extracted_fields,
                    })
        
        return results
    
    def _matches_filters(self, structured_data: StructuredData, filters: Dict[str, Any]) -> bool:
        """Verifica si un documento estructurado coincide con los filtros."""
        if not filters:
            return True
        
        field = filters.get("field")
        operator = filters.get("operator", "equals")
        value = filters.get("value")
        
        if not field or value is None:
            return True
        
        # Obtener valor del campo
        doc_value = structured_data.extracted_fields.get(field)
        if doc_value is None:
            return False
        
        # Aplicar operador
        if operator == "equals":
            return str(doc_value).lower() == str(value).lower()
        elif operator == "contains":
            return str(value).lower() in str(doc_value).lower()
        elif operator == "greater_than":
            try:
                return float(doc_value) > float(value)
            except:
                return False
        elif operator == "less_than":
            try:
                return float(doc_value) < float(value)
            except:
                return False
        elif operator == "in":
            if isinstance(value, list):
                return str(doc_value).lower() in [str(v).lower() for v in value]
            return False
        
        return True
    
    # ============================================================
    # SISTEMA DE CONSULTAS ESTRATÉGICAS ENTERPRISE (NL2Query Avanzado)
    # ============================================================
    
    def _load_query_history(self) -> List[Dict[str, Any]]:
        """Carga el historial de consultas empresariales."""
        if self.query_history_file.exists():
            try:
                with open(self.query_history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return []
        return []
    
    def _save_query_history(self):
        """Guarda el historial de consultas."""
        try:
            self.query_history_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.query_history_file, 'w', encoding='utf-8') as f:
                json.dump(self.query_history[-100:], f, indent=2, ensure_ascii=False)  # Mantener últimas 100
        except Exception as e:
            pass
    
    def get_strategic_questions(self) -> List[Dict[str, str]]:
        """Retorna lista de preguntas estratégicas pre-compiladas."""
        return [
            {
                "id": "risk_financial_critical",
                "text": "🎯 Riesgos financieros críticos",
                "query": "¿Cuáles son los riesgos financieros críticos? Facturas vencidas, deudas pendientes, montos en riesgo.",
                "category": "financiero"
            },
            {
                "id": "opportunities_strategic",
                "text": "🚀 Oportunidades estratégicas",
                "query": "¿Qué oportunidades estratégicas se detectan? Optimizaciones, mejoras, ventajas competitivas.",
                "category": "estrategico"
            },
            {
                "id": "contracts_due_soon",
                "text": "📅 Contratos próximos a vencer",
                "query": "¿Qué contratos vencen en los próximos 30/60/90 días? Incluye fechas exactas, partes y montos.",
                "category": "legal"
            },
            {
                "id": "clients_high_debt",
                "text": "💰 Clientes con deuda alta",
                "query": "Listame todos los clientes con deuda mayor a USD 10,000. Incluye montos, fechas y estado.",
                "category": "financiero"
            },
            {
                "id": "contracts_february",
                "text": "📆 Contratos que vencen en febrero",
                "query": "¿Cuáles son los contratos que vencen en febrero? Incluye año si está disponible.",
                "category": "legal"
            },
            {
                "id": "custom_query",
                "text": "🔍 Consulta personalizada (NL2Query)",
                "query": "",
                "category": "custom"
            }
        ]
    
    def execute_strategic_query(
        self,
        query_id: Optional[str] = None,
        custom_query: Optional[str] = None,
        structured_data_list: Optional[List[StructuredData]] = None,
        detection_results: Optional[Dict[str, Any]] = None,
        relevant_gists: Optional[List[DocumentGist]] = None,
        chunks: Optional[List[Document]] = None,
    ) -> Dict[str, Any]:
        """
        Ejecuta una consulta estratégica enterprise.
        NO es chat conversacional, es traducción de pregunta empresarial a consulta estructurada.
        Si no hay datos estructurados suficientes, usa RAG sobre los documentos.
        """
        # Determinar la pregunta
        if query_id and query_id != "custom_query":
            strategic_questions = self.get_strategic_questions()
            question_obj = next((q for q in strategic_questions if q["id"] == query_id), None)
            if question_obj:
                natural_query = question_obj["query"]
            else:
                natural_query = custom_query or ""
        else:
            natural_query = custom_query or ""
        
        if not natural_query:
            return {
                "error": "No se proporcionó consulta",
                "results": [],
                "query_spec": None
            }
        
        # Cargar datos estructurados persistentes si no se proporcionaron
        if not structured_data_list:
            structured_data_list = self._load_structured_data()
            # También cargar desde store interno
            if not structured_data_list:
                structured_data_list = list(self.structured_data_store.values())
        
        # Cargar gists si no se proporcionaron
        if not relevant_gists:
            relevant_gists = self._load_gists_from_memory()
        
        # Si hay datos estructurados, usar NL2Query
        if structured_data_list and len(structured_data_list) > 0:
            # Ejecutar NL2Query avanzado
            query_result = self.query_structured_data_advanced(
                natural_query,
                structured_data_list,
                detection_results,
                relevant_gists
            )
        else:
            # Fallback: usar RAG sobre los documentos procesados
            query_result = self._query_with_rag(
                natural_query,
                chunks,
                relevant_gists
            )
        
        # Guardar en historial
        query_record = {
            "timestamp": datetime.now().isoformat(),
            "query": natural_query,
            "query_id": query_id,
            "total_matches": query_result.get("total_matches", 0),
            "category": next((q["category"] for q in self.get_strategic_questions() if q["id"] == query_id), "custom") if query_id else "custom"
        }
        self.query_history.append(query_record)
        self._save_query_history()
        
        return query_result
    
    def query_structured_data_advanced(
        self,
        natural_language_query: str,
        structured_data_list: List[StructuredData],
        detection_results: Optional[Dict[str, Any]] = None,
        relevant_gists: Optional[List[DocumentGist]] = None,
    ) -> Dict[str, Any]:
        """
        NL2Query AVANZADO: Traduce pregunta empresarial a consulta estructurada.
        NO es chat, es traducción precisa de intención a filtros sobre datos estructurados.
        """
        # Agrupar datos por tipo
        contracts = [sd for sd in structured_data_list if sd.document_type == "contract"]
        invoices = [sd for sd in structured_data_list if sd.document_type == "invoice"]
        financial = [sd for sd in structured_data_list if sd.document_type in ["invoice", "financial_statement"]]
        
        # Construir esquema de datos disponible
        schema_info = []
        if contracts:
            schema_info.append(f"- Contratos ({len(contracts)}): parte_contratante, contraparte, fecha_inicio, fecha_fin, fecha_vencimiento, monto_total, moneda, renovacion_automatica, clausulas_criticas")
        if invoices:
            schema_info.append(f"- Facturas ({len(invoices)}): cliente, proveedor, numero_factura, monto_total, moneda, fecha_emision, fecha_vencimiento, estado, monto_vencido, monto_pendiente")
        if financial:
            schema_info.append(f"- Financieros ({len(financial)}): cliente, deuda_total, moneda, fecha_corte, estado, monto_vencido, monto_pagado")
        
        # Prompt mejorado para NL2Query
        prompt = f"""Eres un sistema NL2Query Enterprise. Tu tarea es traducir preguntas empresariales a consultas estructuradas precisas.

PREGUNTA DEL USUARIO:
{natural_language_query}

ESQUEMA DE DATOS DISPONIBLES:
{chr(10).join(schema_info)}

INSTRUCCIONES:
1. Analiza la intención de la pregunta (filtrado por fecha, monto, entidad, estado, etc.)
2. Identifica qué tipo(s) de documentos son relevantes (contracts, invoices, financial)
3. Genera filtros precisos en formato JSON
4. Para fechas: extrae mes, año, rango según corresponda
5. Para montos: normaliza a USD si es necesario, usa operadores >, <, >=, <=
6. Para estados: identifica valores como "vencido", "pendiente", "pagado", etc.

Responde SOLO en JSON válido:
{{
    "query_type": "contracts|invoices|financial|all",
    "intent": "descripción clara de lo que busca la consulta",
    "filters": [
        {{
            "field": "nombre_campo",
            "operator": "equals|greater_than|less_than|greater_equal|less_equal|contains|in|date_range|month_equals",
            "value": "valor o lista de valores",
            "normalize_currency": true|false
        }}
    ],
    "aggregations": ["count|sum|avg|max|min"],
    "group_by": ["campo para agrupar resultados"]
}}"""
        
        try:
            raw = self.reasoning_llm.invoke(prompt).content.strip()
            # Limpiar JSON
            if raw.startswith("```json"):
                raw = raw.replace("```json", "").replace("```", "").strip()
            elif raw.startswith("```"):
                raw = raw.replace("```", "").strip()
            
            query_spec = json.loads(raw)
            
            # Ejecutar consulta avanzada
            results = self._execute_advanced_query(
                query_spec, 
                contracts, 
                invoices, 
                financial,
                detection_results,
                relevant_gists
            )
            
            # Generar respuesta ejecutiva
            executive_response = self._generate_executive_query_response(
                natural_language_query,
                query_spec,
                results,
                detection_results
            )
            
            return {
                "query": natural_language_query,
                "query_spec": query_spec,
                "results": results,
                "total_matches": len(results),
                "executive_response": executive_response,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "query": natural_language_query,
                "error": str(e),
                "results": [],
                "total_matches": 0,
                "executive_response": f"⚠️ Error al procesar consulta: {str(e)}"
            }
    
    def _execute_advanced_query(
        self,
        query_spec: Dict[str, Any],
        contracts: List[StructuredData],
        invoices: List[StructuredData],
        financial: List[StructuredData],
        detection_results: Optional[Dict[str, Any]] = None,
        relevant_gists: Optional[List[DocumentGist]] = None,
    ) -> List[Dict[str, Any]]:
        """Ejecuta consulta avanzada con múltiples filtros y agregaciones."""
        results = []
        query_type = query_spec.get("query_type", "all")
        filters = query_spec.get("filters", [])
        
        # Procesar según tipo
        data_sources = []
        if query_type in ["contracts", "all"]:
            data_sources.extend([("contract", c) for c in contracts])
        if query_type in ["invoices", "all"]:
            data_sources.extend([("invoice", i) for i in invoices])
        if query_type in ["financial", "all"]:
            data_sources.extend([("financial", f) for f in financial])
        
        # Aplicar filtros
        for doc_type, sd in data_sources:
            if self._matches_advanced_filters(sd, filters):
                result_item = {
                    "document_id": sd.document_id,
                    "document_type": doc_type,
                    "data": sd.extracted_fields.copy(),
                    "entities": [e.copy() for e in sd.entities] if sd.entities else [],
                    "dates": [d.copy() for d in sd.dates] if sd.dates else [],
                    "amounts": [a.copy() for a in sd.amounts] if sd.amounts else [],
                }
                
                # Enriquecer con información de gist si está disponible
                if relevant_gists:
                    gist = next((g for g in relevant_gists if g.file_name == sd.document_id), None)
                    if gist:
                        result_item["file_name"] = Path(gist.file_name).name
                        result_item["summary"] = gist.text_sample[:500] if gist.text_sample else ""
                
                results.append(result_item)
        
        # Aplicar agregaciones si se solicitan
        aggregations = query_spec.get("aggregations", [])
        group_by = query_spec.get("group_by", [])
        
        if aggregations or group_by:
            results = self._apply_aggregations(results, aggregations, group_by)
        
        return results
    
    def _matches_advanced_filters(self, structured_data: StructuredData, filters: List[Dict[str, Any]]) -> bool:
        """Verifica si un documento coincide con múltiples filtros avanzados."""
        if not filters:
            return True
        
        for filter_item in filters:
            field = filter_item.get("field")
            operator = filter_item.get("operator", "equals")
            value = filter_item.get("value")
            normalize_currency = filter_item.get("normalize_currency", False)
            
            if not field or value is None:
                continue
            
            # Buscar valor en extracted_fields, entities, dates, amounts
            doc_value = None
            
            # 1. Buscar en extracted_fields
            doc_value = structured_data.extracted_fields.get(field)
            
            # 2. Si no está, buscar en entities
            if doc_value is None and structured_data.entities:
                for entity in structured_data.entities:
                    if entity.get("type") == field or entity.get("name") == field:
                        doc_value = entity.get("value")
                        break
            
            # 3. Si no está, buscar en dates
            if doc_value is None and structured_data.dates:
                for date in structured_data.dates:
                    if date.get("type") == field:
                        doc_value = date.get("value") or date.get("parsed")
                        break
            
            # 4. Si no está, buscar en amounts
            if doc_value is None and structured_data.amounts:
                for amount in structured_data.amounts:
                    if amount.get("type") == field:
                        doc_value = amount.get("value")
                        break
            
            if doc_value is None:
                return False
            
            # Aplicar operador
            if not self._apply_advanced_operator(doc_value, operator, value, normalize_currency):
                return False
        
        return True
    
    def _apply_advanced_operator(self, doc_value: Any, operator: str, value: Any, normalize_currency: bool = False) -> bool:
        """Aplica un operador de filtro avanzado."""
        try:
            # Normalizar moneda si es necesario
            if normalize_currency and isinstance(doc_value, (int, float)):
                # Asumir que está en USD o convertir según lógica
                pass
            
            if operator == "equals":
                return str(doc_value).lower() == str(value).lower()
            elif operator == "contains":
                return str(value).lower() in str(doc_value).lower()
            elif operator == "greater_than":
                return float(doc_value) > float(value)
            elif operator == "less_than":
                return float(doc_value) < float(value)
            elif operator == "greater_equal":
                return float(doc_value) >= float(value)
            elif operator == "less_equal":
                return float(doc_value) <= float(value)
            elif operator == "in":
                if isinstance(value, list):
                    return str(doc_value).lower() in [str(v).lower() for v in value]
                return False
            elif operator == "month_equals":
                # Para fechas: comparar mes
                from datetime import datetime
                try:
                    if isinstance(doc_value, str):
                        # Intentar parsear fecha
                        date_obj = datetime.strptime(doc_value, "%Y-%m-%d")
                        month_value = int(value) if isinstance(value, (int, str)) else value
                        return date_obj.month == month_value
                except:
                    # Buscar mes en string
                    month_names = ["enero", "febrero", "marzo", "abril", "mayo", "junio",
                                 "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
                    month_value_str = str(value).lower()
                    if month_value_str in month_names:
                        month_num = month_names.index(month_value_str) + 1
                        return str(month_num) in str(doc_value) or month_value_str in str(doc_value).lower()
                    return str(value) in str(doc_value)
            elif operator == "date_range":
                # Rango de fechas
                if isinstance(value, dict) and "start" in value and "end" in value:
                    from datetime import datetime
                    try:
                        doc_date = datetime.strptime(str(doc_value), "%Y-%m-%d")
                        start_date = datetime.strptime(value["start"], "%Y-%m-%d")
                        end_date = datetime.strptime(value["end"], "%Y-%m-%d")
                        return start_date <= doc_date <= end_date
                    except:
                        return False
        except Exception:
            return False
        
        return True
    
    def _apply_aggregations(self, results: List[Dict[str, Any]], aggregations: List[str], group_by: List[str]) -> List[Dict[str, Any]]:
        """Aplica agregaciones a los resultados."""
        # Implementación básica de agregaciones
        if not aggregations:
            return results
        
        aggregated = {}
        for result in results:
            # Crear clave de agrupación
            group_key = "_".join([str(result.get("data", {}).get(gb, "")) for gb in group_by]) if group_by else "all"
            
            if group_key not in aggregated:
                aggregated[group_key] = {
                    "group": {gb: result.get("data", {}).get(gb) for gb in group_by} if group_by else {},
                    "count": 0,
                    "items": []
                }
            
            aggregated[group_key]["count"] += 1
            aggregated[group_key]["items"].append(result)
        
        # Aplicar agregaciones numéricas
        for group_key, group_data in aggregated.items():
            items = group_data["items"]
            for agg in aggregations:
                if agg == "sum":
                    # Sumar montos
                    total = sum(
                        float(item.get("data", {}).get("monto_total", 0) or 
                             item.get("data", {}).get("deuda_total", 0) or 0)
                        for item in items
                    )
                    aggregated[group_key]["sum"] = total
                elif agg == "avg":
                    # Promedio
                    values = [
                        float(item.get("data", {}).get("monto_total", 0) or 
                             item.get("data", {}).get("deuda_total", 0) or 0)
                        for item in items
                    ]
                    if values:
                        aggregated[group_key]["avg"] = sum(values) / len(values)
                elif agg == "max":
                    values = [
                        float(item.get("data", {}).get("monto_total", 0) or 
                             item.get("data", {}).get("deuda_total", 0) or 0)
                        for item in items
                    ]
                    if values:
                        aggregated[group_key]["max"] = max(values)
                elif agg == "min":
                    values = [
                        float(item.get("data", {}).get("monto_total", 0) or 
                             item.get("data", {}).get("deuda_total", 0) or 0)
                        for item in items
                    ]
                    if values:
                        aggregated[group_key]["min"] = min(values)
        
        return list(aggregated.values())
    
    def _generate_executive_query_response(
        self,
        original_query: str,
        query_spec: Dict[str, Any],
        results: List[Dict[str, Any]],
        detection_results: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Genera respuesta ejecutiva accionable y cuantificada (NO conversacional)."""
        response_parts = []
        
        response_parts.append(f"## 📊 RESPUESTA ESTRATÉGICA ENTERPRISE\n\n")
        response_parts.append(f"**Consulta:** {original_query}\n\n")
        
        if not results:
            response_parts.append("⚠️ **No se encontraron resultados que coincidan con los criterios especificados.**\n")
            return "".join(response_parts)
        
        # Resumen ejecutivo
        response_parts.append(f"✅ **Resultados encontrados:** {len(results)}\n\n")
        
        # Si hay agregaciones, mostrar resumen
        if isinstance(results[0], dict) and "group" in results[0]:
            response_parts.append("### 📈 Resumen Agregado\n\n")
            for group_result in results[:10]:  # Top 10
                group_info = group_result.get("group", {})
                count = group_result.get("count", 0)
                response_parts.append(f"- **{', '.join(f'{k}: {v}' for k, v in group_info.items())}**: {count} documentos")
                if "sum" in group_result:
                    response_parts.append(f" (Total: ${group_result['sum']:,.2f})")
                response_parts.append("\n")
        else:
            # Tabla de resultados
            response_parts.append("### 📋 Resultados Detallados\n\n")
            response_parts.append("| Documento | Tipo | Información Clave |\n")
            response_parts.append("|-----------|------|-------------------|\n")
            
            for result in results[:20]:  # Top 20
                doc_id = result.get("document_id", "N/A")
                doc_name = result.get("file_name", Path(doc_id).name if doc_id != "N/A" else "N/A")
                doc_type = result.get("document_type", "N/A")
                data = result.get("data", {})
                
                # Extraer información clave según tipo
                key_info = []
                if doc_type == "contract":
                    if data.get("contraparte"):
                        key_info.append(f"Parte: {data['contraparte']}")
                    if data.get("fecha_vencimiento"):
                        key_info.append(f"Vence: {data['fecha_vencimiento']}")
                    if data.get("monto_total"):
                        key_info.append(f"Monto: ${data['monto_total']:,.2f}")
                elif doc_type in ["invoice", "financial"]:
                    if data.get("cliente"):
                        key_info.append(f"Cliente: {data['cliente']}")
                    if data.get("deuda_total"):
                        key_info.append(f"Deuda: ${data['deuda_total']:,.2f}")
                    if data.get("estado"):
                        key_info.append(f"Estado: {data['estado']}")
                
                key_info_str = " | ".join(key_info[:3]) if key_info else "Ver detalles"
                response_parts.append(f"| {doc_name[:50]} | {doc_type} | {key_info_str} |\n")
        
        # Recomendaciones accionables
        response_parts.append("\n### 🎯 Recomendaciones Accionables\n\n")
        
        if query_spec.get("query_type") == "contracts":
            response_parts.append("• **Revisar contratos próximos a vencer** para planificar renovaciones\n")
            response_parts.append("• **Evaluar cláusulas críticas** en contratos identificados\n")
        elif query_spec.get("query_type") in ["invoices", "financial"]:
            total_debt = sum(
                float(r.get("data", {}).get("deuda_total", 0) or r.get("data", {}).get("monto_vencido", 0) or 0)
                for r in results if isinstance(r, dict) and "group" not in r
            )
            if total_debt > 0:
                response_parts.append(f"• **Riesgo financiero total**: ${total_debt:,.2f}\n")
                response_parts.append("• **Acción inmediata**: Contactar clientes para cobranza\n")
                response_parts.append("• **Seguimiento**: Establecer plan de pagos para deudas altas\n")
        
        return "".join(response_parts)
    
    def simulate_scenario(
        self,
        scenario_query: str,
        structured_data_list: List[StructuredData],
        detection_results: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Simulador de escenarios "what-if".
        Ejemplo: "¿Qué pasaría si pago todas las facturas hoy?"
        """
        prompt = f"""Eres un simulador de escenarios empresariales. Analiza el escenario propuesto y calcula impactos.

ESCENARIO:
{scenario_query}

DATOS ACTUALES:
- Total facturas pendientes: {len([sd for sd in structured_data_list if sd.document_type == "invoice"])}
- Problemas detectados: {len(detection_results.get('problems', [])) if detection_results else 0}

Tu tarea:
1. Identificar qué cambiaría en el escenario
2. Calcular impactos financieros (montos, ROI, ahorros)
3. Evaluar impactos operacionales
4. Generar recomendación

Responde en JSON:
{{
    "scenario": "descripción del escenario",
    "current_state": {{
        "description": "estado actual",
        "metrics": {{"key": "value"}}
    }},
    "simulated_state": {{
        "description": "estado después del escenario",
        "metrics": {{"key": "value"}}
    }},
    "impact": {{
        "financial": {{
            "savings": 0,
            "costs": 0,
            "roi": 0,
            "roi_percentage": 0
        }},
        "operational": "descripción",
        "strategic": "descripción"
    }},
    "recommendation": "recomendación accionable"
}}"""
        
        try:
            raw = self.reasoning_llm.invoke(prompt).content.strip()
            if raw.startswith("```json"):
                raw = raw.replace("```json", "").replace("```", "").strip()
            elif raw.startswith("```"):
                raw = raw.replace("```", "").strip()
            
            scenario_result = json.loads(raw)
            
            # Enriquecer con datos reales
            if "pago todas las facturas" in scenario_query.lower() or "pay all invoices" in scenario_query.lower():
                total_debt = sum(
                    float(a.get("value", 0))
                    for sd in structured_data_list
                    for a in sd.amounts
                    if a.get("type") in ["vencido", "pendiente", "deuda"] and isinstance(a.get("value"), (int, float))
                )
                if total_debt > 0:
                    estimated_savings = total_debt * 0.15  # 15% en multas evitadas
                    scenario_result["impact"]["financial"]["savings"] = estimated_savings
                    scenario_result["impact"]["financial"]["roi"] = estimated_savings
                    scenario_result["impact"]["financial"]["roi_percentage"] = 15.0
            
            return {
                "scenario_query": scenario_query,
                "simulation": scenario_result,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "scenario_query": scenario_query,
                "error": str(e),
                "simulation": None
            }
    
    def get_query_history_summary(self, limit: int = 10) -> Dict[str, Any]:
        """Retorna resumen del historial de consultas empresariales."""
        recent_queries = self.query_history[-limit:] if self.query_history else []
        
        # Agrupar por categoría
        by_category = {}
        for query in recent_queries:
            category = query.get("category", "custom")
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(query)
        
        return {
            "total_queries": len(self.query_history),
            "recent_queries": recent_queries,
            "by_category": by_category,
            "most_common": self._get_most_common_queries(limit=5)
        }
    
    def _get_most_common_queries(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Identifica las consultas más comunes."""
        from collections import Counter
        query_texts = [q.get("query", "") for q in self.query_history]
        most_common = Counter(query_texts).most_common(limit)
        return [{"query": query, "count": count} for query, count in most_common]
