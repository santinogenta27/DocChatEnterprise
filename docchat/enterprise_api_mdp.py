"""Enterprise API MDP Mode - Procesamiento paralelo tipo MDP/MDP-Agent.

Este modo es un CLON del modo Enterprise API original, pero diseñado para
consultas con MUCHOS documentos (100–300 PDFs o más) usando:

- Procesamiento masivo paralelo (`MassDocumentProcessor`)
- "Gist memories" ligeras por documento
- Filtrado previo con LLM rápido sobre las gists
- Extracción de evidencias en paralelo por documento
- Síntesis tipo map-reduce en un espacio de conocimiento compacto

IMPORTANTE:
- NO modifica `EnterpriseAPIMode` original.
- La interfaz de alto nivel es muy similar: `process_enterprise_documents`
  y `process_enterprise_documents_streaming`, pero internamente usa el
  pipeline tipo MDP (abstracción → filtrado → síntesis paralela).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, List, Iterator, Optional, Tuple
from datetime import datetime
import json

from langchain_core.documents import Document

from .config import AppConfig
from .mass_processor import MassDocumentProcessor, DocumentMetadata, ComparativeAnalysis
from .memory import MemoryStore, ContextManager


@dataclass
class DocumentGist:
    """Gist/memoria ligera por documento."""
    file_name: str
    file_hash: str
    text_sample: str
    chunk_count: int
    size_mb: float


class EnterpriseAPIMDPMode:
    """
    Modo Enterprise API (MDP Parallel):

    - Pensado para 100–300+ PDFs por consulta.
    - Usa MassDocumentProcessor para paralelizar la ingestión.
    - Genera gists por documento y filtra con un LLM rápido.
    - Extrae evidencias en paralelo y las reduce en un contexto compacto
      listo para el modelo principal (LLM fuerte).
    """

    def __init__(self, config: AppConfig, provider: str = "openai"):
        self.config = config
        self.provider = provider
        self.mass_processor = MassDocumentProcessor(config)

        # Memoria opcional
        self.memory_store = MemoryStore(config.memory_dir, config.memory_retention_days) if config.enable_memory else None
        self.context_manager = ContextManager(self.memory_store, config) if self.memory_store else None

        # LLMs
        from docchat.utils.llm_factory import create_llm

        # Modelo "fuerte" para síntesis final
        self.reasoning_llm = create_llm(
            provider=provider,
            model=config.agentic_model,
            temperature=0.2,
            api_key=config.openai_api_key if provider == "openai" else config.anthropic_api_key,
            max_tokens=8000,
            request_timeout=120,
        )

        # Modelo rápido para gists/filtrado
        fast_model = "gpt-4o-mini" if provider == "openai" else "claude-haiku-4-5-20251001"
        self.fast_llm = create_llm(
            provider=provider,
            model=fast_model,
            temperature=0.2,
            api_key=config.openai_api_key if provider == "openai" else config.anthropic_api_key,
            max_tokens=4000,
            request_timeout=60,
        )

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------
    def process_enterprise_documents_streaming(
        self,
        files: List,
        auto_detect: bool = True,
        rules: Optional[List[Dict]] = None,
    ) -> Iterator[str]:
        """Procesa documentos con streaming de resultados (pipeline MDP Parallel)."""
        yield "## 🚀 Procesamiento Enterprise API (MDP Parallel) Iniciado\n\n"
        yield f"📄 Documentos recibidos: {len(files)}\n\n"

        try:
            # 1) Procesamiento masivo en paralelo (ingestión)
            yield "### ⚙️ Procesando documentos en paralelo...\n\n"
            chunks, metadata_list, comparative = self.mass_processor.process_massive_batch(
                files=files,
                enable_comparison=True,
            )
            yield f"- ✅ Chunks generados: {len(chunks)}\n"
            yield f"- ✅ Documentos exitosos: {sum(1 for m in metadata_list if m.chunk_count > 0)}\n\n"

            # 2) Construir gists por documento
            yield "### 🧠 Construyendo gists (memorias ligeras) por documento...\n\n"
            gists = self._build_gists(chunks, metadata_list)
            yield f"- ✅ Gists generadas: {len(gists)}\n\n"

            # 3) Filtrado guiado por gists (MDP: memory-guided filtering)
            yield "### 🔍 Filtrando documentos relevantes usando gists + LLM rápido...\n\n"
            relevant_gists = self._filter_gists_with_llm(gists)
            yield f"- ✅ Documentos marcados como relevantes: {len(relevant_gists)}\n\n"

            if not relevant_gists:
                yield "⚠️ Ningún documento fue considerado claramente relevante. Mostrando visión global.\n\n"

            # 4) Extracción de evidencias en paralelo (map)
            yield "### 🧩 Extrayendo evidencias clave en paralelo (map)...\n\n"
            evidence_by_doc = self._extract_evidence_parallel(chunks, relevant_gists)
            yield f"- ✅ Documentos con evidencias: {len([d for d in evidence_by_doc.values() if d])}\n\n"

            # 5) Síntesis tipo map-reduce en un contexto compacto
            yield "### 🧠 Sintetizando contexto compacto tipo MDP (reduce)...\n\n"
            mdp_context, mdp_summary = self._synthesize_mdp_context(evidence_by_doc, comparative)
            yield mdp_summary + "\n\n"

            # 6) (Opcional) detección automática sobre el contexto ya reducido
            detection_results = {"problems": [], "opportunities": [], "patterns": []}
            if auto_detect:
                yield "### 🔎 Detección automática sobre contexto MDP...\n\n"
                detection_results = self._auto_detect_from_mdp_context(mdp_context)
                if detection_results.get("problems"):
                    yield f"- ⚠️ Problemas: {len(detection_results['problems'])}\n"
                if detection_results.get("opportunities"):
                    yield f"- 💡 Oportunidades: {len(detection_results['opportunities'])}\n"
                if detection_results.get("patterns"):
                    yield f"- 🔍 Patrones: {len(detection_results['patterns'])}\n"
                yield "\n"

            # 7) Resumen ejecutivo final para el usuario (modo story)
            yield "### 📊 Resumen ejecutivo tipo consultor (sobre contexto MDP)\n\n"
            final_report = self._generate_executive_report(mdp_context, detection_results)
            yield final_report + "\n\n"

            # 8) Guardar en memoria (opcional)
            if self.context_manager:
                self._save_to_memory_mdp(mdp_context, detection_results)

            yield "✅ **Procesamiento Enterprise API (MDP Parallel) completado!**\n"

        except Exception as e:
            yield f"\n❌ **Error en Enterprise API (MDP Parallel)**: {str(e)}\n"

    def process_enterprise_documents(
        self,
        files: List,
        auto_detect: bool = True,
        rules: Optional[List[Dict]] = None,
        stream: bool = False,
    ) -> Dict[str, Any]:
        """Versión no streaming: devuelve un dict con resultados del pipeline MDP."""
        results: Dict[str, Any] = {
            "status": "processing",
            "timestamp": datetime.now().isoformat(),
            "documents_processed": len(files),
            "chunks_generated": 0,
            "gists": [],
            "relevant_gists": [],
            "mdp_context": "",
            "mdp_summary": "",
            "problems_detected": [],
            "opportunities_detected": [],
            "patterns_found": [],
            "executive_report": "",
        }

        try:
            chunks, metadata_list, comparative = self.mass_processor.process_massive_batch(
                files=files,
                enable_comparison=True,
            )
            results["chunks_generated"] = len(chunks)

            gists = self._build_gists(chunks, metadata_list)
            results["gists"] = [gist.__dict__ for gist in gists]

            relevant_gists = self._filter_gists_with_llm(gists)
            results["relevant_gists"] = [gist.__dict__ for gist in relevant_gists]

            evidence_by_doc = self._extract_evidence_parallel(chunks, relevant_gists)
            mdp_context, mdp_summary = self._synthesize_mdp_context(evidence_by_doc, comparative)

            results["mdp_context"] = mdp_context
            results["mdp_summary"] = mdp_summary

            detection_results = {"problems": [], "opportunities": [], "patterns": []}
            if auto_detect:
                detection_results = self._auto_detect_from_mdp_context(mdp_context)
            results["problems_detected"] = detection_results.get("problems", [])
            results["opportunities_detected"] = detection_results.get("opportunities", [])
            results["patterns_found"] = detection_results.get("patterns", [])

            executive_report = self._generate_executive_report(mdp_context, detection_results)
            results["executive_report"] = executive_report

            if self.context_manager:
                self._save_to_memory_mdp(mdp_context, detection_results)

            results["status"] = "completed"
            return results
        except Exception as e:
            results["status"] = "error"
            results["error"] = str(e)
            return results

    # ------------------------------------------------------------------
    # Etapas internas del pipeline MDP-like
    # ------------------------------------------------------------------
    def _build_gists(
        self,
        chunks: List[Document],
        metadata_list: List[DocumentMetadata],
    ) -> List[DocumentGist]:
        """Construye una gist simple por documento a partir de los chunks."""
        # Agrupar chunks por hash/nombre de archivo
        from collections import defaultdict

        docs_by_file: Dict[str, List[Document]] = defaultdict(list)
        for doc in chunks:
            src = doc.metadata.get("source") or doc.metadata.get("file_name") or "documento"
            docs_by_file[src].append(doc)

        # Mapear metadata por nombre de archivo
        meta_by_name: Dict[str, DocumentMetadata] = {m.file_name: m for m in metadata_list}

        gists: List[DocumentGist] = []
        for file_name, docs_for_file in docs_by_file.items():
            meta = meta_by_name.get(file_name)
            # Tomar primeras páginas como muestra
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

            gists.append(
                DocumentGist(
                    file_name=file_name,
                    file_hash=file_hash,
                    text_sample=text_sample,
                    chunk_count=len(docs_for_file),
                    size_mb=(meta.size_mb if meta else 0.0),
                )
            )

        return gists

    def _filter_gists_with_llm(self, gists: List[DocumentGist]) -> List[DocumentGist]:
        """Filtra gists relevantes usando un LLM ligero (approx. memory-guided filtering)."""
        if not gists:
            return []

        # Construir prompt compacto con muchos documentos, pedir selección binaria
        items = []
        for i, gist in enumerate(gists, 1):
            snippet = gist.text_sample[:600].replace("\n", " ")
            items.append(f"{i}. {gist.file_name} :: {snippet}")

        joined = "\n\n".join(items)
        prompt = f"""Eres un sistema que prioriza documentos relevantes para análisis empresarial.

