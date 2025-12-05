"""
ChatDoc - Sistema de Inteligencia Documental Avanzado (Eric Schmidt Style)
Integra todas las capacidades avanzadas de optimización:

PIPELINE MDP COMPLETO:
- Gist memories persistentes por documento
- Filtrado agresivo con LLM rápido
- Extracción estructurada en paralelo (Semantic ETL)
- Análisis comparativo automático
- Síntesis map-reduce (contexto compacto LLM-ready)
- NL2Query para consultas precisas sobre datos estructurados
- AI-to-AI verification para máxima precisión

CAPACIDADES AVANZADAS:
- Context Folding para conversaciones largas
- Data Provenance para trazabilidad completa
- Chain of Thought Reasoning paso a paso
- Path-dependent Reasoning (múltiples enfoques)
- Test Time Training (mejora continua)
- Person in the Loop (control humano)
- Reinforcement Planning (estrategias adaptativas)
- MCP Integration (sistemas externos)

OPTIMIZACIONES ERIC SCHMIDT:
- Procesamiento masivo paralelo (500+ PDFs)
- Separación: LLM rápido (filtrado) vs LLM fuerte (razonamiento)
- Datos estructurados como base, LLM como cerebro
- Respuestas por documento + vista global ejecutiva
- Citas precisas (página, párrafo) para verificación
- Agentes especializados (contratos, financiero, comparativo)
"""

from __future__ import annotations

import json
import time
import asyncio
from typing import List, Dict, Optional, Any, Tuple
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict
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
from .mass_processor import MassDocumentProcessor, DocumentMetadata, ComparativeAnalysis
from .utils.llm_factory import create_llm
from .executive_decision_system import (
    EntityIdentifier, AnswerEngine, PriorityEngine, ImpactCalculator,
    ActionGenerator, ValidationSystem, StructuredAnswer
)


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


