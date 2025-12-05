"""MDP-Agent style wrapper over SemanticDataEngine for the R&A Agent.

Este módulo implementa una versión simplificada de MDP-Agent:

- Usa SemanticDataEngine como backend de documentos.
- Construye "gist memories" (resúmenes + tópicos) por documento.
- Implementa búsqueda híbrida (vector + BM25/histórico) y síntesis tipo map-reduce.

La idea no es reemplazar toda la lógica de SemanticDataEngine, sino
envolverla con capacidades más agentic para el Research & Action Agent.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import json
from pathlib import Path

from langchain_core.messages import HumanMessage

from docchat.semantic_data_engine import SemanticDataEngine, SemanticDocument


@dataclass
class GistMemory:
    """Gist / resumen de alto nivel de un documento."""

    doc_id: str
    summary: str
    topics: List[str]
    source_path: str


class MDPAgent:
    """Lightweight MDP-Agent wrapper around SemanticDataEngine."""

    def __init__(self, semantic_engine: SemanticDataEngine):
        self.semantic_engine = semantic_engine
        self.config = semantic_engine.config
        self.llm = semantic_engine.llm

        self.data_dir = self.config.base_path / "semantic_data"
        self.gist_file = self.data_dir / "gist_memories.json"
        self._gists: Dict[str, GistMemory] = {}
        self._load_gists()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load_gists(self) -> None:
        if self.gist_file.exists():
            try:
                with open(self.gist_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for doc_id, g in data.items():
                    self._gists[doc_id] = GistMemory(
                        doc_id=doc_id,
                        summary=g.get("summary", ""),
                        topics=g.get("topics", []),
                        source_path=g.get("source_path", ""),
                    )
            except Exception as e:  # pragma: no cover - IO errors
                print(f"[MDP-Agent] Error cargando gist memories: {e}")

    def _save_gists(self) -> None:
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            data = {
                doc_id: {
                    "summary": g.summary,
                    "topics": g.topics,
                    "source_path": g.source_path,
                }
                for doc_id, g in self._gists.items()
            }
            with open(self.gist_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:  # pragma: no cover - IO errors
            print(f"[MDP-Agent] Error guardando gist memories: {e}")

    # ------------------------------------------------------------------
    # Gist creation
    # ------------------------------------------------------------------

    def build_gist_for_document(self, doc: SemanticDocument, force: bool = False) -> GistMemory:
        """Create or update gist memory for a single document."""
        if doc.doc_id in self._gists and not force:
            return self._gists[doc.doc_id]

        # If no LLM available, fallback to simple heuristic
        if not self.llm:
            text = doc.content[:2000]
            summary = (text[:500] + "...") if len(text) > 500 else text
            topics = []
        else:
            prompt = (
                "Eres un analista de documentos para un sistema de RAG.\n"
                "Recibirás el contenido de un documento y debes devolver un JSON con:\n"
                "{\n"
                '  "summary": "resumen en 3-5 frases",\n'
                '  "topics": ["tema1", "tema2", ...]\n'
                "}\n"
                "Documento:\n"
                f"{doc.content[:4000]}\n\n"
                "Devuelve SOLO el JSON, sin texto adicional."
            )
            response = self.llm.invoke([HumanMessage(content=prompt)])
            content = getattr(response, "content", "").strip()
            try:
                parsed = json.loads(content)
                summary = parsed.get("summary", "")
                topics = parsed.get("topics", [])
            except Exception:
                text = doc.content[:2000]
                summary = (text[:500] + "...") if len(text) > 500 else text
                topics = []

        gist = GistMemory(
            doc_id=doc.doc_id,
            summary=summary,
            topics=topics,
            source_path=doc.source_path,
        )
        self._gists[doc.doc_id] = gist
        self._save_gists()
        return gist

    def ensure_all_gists(self) -> None:
        """Ensure all current documents have gist memories."""
        for doc in self.semantic_engine.documents.values():
            if doc.doc_id not in self._gists:
                self.build_gist_for_document(doc)

    # ------------------------------------------------------------------
    # Hybrid search + map-reduce style synthesis
    # ------------------------------------------------------------------

    def search(self, query: str, k: int = 10) -> Dict[str, Any]:
        """Hybrid search using SemanticDataEngine + gist memories.

        Returns:
            {
              "results": [
                 {"doc_id", "summary", "topics", "score", "metadata"...},
                 ...
              ]
            }
        """
        # Ensure there is a vector store built
        if not self.semantic_engine.vector_store:
            # Try to build on the fly
            try:
                self.semantic_engine._load_vector_store()
            except Exception as e:  # pragma: no cover
                print(f"[MDP-Agent] Error inicializando vector store: {e}")

        # 1) Vector search (SemanticDataEngine already handles vector store)
        matched_docs: List[Tuple[SemanticDocument, float]] = []
        if self.semantic_engine.vector_store:
            try:
                # Vector store similarity search
                results = self.semantic_engine.vector_store.similarity_search_with_score(query, k=k)
                for doc, score in results:
                    doc_id = doc.metadata.get("doc_id")
                    if not doc_id:
                        continue
                    sem_doc = self.semantic_engine.documents.get(doc_id)
                    if sem_doc:
                        matched_docs.append((sem_doc, float(score)))
            except Exception as e:  # pragma: no cover
                print(f"[MDP-Agent] Error en búsqueda vectorial: {e}")

        # 2) Fallback: simple keyword search over gist summaries if no results
        if not matched_docs and self._gists:
            q_lower = query.lower()
            for doc_id, gist in self._gists.items():
                score = 0.0
                if any(t.lower() in q_lower for t in gist.topics):
                    score += 1.0
                if any(word in gist.summary.lower() for word in q_lower.split()[:5]):
                    score += 0.5
                if score > 0:
                    sem_doc = self.semantic_engine.documents.get(doc_id)
                    if sem_doc:
                        matched_docs.append((sem_doc, score))
            # Sort by score desc
            matched_docs.sort(key=lambda x: x[1], reverse=True)
            matched_docs = matched_docs[:k]

        # Build response
        results_payload: List[Dict[str, Any]] = []
        for doc, score in matched_docs:
            gist = self._gists.get(doc.doc_id) or self.build_gist_for_document(doc)
            payload: Dict[str, Any] = {
                "doc_id": doc.doc_id,
                "summary": gist.summary,
                "topics": gist.topics,
                "score": float(score),
                "metadata": doc.metadata,
                "source_path": doc.source_path,
            }
            results_payload.append(payload)

        return {"results": results_payload}

    def synthesize_answer(self, query: str, k: int = 10) -> Dict[str, Any]:
        """Map-reduce style synthesis over top-k documents for a query.

        This is the high-level entry point that the Research & Action Agent
        can use as an MDP-style retrieval + synthesis primitive.
        """
        search_result = self.search(query, k=k)
        docs = search_result.get("results", [])

        if not self.llm or not docs:
            # Best-effort fallback
            return {
                "summary": "No se encontraron documentos relevantes o no hay LLM configurado.",
                "sources": docs,
                "log": [],
            }

        # Map: build small snippets per document
        snippets = []
        for d in docs:
            snippet = f"- {d.get('source_path', d['doc_id'])}: {d.get('summary', '')}"
            snippets.append(snippet)

        map_text = "\n".join(snippets)
        reduce_prompt = (
            "Eres un agente de síntesis de información.\n"
            "Has recibido fragmentos relevantes de varios documentos (formato lista).\n"
            "Tu tarea es:\n"
            "1) Responder a la pregunta del usuario.\n"
            "2) Explicar brevemente la lógica.\n"
            "3) Listar qué documentos usaste.\n\n"
            f"Pregunta del usuario: {query}\n\n"
            f"Fragmentos:\n{map_text}\n\n"
            "Responde en formato JSON con claves:\n"
            "{\n"
            '  "summary": "...",\n'
            '  "reasoning": "...",\n'
            '  "sources_used": ["doc_id_1", "doc_id_2", ...]\n'
            "}\n"
            "Devuelve SOLO el JSON."
        )
        response = self.llm.invoke([HumanMessage(content=reduce_prompt)])
        content = getattr(response, "content", "").strip()
        try:
            parsed = json.loads(content)
        except Exception:
            parsed = {
                "summary": content,
                "reasoning": "",
                "sources_used": [d["doc_id"] for d in docs[:5]],
            }

        return {
            "summary": parsed.get("summary", ""),
            "reasoning": parsed.get("reasoning", ""),
            "sources": docs,
            "sources_used": parsed.get("sources_used", []),
        }


__all__ = ["MDPAgent", "GistMemory"]