Analiza rápidamente las siguientes "gists" de documentos (resúmenes muy breves)
y decide cuáles parecen especialmente relevantes para:
- detectar riesgos, oportunidades de negocio y patrones
- análisis comparativo entre documentos (contratos, informes, políticas, etc.)

Documentos:
{joined}

Devuelve SOLO un JSON con este formato:
{{
  "relevant_indices": [1, 3, 5],
  "comment": "breve justificación general (1-2 frases)"
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
            # Si algo falla, considerar todos relevantes (mejor recall que perder información)
            indices = set(range(1, len(gists) + 1))

        return [gists[i - 1] for i in sorted(indices) if 1 <= i <= len(gists)]

    def _extract_evidence_parallel(
        self,
        chunks: List[Document],
        relevant_gists: List[DocumentGist],
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Extrae evidencias finas por documento en paralelo (map)."""
        from concurrent.futures import ThreadPoolExecutor, as_completed
        from collections import defaultdict

        # Mapear chunks por file_name
        docs_by_file: Dict[str, List[Document]] = defaultdict(list)
        for doc in chunks:
            src = doc.metadata.get("source") or doc.metadata.get("file_name") or "documento"
            docs_by_file[src].append(doc)

        # Limitar a los documentos marcados como relevantes
        relevant_names = {g.file_name for g in relevant_gists} if relevant_gists else set(docs_by_file.keys())

        def _extract_for_file(file_name: str, docs_for_file: List[Document]) -> Tuple[str, List[Dict[str, Any]]]:
            # Tomar contexto moderado para extracción estructurada
            parts = []
            max_chars = 6000
            total_chars = 0
            for d in docs_for_file[:40]:
                if total_chars >= max_chars:
                    break
                piece = d.page_content[:400]
                parts.append(piece)
                total_chars += len(piece)
            context = "\n\n".join(parts)

            prompt = f"""Analiza el siguiente documento y extrae evidencias estructuradas
para un análisis empresarial profesional (contratos, informes, políticas,
manuales, etc.).

DOCUMENTO: {file_name}

CONTENIDO MUESTRA (parcial):
{context}

Devuelve SOLO JSON con el siguiente formato:
{{
  "key_risks": [
    {{"title": "...", "description": "...", "severity": "alta|media|baja"}}
  ],
  "opportunities": [
    {{"title": "...", "description": "...", "impact": "alto|medio|bajo"}}
  ],
  "important_clauses": [
    {{"title": "...", "description": "..."}}
  ],
  "entities": ["Empresa X", "Cliente Y", ...],
  "topics": ["compliance", "ventas", ...]
}}"""

            try:
                raw = self.fast_llm.invoke(prompt).content.strip()
                if raw.startswith("```json"):
                    raw = raw.replace("```json", "").replace("```", "").strip()
                elif raw.startswith("```"):
                    raw = raw.replace("```", "").strip()
                data = json.loads(raw)
                return file_name, [data]
            except Exception:
                # Fallback: devolver evidencia básica a partir de texto
                basic = {
                    "key_risks": [],
                    "opportunities": [],
                    "important_clauses": [],
                    "entities": [],
                    "topics": [],
                    "raw_excerpt": context[:1000],
                }
                return file_name, [basic]

        evidence_by_doc: Dict[str, List[Dict[str, Any]]] = {}
        max_workers = min(8, len(relevant_names) or 1)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(_extract_for_file, name, docs_by_file.get(name, [])): name
                for name in relevant_names
                if docs_by_file.get(name)
            }
            for future in as_completed(futures):
                file_name, evidences = future.result()
                evidence_by_doc[file_name] = evidences

        return evidence_by_doc

    def _synthesize_mdp_context(
        self,
        evidence_by_doc: Dict[str, List[Dict[str, Any]]],
        comparative: Optional[ComparativeAnalysis],
    ) -> Tuple[str, str]:
        """
        Reduce (synthesis) de todas las evidencias y del análisis comparativo
        a un contexto compacto tipo "knowledge chain" para el LLM principal.
        """
        # Construir una representación de alto nivel
        items = []
        for file_name, evidences in evidence_by_doc.items():
            for ev in evidences:
                items.append(
                    {
                        "file_name": file_name,
                        "key_risks": ev.get("key_risks", []),
                        "opportunities": ev.get("opportunities", []),
                        "important_clauses": ev.get("important_clauses", []),
                        "entities": ev.get("entities", []),
                        "topics": ev.get("topics", []),
                    }
                )

        mdp_context = json.dumps(
            {
                "documents": items,
                "comparative": (
                    {
                        "common_themes": comparative.common_themes,
                        "statistics": comparative.statistics,
                    }
                    if comparative
                    else None
                ),
            },
            ensure_ascii=False,
        )

        # Pedir un resumen corto del propio contexto MDP (para mostrar en streaming)
        prompt = f"""Eres un orquestador de conocimiento empresarial.

Se te entrega un CONTEXTO MDP ya estructurado (JSON) con:
- evidencias por documento (riesgos, oportunidades, cláusulas clave)
- análisis comparativo (temas comunes, estadísticas)

Tu tarea:
- generar un resumen ULTRA compacto (5–7 bullets) explicando
  qué hizo el sistema y qué encontró a alto nivel.

CONTEXTO MDP (JSON):
{mdp_context}

Devuelve SOLO texto en Markdown (sin JSON)."""

        try:
            summary = self.fast_llm.invoke(prompt).content.strip()
        except Exception:
            summary = "- Contexto MDP generado (no se pudo producir resumen breve)."

        return mdp_context, summary

    def _auto_detect_from_mdp_context(self, mdp_context: str) -> Dict[str, List[Dict[str, Any]]]:
        """Detección automática de problemas/oportunidades/patrones sobre el contexto MDP ya reducido."""
        prompt = f"""Eres un motor de detección automática de riesgos y oportunidades.

Analiza el siguiente CONTEXTO MDP (JSON) y detecta:
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
      "source": "documento o conjunto de documentos",
      "recommendation": "acción recomendada"
    }}
  ],
  "opportunities": [
    {{
      "type": "tipo de oportunidad",
      "impact": "alto|medio|bajo",
      "description": "...",
      "source": "documento o conjunto de documentos",
      "action": "acción sugerida"
    }}
  ],
  "patterns": [
    {{
      "type": "tipo de patrón",
      "description": "...",
      "frequency": "alta|media|baja",
      "implication": "qué implica para el negocio"
    }}
  ]
}}