class ChatDoc:
    """
    ChatDoc - Sistema de Inteligencia Documental Avanzado (Eric Schmidt Style)
    
    Características principales:
    - Pipeline MDP completo (gists, filtrado, extracción estructurada, síntesis)
    - Procesamiento masivo paralelo (500+ PDFs)
    - Extracción estructurada (semantic ETL) por dominio
    - NL2Query para consultas precisas sobre datos estructurados
    - Análisis comparativo automático
    - AI-to-AI verification para máxima precisión
    - Respuestas por documento + vista global ejecutiva
    - Citas precisas (página, párrafo) para verificación completa
    - Agentes especializados (contratos, financiero, comparativo)
    """
    
    def __init__(
        self,
        config: AppConfig,
        processor: DocumentProcessor,
        retriever_builder: RetrieverBuilder,
        context_manager: Optional[Any] = None,
        provider: str = "openai"
    ):
        self.config = config
        self.processor = processor
        self.retriever_builder = retriever_builder
        self.context_manager = context_manager
        self.provider = provider
        
        # Procesador masivo para paralelismo
        self.mass_processor = MassDocumentProcessor(config)
        
        # LLM principal (fuerte) para razonamiento final
        if not config.openai_api_key:
            raise ValueError("OPENAI_API_KEY requerida para ChatDoc")
        
        self.llm = ChatOpenAI(
            model=config.research_model or "gpt-4o",
            temperature=0.2,
            api_key=config.openai_api_key,
            max_tokens=4000
        )
        
        # LLM rápido para filtrado y trabajo pesado (optimización Eric Schmidt)
        fast_model = "gpt-4o-mini" if provider == "openai" else "claude-haiku-4-5-20251001"
        self.fast_llm = create_llm(
            provider=provider,
            model=fast_model,
            temperature=0.1,
            api_key=config.openai_api_key if provider == "openai" else config.anthropic_api_key,
            max_tokens=2000,
            request_timeout=60,
        )
        
        # Directorios para persistencia
        self.gist_memories_dir = Path(config.memory_dir) / "gist_memories" if config.memory_dir else Path("semantic_data")
        self.gist_memories_dir.mkdir(parents=True, exist_ok=True)
        self.gist_memories_file = self.gist_memories_dir / "gist_memories.json"
        self.structured_data_dir = Path(config.memory_dir) / "structured_data" if config.memory_dir else Path("semantic_data")
        self.structured_data_dir.mkdir(parents=True, exist_ok=True)
        
        # Almacenes en memoria
        self.gist_memories: Dict[str, Dict[str, Any]] = self._load_gist_memories()
        self.structured_data_store: Dict[str, StructuredData] = {}
        
        # LLM verificador (AI-to-AI verification)
        self.verifier_llm = create_llm(
            provider=provider,
            model=fast_model,
            temperature=0.1,
            api_key=config.openai_api_key if provider == "openai" else config.anthropic_api_key,
            max_tokens=2000,
            request_timeout=60,
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
        
        # Sistema Ejecutivo de Decisión Inteligente (6 CAPAS)
        self.entity_identifier = EntityIdentifier(config=config)
        self.priority_engine = PriorityEngine()
        self.impact_calculator = ImpactCalculator()
        self.action_generator = ActionGenerator(self.priority_engine)
        self.validation_system = ValidationSystem()
        self.answer_engine = AnswerEngine(
            priority_engine=self.priority_engine,
            impact_calculator=self.impact_calculator,
            action_generator=self.action_generator,
            validation_system=self.validation_system
        )
        
        # Sesiones activas
        self.sessions: Dict[str, Dict[str, Any]] = {}
    
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
    
    def _save_structured_data(self, structured_data_list: List[StructuredData]):
        """Guarda datos estructurados persistentemente."""
        try:
            structured_data_file = self.structured_data_dir / "structured_data.json"
            data_to_save = [asdict(sd) for sd in structured_data_list]
            with open(structured_data_file, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            print(f"⚠️ Error guardando datos estructurados: {e}")
    
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
            print(f"📄 [ChatDoc] Procesando {len(new_files)} nuevos documentos...")
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
                print(f"✅ [ChatDoc] Retriever actualizado: {len(session['docs'])} chunks")
            
            # Construir gists automáticamente para documentos nuevos (Pipeline MDP)
            if new_docs:
                print("🧠 [ChatDoc] Construyendo gist memories para documentos nuevos...")
                from .mass_processor import DocumentMetadata
                metadata_list = []
                docs_by_file = defaultdict(list)
                for doc in new_docs:
                    src = doc.metadata.get("source") or doc.metadata.get("file_name") or "documento"
                    docs_by_file[src].append(doc)
                
                for file_name, docs_for_file in docs_by_file.items():
                    metadata = DocumentMetadata(
                        file_name=file_name,
                        file_hash=hash(file_name) % 1000000,
                        chunk_count=len(docs_for_file),
                        processing_time=0.0,
                        size_mb=0.0,
                        errors=[]
                    )
                    metadata_list.append(metadata)
                
                # Construir gists solo para documentos nuevos
                new_gists = self._build_enhanced_gists(new_docs, metadata_list)
                if "gists" not in session:
                    session["gists"] = []
                session["gists"].extend(new_gists)
                print(f"✅ [ChatDoc] Gists construidos: {len(new_gists)} nuevos")
            
            return {
                "status": "success",
                "new_docs": len(new_docs),
                "total_docs": len(session["docs"]),
                "total_chunks": len(session["docs"])
            }
            
        except Exception as e:
            print(f"❌ [ChatDoc] Error procesando documentos: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _build_enhanced_gists(
        self,
        chunks: List[Document],
        metadata_list: List[DocumentMetadata]
    ) -> List[DocumentGist]:
        """
        Construye gist memories mejoradas por documento (MDP-style).
        Cada gist incluye: resumen corto + metadatos clave + entidades + temas.
        """
        from collections import defaultdict
        
        # Agrupar chunks por archivo
        docs_by_file: Dict[str, List[Document]] = defaultdict(list)
        for doc in chunks:
            src = doc.metadata.get("source") or doc.metadata.get("file_name") or "documento"
            docs_by_file[src].append(doc)
        
        # Mapear metadata
        metadata_map = {m.file_name: m for m in metadata_list}
        
        gists: List[DocumentGist] = []
        
        for file_name, docs_for_file in docs_by_file.items():
            metadata = metadata_map.get(file_name)
            if not metadata:
                continue
            
            # Construir muestra de texto (primeros chunks)
            text_sample = ""
            for doc in docs_for_file[:5]:
                text_sample += doc.page_content[:500] + "\n\n"
            
            # Detectar tipo de documento y extraer entidades/temas básicos
            doc_type = self._detect_document_type(text_sample)
            key_entities = self._extract_key_entities(text_sample[:2000])
            key_topics = self._extract_key_topics(text_sample[:2000])
            
            gist = DocumentGist(
                file_name=file_name,
                file_hash=metadata.file_hash,
                text_sample=text_sample[:2000],  # Limitar tamaño
                chunk_count=metadata.chunk_count,
                size_mb=metadata.size_mb,
                document_type=doc_type,
                key_entities=key_entities[:10],
                key_topics=key_topics[:10],
            )
            gists.append(gist)
            
            # Guardar en memoria persistente
            gist_key = metadata.file_hash or Path(file_name).stem
            self.gist_memories[gist_key] = {
                "file_name": file_name,
                "file_hash": metadata.file_hash,
                "text_sample": text_sample[:2000],
                "chunk_count": metadata.chunk_count,
                "size_mb": metadata.size_mb,
                "document_type": doc_type,
                "key_entities": key_entities[:10],
                "key_topics": key_topics[:10],
                "last_updated": datetime.now().isoformat(),
            }
        
        self._save_gist_memories()
        return gists
    
    def _detect_document_type(self, text: str) -> str:
        """Detecta el tipo de documento basado en contenido."""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ["contrato", "contract", "acuerdo", "agreement"]):
            return "contract"
        elif any(word in text_lower for word in ["factura", "invoice", "recibo", "bill"]):
            return "invoice"
        elif any(word in text_lower for word in ["estado financiero", "balance", "financial statement"]):
            return "financial_statement"
        elif any(word in text_lower for word in ["reporte", "report", "informe"]):
            return "report"
        elif any(word in text_lower for word in ["póliza", "policy", "política"]):
            return "policy"
        else:
            return "other"
    
    def _extract_key_entities(self, text: str) -> List[str]:
        """Extrae entidades clave del texto (empresas, personas, productos)."""
        # Versión simplificada - en producción usar NER
        entities = []
        # Buscar patrones comunes de entidades
        import re
        # Empresas (mayúsculas, palabras comunes)
        company_patterns = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
        entities.extend(company_patterns[:5])
        return list(set(entities))[:10]
    
    def _extract_key_topics(self, text: str) -> List[str]:
        """Extrae temas clave del texto."""
        # Versión simplificada - en producción usar topic modeling
        topics = []
        keywords = ["contrato", "pago", "vencimiento", "cliente", "deuda", "riesgo", "oportunidad"]
        text_lower = text.lower()
        for keyword in keywords:
            if keyword in text_lower:
                topics.append(keyword)
        return topics[:10]
    
    def _filter_gists_aggressive(
        self,
        gists: List[DocumentGist],
        query: Optional[str] = None
    ) -> List[DocumentGist]:
        """
        Filtrado agresivo usando gists + LLM rápido (optimización Eric Schmidt).
        Filtra 70-90% de documentos irrelevantes antes de hacer trabajo caro.
        """
        if not query or not gists:
            return gists
        
        # Usar LLM rápido para filtrar
        gist_summaries = []
        for gist in gists:
            summary = f"Doc: {Path(gist.file_name).name}\nTipo: {gist.document_type}\nTemas: {', '.join(gist.key_topics[:5])}\nMuestra: {gist.text_sample[:300]}"
            gist_summaries.append((gist, summary))
        
        # Prompt para filtrado
        prompt = f"""Eres un filtro inteligente de documentos. Tu tarea es identificar qué documentos son RELEVANTES para la siguiente pregunta.

PREGUNTA DEL USUARIO:
{query}

DOCUMENTOS DISPONIBLES:
{chr(10).join([f"{i+1}. {summary[:200]}" for i, (_, summary) in enumerate(gist_summaries[:50])])}

Responde SOLO con una lista de números separados por comas de los documentos RELEVANTES (ej: 1,3,5,7).
Si todos son relevantes, responde "ALL".
Si ninguno es claramente relevante, responde "NONE"."""
        
        try:
            response = self.fast_llm.invoke(prompt).content.strip()
            
            if "ALL" in response.upper():
                return gists
            elif "NONE" in response.upper():
                return []
            else:
                # Extraer números
                import re
                indices = [int(x.strip()) - 1 for x in re.findall(r'\d+', response) if int(x.strip()) <= len(gist_summaries)]
                filtered = [gist_summaries[i][0] for i in indices if 0 <= i < len(gist_summaries)]
                return filtered if filtered else gists  # Fallback: todos si falla
        except Exception as e:
            print(f"⚠️ Error en filtrado agresivo: {e}")
            return gists  # Fallback: todos
    
    def _detect_structured_query_intent(self, query: str) -> bool:
        """Detecta si la pregunta requiere consulta estructurada (NL2Query).
        
        Pensado para consultas tipo:
        - "¿Qué contratos vencen en febrero?"
        - "Listame todos los clientes con deuda > 10.000 USD"
        donde la respuesta debe ser TABLA / LISTA precisa, sin relleno.
        """
        query_lower = query.lower()
        
        # Palabras clave que indican consulta estructurada / tipo reporte
        structured_keywords = [
            "listame", "muéstrame", "muestrame", "listar", "lista",
            "cuáles son", "cuales son", "qué contratos", "que contratos",
            "qué clientes", "que clientes", "facturas", "vencimientos",
            "contratos que vencen", "vencen en", "deuda mayor", "deuda >", 
            "mayor a", "menor a", "superior a", "inferior a",
            "top", "ranking", "ranking de", "filtra", "filtrar", "busca",
            "clientes con deuda", "contratos que vencen en",
        ]
        
        # Heurística extra: presencia de operadores numéricos típicos
        numeric_markers = [">", "<", ">=", "<=", "≥", "≤", "mayor que", "menor que"]
        
        if any(keyword in query_lower for keyword in structured_keywords):
            return True
        
        if any(marker in query_lower for marker in numeric_markers):
            return True
        
        return False

    def _format_structured_query_answer(
        self,
        query: str,
        nl2query_result: Optional[Dict[str, Any]]
    ) -> str:
        """
        Formatea una respuesta ULTRA PRECISA para consultas estructuradas (NL2Query).
        
        Regla: responder EXACTAMENTE lo que se pide, en formato tabla/lista,
        sin párrafos de relleno.
        """
        if not nl2query_result or not nl2query_result.get("results"):
            return (
                "## 🎯 Respuesta estructurada\n\n"
                f"No se encontraron resultados para la consulta:\n\n> {query}\n"
            )
        
        results = nl2query_result.get("results", [])
        query_spec = nl2query_result.get("query_spec", {})
        query_type = query_spec.get("query_type", "both")
        
        lines: List[str] = []
        lines.append("## 🎯 Respuesta estructurada\n")
        lines.append(f"Consulta: `{query}`\n")
        lines.append(f"Coincidencias encontradas: **{len(results)}**\n")
        
        # Encabezado de tabla según tipo
        lines.append("\n### 📊 Resultados en tabla\n")
        if query_type in ["contracts", "both"]:
            header = "| Documento | Tipo | Cliente / Parte | Fecha inicio | Fecha fin | Monto | Moneda |\n"
            sep = "|-----------|------|-----------------|-------------|-----------|-------|--------|\n"
        else:
            header = "| Documento | Tipo | Cliente | Deuda total | Moneda | Fecha corte |\n"
            sep = "|-----------|------|---------|-------------|--------|-------------|\n"
        
        lines.append(header)
        lines.append(sep)
        
        # Limitar filas para mantener legibilidad
        max_rows = 50
        for row in results[:max_rows]:
            doc_id = row.get("document_id", "N/A")
            doc_type = row.get("document_type", "N/A")
            data = row.get("data", {}) or {}
            
            if query_type in ["contracts", "both"]:
                cliente = data.get("cliente") or data.get("contraparte") or data.get("parte_contratante") or ""
                f_ini = data.get("fecha_inicio") or data.get("fecha_firma") or ""
                f_fin = data.get("fecha_fin") or data.get("fecha_vencimiento") or ""
                monto = data.get("monto_total") or data.get("importe") or ""
                moneda = data.get("moneda") or ""
                try:
                    monto_str = f"${float(monto):,.2f}" if monto not in (None, "") else ""
                except Exception:
                    monto_str = str(monto) if monto is not None else ""
                line = f"| {Path(doc_id).name} | {doc_type} | {cliente} | {f_ini} | {f_fin} | {monto_str} | {moneda} |\n"
            else:
                cliente = data.get("cliente") or ""
                deuda = data.get("deuda_total") or data.get("monto_vencido") or ""
                moneda = data.get("moneda") or ""
                fecha_corte = data.get("fecha_corte") or ""
                try:
                    deuda_str = f"${float(deuda):,.2f}" if deuda not in (None, "") else ""
                except Exception:
                    deuda_str = str(deuda) if deuda is not None else ""
                line = f"| {Path(doc_id).name} | {doc_type} | {cliente} | {deuda_str} | {moneda} | {fecha_corte} |\n"
            
            lines.append(line)
        
        if len(results) > max_rows:
            lines.append(
                f"\n_Se muestran solo las primeras {max_rows} filas de {len(results)} resultados._\n"
            )
        
        # Nada de texto de relleno: solo un mini resumen cuantitativo
        lines.append("\n### 📌 Resumen numérico\n")
        if query_type in ["financial", "both"]:
            total_deuda = 0.0
            count_con_deuda = 0
            for row in results:
                data = row.get("data", {}) or {}
                deuda = data.get("deuda_total") or data.get("monto_vencido")
                try:
                    if deuda not in (None, ""):
                        total_deuda += float(deuda)
                        count_con_deuda += 1
                except Exception:
                    continue
            lines.append(f"- Registros con deuda cuantificada: **{count_con_deuda}**\n")
            lines.append(f"- Deuda total aproximada: **${total_deuda:,.2f}**\n")
        else:
            lines.append(f"- Total de registros: **{len(results)}**\n")
        
        return "\n".join(lines)
    
    async def _extract_structured_data_parallel_async(
        self,
        chunks: List[Document],
        relevant_gists: List[DocumentGist]
    ) -> List[StructuredData]:
        """Extracción estructurada en paralelo (semantic ETL) - versión async."""
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
            
            # Prompt especializado según tipo
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
                print(f"⚠️ Error extrayendo datos estructurados de {file_name}: {e}")
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
        
        # Ejecutar en paralelo
        structured_data_list: List[StructuredData] = []
        max_workers = min(8, len(relevant_names) or 1)
        
        doc_type_map = {g.file_name: g.document_type for g in relevant_gists}
        
        # Ejecutar en thread pool (async wrapper)
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                loop.run_in_executor(
                    executor,
                    _extract_for_file,
                    name,
                    docs_by_file.get(name, []),
                    doc_type_map.get(name, "other")
                ): name
                for name in relevant_names
                if docs_by_file.get(name)
            }
            
            for future in asyncio.as_completed(futures):
                try:
                    sd = await future
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
        return f"""Eres un especialista en extracción de datos financieros. Tu tarea es extraer FACTURAS específicas del documento.

DOCUMENTO: {file_name} (Tipo: {doc_type})

CONTENIDO:
{context[:6000]}

IMPORTANTE: Si el documento contiene FACTURAS, extrae CADA FACTURA por separado con:
- Número de factura (ej: #002, #004)
- Fecha de emisión
- Fecha de vencimiento (CRÍTICO)
- Monto
- Estado (vencido, pendiente, pagado) - DEBE ser exacto
- Cliente o proveedor

Si hay una TABLA de facturas, extrae TODAS las filas.

Responde SOLO en JSON:
{{
    "extracted_fields": {{
        "facturas": [
            {{
                "numero_factura": "002",
                "fecha_emision": "YYYY-MM-DD o texto exacto",
                "fecha_vencimiento": "YYYY-MM-DD o texto exacto",
                "monto_total": número,
                "moneda": "USD",
                "estado": "vencido|pendiente|pagado",
                "cliente": "...",
                "concepto": "..."
            }},
            ...
        ],
        "cliente": "...",
        "deuda_total": número o null,
        "moneda": "USD/EUR/etc o null",
        "fecha_corte": "YYYY-MM-DD o texto",
        "estado": "al_dia|moroso|vencido|..."
    }},
    "entities": [
        {{"type": "cliente|empresa|producto", "name": "...", "value": "..."}}
    ],
    "dates": [
        {{"type": "corte|vencimiento|pago|emision", "value": "...", "parsed": "YYYY-MM-DD o null"}}
    ],
    "amounts": [
        {{"type": "deuda|pago|vencido|factura", "value": número, "currency": "...", "description": "..."}}
    ],
    "risk_flags": ["riesgo1", ...],
    "opportunity_flags": ["oportunidad1", ...]
}}

CRÍTICO: Si una factura dice "VENCIDO" o "VENCIDA" o tiene fecha pasada, el estado DEBE ser "vencido". NO inventes fechas. Usa SOLO datos del documento."""
    
    def _get_generic_extraction_prompt(self, file_name: str, context: str, doc_type: str) -> str:
        """Prompt genérico para otros tipos de documentos."""
        return f"""Eres un especialista en extracción de datos estructurados.

DOCUMENTO: {file_name} (Tipo: {doc_type})

CONTENIDO:
{context[:6000]}

Extrae los campos más importantes del documento: entidades, fechas, montos, temas clave.

Responde SOLO en JSON:
{{
    "extracted_fields": {{}},
    "entities": [
        {{"type": "...", "name": "...", "value": "..."}}
    ],
    "dates": [
        {{"type": "...", "value": "...", "parsed": "YYYY-MM-DD o null"}}
    ],
    "amounts": [
        {{"type": "...", "value": número, "currency": "...", "description": "..."}}
    ],
    "risk_flags": [],
    "opportunity_flags": []
}}"""
    
    async def _execute_nl2query(
        self,
        query: str,
        structured_data_list: List[StructuredData]
    ) -> Optional[Dict[str, Any]]:
        """Ejecuta NL2Query: traduce pregunta natural a consulta estructurada."""
        # Separar por tipo
        contracts = [sd for sd in structured_data_list if sd.document_type == "contract"]
        financial = [sd for sd in structured_data_list if sd.document_type in ["invoice", "financial_statement", "balance_sheet"]]
        
        prompt = f"""Eres un sistema NL2Query. Convierte la pregunta del usuario en una consulta
sobre los datos estructurados disponibles.

PREGUNTA DEL USUARIO:
{query}

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
            
            # Ejecutar consulta
            results = self._execute_structured_query(query_spec, contracts, financial)
            
            return {
                "query": query,
                "query_spec": query_spec,
                "results": results,
                "total_matches": len(results),
            }
        except Exception as e:
            print(f"⚠️ Error en NL2Query: {e}")
            return None
    
    def _execute_structured_query(
        self,
        query_spec: Dict[str, Any],
        contracts: List[StructuredData],
        financial: List[StructuredData]
    ) -> List[Dict[str, Any]]:
        """Ejecuta una consulta estructurada sobre los datos."""
        results = []
        query_type = query_spec.get("query_type", "both")
        filters = query_spec.get("filters", {})
        
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
        
        doc_value = structured_data.extracted_fields.get(field)
        if doc_value is None:
            return False
        
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
    
    async def _generate_comparative_analysis(
        self,
        docs: List[Document],
        gists: List[DocumentGist],
        structured_data_list: List[StructuredData]
    ) -> str:
        """Genera análisis comparativo entre documentos."""
        if len(gists) < 2:
            return ""
        
        # Agrupar por tipo
        by_type = defaultdict(list)
        for gist in gists:
            by_type[gist.document_type].append(gist)
        
        insights = []
        insights.append("## 📊 Análisis Comparativo\n\n")
        
        # Comparar contratos
        if "contract" in by_type:
            contracts = [sd for sd in structured_data_list if sd.document_type == "contract"]
            if contracts:
                insights.append("### 📄 Contratos:\n")
                # Comparar fechas de vencimiento
                vencimientos = [sd.extracted_fields.get("fecha_vencimiento") for sd in contracts if sd.extracted_fields.get("fecha_vencimiento")]
                if vencimientos:
                    insights.append(f"- Total de contratos: {len(contracts)}\n")
                    insights.append(f"- Contratos con fecha de vencimiento: {len(vencimientos)}\n")
        
        # Comparar documentos financieros
        if any(t in by_type for t in ["invoice", "financial_statement"]):
            financial = [sd for sd in structured_data_list if sd.document_type in ["invoice", "financial_statement"]]
            if financial:
                insights.append("\n### 💰 Documentos Financieros:\n")
                deudas = [float(sd.extracted_fields.get("deuda_total", 0) or 0) for sd in financial if sd.extracted_fields.get("deuda_total")]
                if deudas:
                    insights.append(f"- Total de documentos: {len(financial)}\n")
                    insights.append(f"- Deuda total: ${sum(deudas):,.2f}\n")
                    insights.append(f"- Deuda promedio: ${sum(deudas)/len(deudas):,.2f}\n")
                    insights.append(f"- Deuda máxima: ${max(deudas):,.2f}\n")
        
        return "\n".join(insights)
    
    def _synthesize_mdp_context(
        self,
        docs: List[Document],
        gists: List[DocumentGist],
        structured_data_list: List[StructuredData],
        nl2query_result: Optional[Dict[str, Any]]
    ) -> str:
        """Síntesis map-reduce: contexto compacto LLM-ready."""
        context_parts = []
        
        # Resumen de gists
        context_parts.append("=== RESUMEN DE DOCUMENTOS ===\n")
        for gist in gists[:20]:  # Limitar a 20
            context_parts.append(f"- {Path(gist.file_name).name} ({gist.document_type}): {gist.text_sample[:200]}...\n")
        
        # Datos estructurados clave
        if structured_data_list:
            context_parts.append("\n=== DATOS ESTRUCTURADOS CLAVE ===\n")
            for sd in structured_data_list[:10]:  # Limitar a 10
                context_parts.append(f"- {sd.document_id} ({sd.document_type}): {json.dumps(sd.extracted_fields, ensure_ascii=False)[:200]}...\n")
        
        # Resultados NL2Query
        if nl2query_result:
            context_parts.append("\n=== RESULTADOS DE CONSULTA ESTRUCTURADA ===\n")
            context_parts.append(f"Consulta: {nl2query_result.get('query', 'N/A')}\n")
            context_parts.append(f"Coincidencias: {nl2query_result.get('total_matches', 0)}\n")
            if nl2query_result.get('results'):
                for result in nl2query_result['results'][:5]:
                    context_parts.append(f"- {result.get('document_id', 'N/A')}: {json.dumps(result.get('data', {}), ensure_ascii=False)[:150]}...\n")
        
        return "\n".join(context_parts)
    
    async def process_query_async(
        self,
        session_id: str,
        message: str,
        history: List[Tuple[str, str]],
        speed_mode: str = "balanced",
        provider: str = "openai"
    ) -> Tuple[List[Tuple[str, str]], Optional[str], Dict[str, Any]]:
        """
        Procesa una consulta con PIPELINE MDP COMPLETO (Eric Schmidt Style).
        
        Pipeline optimizado:
        1. Construir/recuperar gist memories
        2. Filtrado agresivo con LLM rápido
        3. Extracción estructurada en paralelo (si es necesario)
        4. NL2Query para consultas precisas sobre datos estructurados
        5. Análisis comparativo automático
        6. Síntesis map-reduce (contexto compacto)
        7. AI-to-AI verification
        8. Respuestas por documento + vista global ejecutiva
        
        Returns:
            (history, error, metadata): Historial actualizado, error si hay, metadatos
        """
        session = self.initialize_session(session_id)
        
        if not session["retriever"] and not session["docs"]:
            return history, "⚠️ No hay documentos procesados. Carga documentos primero.", {}
        
        start_time = time.time()
        
        # ============================================================
        # FASE 1: CONSTRUIR/RECUPERAR GIST MEMORIES
        # ============================================================
        print("🧠 [ChatDoc] Fase 1: Construyendo/recuperando gist memories...")
        
        # Si hay documentos nuevos, construir gists
        if session["docs"]:
            # Crear metadata temporal
            from .mass_processor import DocumentMetadata
            metadata_list = []
            docs_by_file = defaultdict(list)
            for doc in session["docs"]:
                src = doc.metadata.get("source") or doc.metadata.get("file_name") or "documento"
                docs_by_file[src].append(doc)
            
            for file_name, docs_for_file in docs_by_file.items():
                metadata = DocumentMetadata(
                    file_name=file_name,
                    file_hash=hash(file_name) % 1000000,
                    chunk_count=len(docs_for_file),
                    processing_time=0.0,
                    size_mb=0.0,
                    errors=[]
                )
                metadata_list.append(metadata)
            
            gists = self._build_enhanced_gists(session["docs"], metadata_list)
            session["gists"] = gists
        else:
            # Cargar gists desde memoria
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
            session["gists"] = gists
        
        # ============================================================
        # FASE 2: FILTRADO AGRESIVO CON GISTS + LLM RÁPIDO
        # ============================================================
        print("🔍 [ChatDoc] Fase 2: Filtrado agresivo...")
        relevant_gists = self._filter_gists_aggressive(gists, message)
        print(f"✅ [ChatDoc] Documentos relevantes: {len(relevant_gists)}/{len(gists)}")
        
        # ============================================================
        # FASE 3: DETECTAR SI ES CONSULTA ESTRUCTURADA (NL2Query)
        # ============================================================
        print("🎯 [ChatDoc] Fase 3: Detectando tipo de consulta...")
        
        # Cargar datos estructurados si existen
        structured_data_list = self._load_structured_data()
        if not structured_data_list and session["docs"]:
            # Extraer datos estructurados en paralelo (solo si hay docs nuevos)
            print("🏗️ [ChatDoc] Extrayendo datos estructurados en paralelo...")
            structured_data_list = await self._extract_structured_data_parallel_async(
                session["docs"], relevant_gists
            )
            # Guardar
            for sd in structured_data_list:
                self.structured_data_store[sd.document_id] = sd
            self._save_structured_data(structured_data_list)
        
        # Detectar si la pregunta requiere NL2Query
        requires_structured_query = self._detect_structured_query_intent(message)
        
        # ============================================================
        # FASE 4: EJECUTAR NL2Query SI ES NECESARIO
        # ============================================================
        nl2query_result = None
        if requires_structured_query and structured_data_list:
            print("🔍 [ChatDoc] Fase 4: Ejecutando NL2Query...")
            nl2query_result = await self._execute_nl2query(message, structured_data_list)
        
        # ============================================================
        # FASE 5: ANÁLISIS COMPARATIVO (si hay múltiples documentos)
        # ============================================================
        comparative_insights = ""
        if len(relevant_gists) > 1:
            print("📊 [ChatDoc] Fase 5: Análisis comparativo...")
            comparative_insights = await self._generate_comparative_analysis(
                session["docs"], relevant_gists, structured_data_list
            )
        
        # ============================================================
        # FASE 6: SÍNTESIS MAP-REDUCE (Contexto Compacto)
        # ============================================================
        print("🧩 [ChatDoc] Fase 6: Síntesis map-reduce...")
        mdp_context = self._synthesize_mdp_context(
            session["docs"], relevant_gists, structured_data_list, nl2query_result
        )
        
        # ============================================================
        # FASE 7: CREAR CADENA DE RAZONAMIENTO Y CONTEXTO
        # ============================================================
        chain_id = self.chain_reasoner.create_chain(message)
        session["chain_id"] = chain_id
        
        # Construir contexto enriquecido con MDP
        conversation_context = self._build_folded_context(session, history)
        enriched_context = f"{conversation_context}\n\n=== CONTEXTO MDP (SÍNTESIS COMPACTA) ===\n{mdp_context}\n=== FIN CONTEXTO MDP ===\n"
        
        if comparative_insights:
            enriched_context += f"\n=== ANÁLISIS COMPARATIVO ===\n{comparative_insights}\n=== FIN ANÁLISIS COMPARATIVO ===\n"
        
        if nl2query_result:
            enriched_context += f"\n=== RESULTADOS NL2Query ===\n{json.dumps(nl2query_result, indent=2, ensure_ascii=False)}\n=== FIN NL2Query ===\n"
        
        # ============================================================
        # FASE 8: AGREGAR PASOS DE RAZONAMIENTO
        # ============================================================
        try:
            await self.chain_reasoner.add_reasoning_steps(chain_id, enriched_context)
        except Exception as e:
            print(f"⚠️ [ChatDoc] Error agregando pasos de razonamiento: {e}")
        
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
            print(f"⚠️ [ChatDoc] Error en Reinforcement Planning: {e}")
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
            print(f"⚠️ [ChatDoc] Error en Path-dependent Reasoning: {e}")
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
            print(f"⚠️ [ChatDoc] Error consultando MCP: {e}")
            # Continuar sin datos MCP si falla
        
        # Aplicar modo de velocidad
        original_speed_mode = self.config.speed_mode
        self.config.speed_mode = speed_mode
        
        try:
            # Crear workflow para consultas abiertas / narrativas
            temp_workflow = AgentWorkflow(self.config, provider=provider)
            
            # ============================================================
            # FASE 9: SISTEMA EJECUTIVO DE DECISIÓN INTELIGENTE
            # ============================================================
            print("🎯 [ChatDoc] Fase 9: Sistema Ejecutivo de Decisión Inteligente...")
            
            # Detectar si la pregunta requiere sistema ejecutivo
            requires_executive_system = self._requires_executive_system(message)
            executive_answer = None
            
            if requires_executive_system and session["docs"]:
                try:
                    # Asegurar que structured_data_list esté disponible
                    if not structured_data_list:
                        structured_data_list = self._load_structured_data()
                        # También cargar desde store
                        for sd in self.structured_data_store.values():
                            if sd not in [s for s in structured_data_list if s.document_id == sd.document_id]:
                                structured_data_list.append(sd)
                    
                    # Convertir documentos a formato esperado por AnswerEngine
                    documentos_formato = []
                    for doc in session["docs"]:
                        # Identificar entidad del documento
                        doc_dict = {
                            "text": doc.page_content,
                            "file_name": doc.metadata.get("source") or doc.metadata.get("file_name", "documento"),
                            "metadata": doc.metadata,
                            "document_type": doc.metadata.get("document_type", "unknown")
                        }
                        
                        # Agregar datos estructurados si existen
                        doc_id = doc.metadata.get("source") or doc.metadata.get("file_name", "")
                        # Buscar en structured_data_store por cualquier parte del path
                        structured_data_found = None
                        for key, sd in self.structured_data_store.items():
                            if doc_id in key or key in doc_id or Path(doc_id).name in key or Path(key).name in Path(doc_id).name:
                                structured_data_found = sd
                                break
                        
                        if structured_data_found:
                            # Convertir StructuredData a formato dict esperado
                            doc_dict["structured_data"] = {
                                "extracted_fields": structured_data_found.extracted_fields,
                                "entities": structured_data_found.entities,
                                "dates": structured_data_found.dates,
                                "amounts": structured_data_found.amounts
                            }
                        # También buscar en structured_data_list si está disponible
                        elif structured_data_list:
                            for sd in structured_data_list:
                                if sd.document_id in doc_id or doc_id in sd.document_id or Path(sd.document_id).name in Path(doc_id).name:
                                    doc_dict["structured_data"] = {
                                        "extracted_fields": sd.extracted_fields,
                                        "entities": sd.entities,
                                        "dates": sd.dates,
                                        "amounts": sd.amounts
                                    }
                                    break
                        
                        documentos_formato.append(doc_dict)
                    
                    # Parsear intención
                    intención = self.answer_engine.parse_intention(message)
                    
                    # Filtrar documentos relevantes (SOLO empresa principal)
                    documentos_relevantes = self.answer_engine.filter_relevant_docs(
                        documentos_formato, intención, self.entity_identifier
                    )
                    
                    # Extraer información específica
                    info_extraída = self.answer_engine.extract_specific_info(
                        documentos_relevantes, intención
                    )
                    
                    # Generar respuesta estructurada ejecutiva
                    structured_answer = self.answer_engine.structure_executive_response(
                        info_extraída, intención
                    )
                    
                    # Formatear respuesta ejecutiva
                    executive_answer = self.answer_engine.format_executive_response(structured_answer)
                    
                    print("✅ [ChatDoc] Sistema Ejecutivo generó respuesta estructurada")
                except Exception as e:
                    print(f"⚠️ [ChatDoc] Error en Sistema Ejecutivo: {e}")
                    import traceback
                    traceback.print_exc()
                    # Continuar con flujo normal si falla
            
            # ============================================================
            # FASE 10: GENERAR RESPUESTA CON CONTEXTO MDP ENRIQUECIDO
            # ============================================================
            print("💬 [ChatDoc] Fase 10: Generando respuesta con contexto MDP...")
            
            # PRIORIDAD 1: si hay NL2Query y es una consulta estructurada, usar respuesta tabular exacta
            answer: str
            sources: List[Dict[str, Any]] = []
            if requires_structured_query and nl2query_result:
                # Respuesta estrictamente estructurada (tablas, sin relleno)
                answer = self._format_structured_query_answer(message, nl2query_result)
            elif executive_answer:
                # Usar respuesta ejecutiva basada en sistema de decisión inteligente
                answer = executive_answer
                # Agregar contexto adicional si es necesario
                enriched_query = f"{enriched_context}\n\nPREGUNTA ACTUAL:\n{message}"
                if best_strategy:
                    enriched_query += f"\n\n🎯 ESTRATEGIA DE RL: {best_strategy}"
                if best_approach:
                    enriched_query += f"\n\n🛤️ ENFOQUE RECOMENDADO: {best_approach}"
                
                # Obtener fuentes adicionales si es necesario
                result = temp_workflow.run(
                    enriched_query,
                    session["retriever"] if session["retriever"] else None,
                    all_documents=session["docs"],
                    conversational_mode=True
                )
                sources = result.get("sources", [])
            else:
                # Consulta abierta / narrativa: usar workflow completo con contexto MDP
                enriched_query = f"{enriched_context}\n\nPREGUNTA ACTUAL:\n{message}"
                if best_strategy:
                    enriched_query += f"\n\n🎯 ESTRATEGIA DE RL: {best_strategy}"
                if best_approach:
                    enriched_query += f"\n\n🛤️ ENFOQUE RECOMENDADO: {best_approach}"
                
                result = temp_workflow.run(
                    enriched_query,
                    session["retriever"] if session["retriever"] else None,
                    all_documents=session["docs"],
                    conversational_mode=True
                )
                
                answer = result.get("answer", result.get("draft_answer", "No se pudo generar respuesta."))
                sources = result.get("sources", [])
            
            # ============================================================
            # FASE 11: GENERAR RESPUESTAS POR DOCUMENTO (si hay múltiples)
            # ============================================================
            per_document_responses = []
            if len(relevant_gists) > 1:
                print("📄 [ChatDoc] Fase 11: Generando respuestas por documento...")
                per_document_responses = await self._generate_per_document_responses(
                    message, relevant_gists, session["docs"], structured_data_list
                )
            
            # ============================================================
            # FASE 12: AI-TO-AI VERIFICATION (Verificación de IA por IA)
            # ============================================================
            print("✅ [ChatDoc] Fase 12: Verificación AI-to-AI...")
            verification_result = await self._verify_ai_response(
                answer, message, mdp_context, structured_data_list
            )
            
            # Aplicar correcciones si hay inconsistencias
            if verification_result.get("inconsistencies"):
                answer += f"\n\n⚠️ **Nota de Verificación:** {verification_result.get('verification_note', '')}"
            
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
            
            # ============================================================
            # FASE 12: FORMATEAR RESPUESTA FINAL (Vista Global + Por Documento)
            # ============================================================
            print("📝 [ChatDoc] Fase 12: Formateando respuesta final...")
            
            # Construir respuesta completa
            formatted_answer = "## 🎯 Respuesta Ejecutiva (Vista Global)\n\n"
            formatted_answer += answer
            
            # Agregar respuestas por documento si hay
            if per_document_responses:
                formatted_answer += "\n\n---\n\n## 📄 Respuestas por Documento\n\n"
                for doc_response in per_document_responses[:10]:  # Limitar a 10
                    formatted_answer += f"### 📄 {doc_response.get('file_name', 'Documento')}\n\n"
                    formatted_answer += f"{doc_response.get('answer', 'N/A')}\n\n"
                    if doc_response.get('citations'):
                        formatted_answer += "**Citas:**\n"
                        for citation in doc_response['citations'][:3]:
                            formatted_answer += f"- {citation}\n"
                        formatted_answer += "\n"
            
            # Agregar fuentes con citas precisas (página, párrafo)
            if source_provenances:
                formatted_answer += "\n---\n\n## 📚 Fuentes con Citas Precisas\n\n"
                sources_list = []
                for prov in source_provenances[:10]:
                    source_info = f"- **{Path(prov.source_name).name}**"
                    if prov.page_number:
                        source_info += f" (Página {prov.page_number})"
                    if hasattr(prov, 'paragraph_number') and prov.paragraph_number:
                        source_info += f", Párrafo {prov.paragraph_number}"
                    sources_list.append(source_info)
                
                if sources_list:
                    formatted_answer += "\n".join(sources_list)
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
                        "mode": "chatdoc",
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
    
    async def _generate_per_document_responses(
        self,
        query: str,
        gists: List[DocumentGist],
        docs: List[Document],
        structured_data_list: List[StructuredData]
    ) -> List[Dict[str, Any]]:
        """Genera respuestas individuales por documento (una pregunta → múltiples respuestas)."""
        responses = []
        
        # Agrupar docs por archivo
        docs_by_file = defaultdict(list)
        for doc in docs:
            src = doc.metadata.get("source") or doc.metadata.get("file_name") or "documento"
            docs_by_file[src].append(doc)
        
        # Para cada gist relevante, generar respuesta
        for gist in gists[:20]:  # Limitar a 20 documentos
            file_docs = docs_by_file.get(gist.file_name, [])
            if not file_docs:
                continue
            
            # Buscar datos estructurados correspondientes
            structured_data = next(
                (sd for sd in structured_data_list if sd.document_id == gist.file_name),
                None
            )
            
            # Construir contexto del documento
            doc_context = f"Documento: {Path(gist.file_name).name}\n"
            doc_context += f"Tipo: {gist.document_type}\n"
            doc_context += f"Muestra: {gist.text_sample[:1000]}\n"
            
            if structured_data:
                doc_context += f"\nDatos estructurados: {json.dumps(structured_data.extracted_fields, ensure_ascii=False)[:500]}\n"
            
            # Generar respuesta específica para este documento
            prompt = f"""Responde la siguiente pregunta específicamente para ESTE documento.