CONTEXTO MDP:
{mdp_context}"""

        try:
            raw = self.fast_llm.invoke(prompt).content.strip()
            if raw.startswith("```json"):
                raw = raw.replace("```json", "").replace("```", "").strip()
            elif raw.startswith("```"):
                raw = raw.replace("```", "").strip()
            return json.loads(raw)
        except Exception:
            return {"problems": [], "opportunities": [], "patterns": []}

    def _generate_executive_report(
        self,
        mdp_context: str,
        detection_results: Dict[str, Any],
    ) -> str:
        """Informe ejecutivo final tipo consultor sobre el contexto MDP + detecciones."""
        prompt = f"""Actúa como consultor senior para empresas (nivel board).

Se te entrega:
- Un CONTEXTO MDP (JSON) con evidencias y análisis comparativo
- Resultados de detección automática de problemas y oportunidades

Tu tarea:
- Redactar un INFORME EJECUTIVO profesional en español para un CEO/C-level.
- Estructura sugerida:
  1. Resumen ejecutivo (2–3 párrafos)
  2. Principales riesgos y problemas (bullets)
  3. Principales oportunidades (bullets)
  4. Patrones y aprendizajes transversales
  5. Recomendaciones accionables en 30/60/90 días

CONTEXTO MDP:
{mdp_context}