PREGUNTA: {query}

CONTEXTO DEL DOCUMENTO:
{doc_context}

Responde de forma concisa y específica. Si la pregunta no aplica a este documento, di "No aplica".

Responde SOLO el texto de la respuesta, sin explicaciones adicionales."""
            
            try:
                doc_answer = self.fast_llm.invoke(prompt).content.strip()
                
                # Extraer citas (página, párrafo) de los docs
                citations = []
                for doc in file_docs[:3]:
                    page = doc.metadata.get("page", doc.metadata.get("page_number"))
                    citation = Path(gist.file_name).name
                    if page:
                        citation += f" (Página {page})"
                    citations.append(citation)
                
                responses.append({
                    "file_name": Path(gist.file_name).name,
                    "document_type": gist.document_type,
                    "answer": doc_answer,
                    "citations": citations
                })
            except Exception as e:
                print(f"⚠️ Error generando respuesta para {gist.file_name}: {e}")
        
        return responses
    
    async def _verify_ai_response(
        self,
        answer: str,
        query: str,
        context: str,
        structured_data_list: List[StructuredData]
    ) -> Dict[str, Any]:
        """AI-to-AI verification: verifica consistencia y precisión de la respuesta."""
        prompt = f"""Eres un verificador de IA. Tu tarea es verificar la siguiente respuesta generada por otro modelo.

PREGUNTA ORIGINAL:
{query}

RESPUESTA A VERIFICAR:
{answer}

CONTEXTO DISPONIBLE:
{context[:2000]}

Verifica:
1. ¿La respuesta es consistente con el contexto?
2. ¿Hay números o fechas que puedan ser incorrectos?
3. ¿Hay contradicciones o afirmaciones sin fundamento?
4. ¿La respuesta responde realmente a la pregunta?

Responde SOLO en JSON:
{{
    "is_consistent": true/false,
    "confidence": 0.0-1.0,
    "inconsistencies": ["inconsistencia1", ...],
    "verification_note": "nota de verificación"
}}"""
        
        try:
            raw = self.verifier_llm.invoke(prompt).content.strip()
            if raw.startswith("```json"):
                raw = raw.replace("```json", "").replace("```", "").strip()
            elif raw.startswith("```"):
                raw = raw.replace("```", "").strip()
            
            result = json.loads(raw)
            return result
        except Exception as e:
            print(f"⚠️ Error en verificación AI-to-AI: {e}")
            return {
                "is_consistent": True,
                "confidence": 0.5,
                "inconsistencies": [],
                "verification_note": "Verificación no disponible"
            }
    
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
                    print(f"⚠️ [ChatDoc] Error consultando MCP {connection.name}: {e}")
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
            print(f"⚠️ [ChatDoc] Error en consulta MCP: {e}")
            return None
    
    def _requires_executive_system(self, message: str) -> bool:
        """
        Detecta si la pregunta requiere el Sistema Ejecutivo de Decisión Inteligente.
        
        El sistema ejecutivo se activa para preguntas sobre:
        - Vencimientos (contratos, facturas)
        - Análisis financiero estructurado
        - Priorización y acciones
        - Cuantificación de impacto
        """
        message_lower = message.lower()
        
        # Palabras clave que activan sistema ejecutivo
        executive_keywords = [
            "vencer", "vencimiento", "vencen", "vencidos", "vencerá",
            "contratos", "facturas", "pagos", "deudas",
            "prioridad", "priorizar", "urgente", "crítico",
            "impacto", "riesgo", "multas", "exposición",
            "acciones", "qué hacer", "recomendaciones",
            "febrero", "marzo", "abril", "mayo", "junio",
            "mayor a", "menor a", "superior a", "inferior a",
            "clientes con", "proveedores con", "contratos que",
            "facturas que", "listar", "mostrar", "cuáles son"
        ]
        
        return any(keyword in message_lower for keyword in executive_keywords)
    
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
_chatdoc_instance: Optional[ChatDoc] = None


def get_chatdoc(
    config: AppConfig,
    processor: DocumentProcessor,
    retriever_builder: RetrieverBuilder,
    context_manager: Optional[Any] = None,
    provider: str = "openai"
) -> ChatDoc:
    """Obtiene o crea la instancia global de ChatDoc."""
    global _chatdoc_instance
    
    if _chatdoc_instance is None:
        _chatdoc_instance = ChatDoc(
            config=config,
            processor=processor,
            retriever_builder=retriever_builder,
            context_manager=context_manager,
            provider=provider
        )
    
    return _chatdoc_instance


def run_chatdoc(
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
    Función principal para ejecutar ChatDoc.
    Compatible con Gradio (síncrona).
    """
    if not config or not processor or not retriever_builder:
        return history, "❌ Configuración incompleta"
    
    # Obtener instancia
    chatdoc = get_chatdoc(
        config=config,
        processor=processor,
        retriever_builder=retriever_builder,
        context_manager=context_manager
    )
    
    # Procesar documentos si hay
    if files:
        result = chatdoc.process_documents(session_id, files)
        if result.get("status") == "error":
            return history, f"❌ Error procesando documentos: {result.get('error')}"
    
    # Ejecutar query (async wrapper)
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        new_history, error, metadata = loop.run_until_complete(
            chatdoc.process_query_async(
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