DETECCIONES AUTOMÁTICAS:
{json.dumps(detection_results, ensure_ascii=False)}
"""

        try:
            report = self.reasoning_llm.invoke(prompt).content.strip()
        except Exception as e:
            report = f"⚠️ No se pudo generar informe ejecutivo completo. Error: {str(e)}"
        return report

    def _save_to_memory_mdp(
        self,
        mdp_context: str,
        detection_results: Dict[str, Any],
    ) -> None:
        """Guarda el contexto MDP y hallazgos clave en la memoria persistente."""
        if not self.context_manager:
            return

        # Guardar snapshot del contexto MDP
        self.context_manager.add_query(
            query="Snapshot contexto MDP Enterprise API",
            answer=mdp_context[:8000],
            sources=[],
            metadata={"type": "mdp_snapshot"},
        )

        # Guardar problemas y oportunidades como memorias discretas
        for problem in detection_results.get("problems", []):
            self.context_manager.add_query(
                query=f"Problema MDP: {problem.get('type', 'desconocido')}",
                answer=problem.get("description", ""),
                sources=[problem.get("source", "")] if problem.get("source") else [],
                metadata={
                    "type": "mdp_detection",
                    "detection_type": "problem",
                    "severity": problem.get("severity", "media"),
                },
            )

        for opp in detection_results.get("opportunities", []):
            self.context_manager.add_query(
                query=f"Oportunidad MDP: {opp.get('type', 'desconocido')}",
                answer=opp.get("description", ""),
                sources=[opp.get("source", "")] if opp.get("source") else [],
                metadata={
                    "type": "mdp_detection",
                    "detection_type": "opportunity",
                    "impact": opp.get("impact", "medio"),
                },
            )


