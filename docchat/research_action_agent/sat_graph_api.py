"""SAT-Graph API - Deterministic primitives for legal reasoning.

Este módulo implementa una versión simplificada y extensible de la
API de primitivas descrita en el paper de SAT-Graph:

- resolve_item_reference
- get_valid_version
- get_text_for_version
- get_item_history
- trace_causality
- compare_versions

La implementación está pensada para dos modos:
- Modo real: usa GraphRAGEngine + un modelo de grafo SAT-Graph
  (Neo4j/Memgraph) con nodos Item/Version/Action/TextUnit.
- Modo mock: devuelve resultados deterministas para tests y demos.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import json

from .graphrag_engine import GraphRAGEngine


@dataclass
class SATGraphConfig:
    """Configuration for SAT-Graph API."""

    use_mock: bool = False


@dataclass
class VersionInfo:
    version_id: str
    item_id: str
    valid_from: str
    valid_to: Optional[str]


@dataclass
class ActionInfo:
    action_id: str
    type: str
    date: str
    source_version: str
    terminates_version: Optional[str]
    produces_version: Optional[str]


class SATGraphAPI:
    """Deterministic primitives on top of a SAT-Graph-like property graph."""

    def __init__(self, graph_engine: Optional[GraphRAGEngine] = None, config: Optional[SATGraphConfig] = None):
        self.graph_engine = graph_engine or GraphRAGEngine()
        self.config = config or SATGraphConfig(use_mock=self.graph_engine.is_mock)

    # ------------------------------------------------------------------
    # Discovery (probabilistic-ish but auditable)
    # ------------------------------------------------------------------

    def resolve_item_reference(self, reference_text: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Resolve a natural language reference (e.g. 'Artículo 6 de la Constitución').

        Returns a ranked list of candidate items:
        [{"item_id": "...", "label": "...", "confidence": 0.95}, ...]
        """
        if self.config.use_mock:
            # Minimal deterministic stub
            return [
                {"item_id": "item_const_art_6", "label": "Artículo 6 de la Constitución", "confidence": 0.98},
            ]

        # Example query – assumes an Item node with label + fullText / name fields.
        query = """
        MATCH (i:Item)
        WHERE toLower(i.label) CONTAINS toLower($q)
           OR toLower(i.name) CONTAINS toLower($q)
        RETURN i.itemId AS item_id, i.label AS label
        LIMIT $top_k
        """
        rows = self.graph_engine.execute_cypher(query, {"q": reference_text, "top_k": top_k})
        # For now assign a simple confidence heuristic
        results = []
        for idx, row in enumerate(rows):
            results.append(
                {
                    "item_id": row.get("item_id"),
                    "label": row.get("label"),
                    "confidence": 1.0 - idx * 0.1,
                }
            )
        return results

    # ------------------------------------------------------------------
    # Deterministic primitives
    # ------------------------------------------------------------------

    def get_valid_version(self, item_id: str, timestamp: str) -> Optional[VersionInfo]:
        """Return the Version that was valid for an Item on a given timestamp."""
        if self.config.use_mock:
            # Very small deterministic behaviour
            if item_id == "item_const_art_6":
                return VersionInfo(
                    version_id="ver_const_art_6_2001",
                    item_id=item_id,
                    valid_from="2000-02-14",
                    valid_to=None,
                )
            return None

        query = """
        MATCH (v:Version)-[:VERSION_OF]->(i:Item {itemId: $item_id})
        WHERE v.validFrom <= datetime($ts)
          AND (v.validTo IS NULL OR v.validTo >= datetime($ts))
        RETURN v.versionId AS version_id, i.itemId AS item_id,
               toString(v.validFrom) AS valid_from,
               CASE WHEN v.validTo IS NULL THEN NULL ELSE toString(v.validTo) END AS valid_to
        ORDER BY v.validFrom DESC
        LIMIT 1
        """
        rows = self.graph_engine.execute_cypher(query, {"item_id": item_id, "ts": timestamp})
        if not rows:
            return None
        row = rows[0]
        return VersionInfo(
            version_id=row.get("version_id"),
            item_id=row.get("item_id"),
            valid_from=row.get("valid_from"),
            valid_to=row.get("valid_to"),
        )

    def get_text_for_version(self, version_id: str, language: str = "es") -> Optional[str]:
        """Return canonical text for a Version."""
        if self.config.use_mock:
            if version_id == "ver_const_art_6_2001":
                return (
                    "Todos tienen derecho a la educación, la salud, el trabajo, la vivienda, "
                    "el ocio, la seguridad social y la protección de la maternidad y la infancia."
                )
            return None

        query = """
        MATCH (t:TextUnit)-[:TEXT_OF]->(v:Version {versionId: $version_id})
        WHERE t.language = $lang AND t.aspect = 'canonical'
        RETURN t.content AS content
        LIMIT 1
        """
        rows = self.graph_engine.execute_cypher(query, {"version_id": version_id, "lang": language})
        if not rows:
            return None
        return rows[0].get("content")

    def get_item_history(self, item_id: str) -> List[ActionInfo]:
        """Return all Actions that affected an Item (ordered by date)."""
        if self.config.use_mock:
            if item_id == "item_const_art_6":
                return [
                    ActionInfo(
                        action_id="act_amend_26",
                        type="Amendment",
                        date="2000-02-14",
                        source_version="ver_const_amend_26",
                        terminates_version=None,
                        produces_version="ver_const_art_6_2001",
                    )
                ]
            return []

        query = """
        MATCH (a:Action)-[:AFFECTS]->(v:Version)-[:VERSION_OF]->(i:Item {itemId: $item_id})
        RETURN a.actionId AS action_id,
               a.type AS type,
               toString(a.date) AS date,
               a.sourceVersion AS source_version,
               a.terminatesVersion AS terminates_version,
               a.producesVersion AS produces_version
        ORDER BY a.date ASC
        """
        rows = self.graph_engine.execute_cypher(query, {"item_id": item_id})
        actions: List[ActionInfo] = []
        for row in rows:
            actions.append(
                ActionInfo(
                    action_id=row.get("action_id"),
                    type=row.get("type"),
                    date=row.get("date"),
                    source_version=row.get("source_version"),
                    terminates_version=row.get("terminates_version"),
                    produces_version=row.get("produces_version"),
                )
            )
        return actions

    def trace_causality(self, version_id: str) -> Dict[str, Optional[ActionInfo]]:
        """Trace the action that created and terminated a Version."""
        if self.config.use_mock:
            if version_id == "ver_const_art_6_2001":
                creator = ActionInfo(
                    action_id="act_amend_26",
                    type="Amendment",
                    date="2000-02-14",
                    source_version="ver_const_amend_26",
                    terminates_version=None,
                    produces_version=version_id,
                )
                return {"creating_action": creator, "terminating_action": None}
            return {"creating_action": None, "terminating_action": None}

        query = """
        MATCH (a:Action)
        WHERE a.producesVersion = $version_id OR a.terminatesVersion = $version_id
        RETURN a.actionId AS action_id,
               a.type AS type,
               toString(a.date) AS date,
               a.sourceVersion AS source_version,
               a.terminatesVersion AS terminates_version,
               a.producesVersion AS produces_version
        """
        rows = self.graph_engine.execute_cypher(query, {"version_id": version_id})
        creating: Optional[ActionInfo] = None
        terminating: Optional[ActionInfo] = None
        for row in rows:
            info = ActionInfo(
                action_id=row.get("action_id"),
                type=row.get("type"),
                date=row.get("date"),
                source_version=row.get("source_version"),
                terminates_version=row.get("terminates_version"),
                produces_version=row.get("produces_version"),
            )
            if info.produces_version == version_id:
                creating = info
            if info.terminates_version == version_id:
                terminating = info
        return {"creating_action": creating, "terminating_action": terminating}

    def compare_versions(self, version_id_a: str, version_id_b: str, language: str = "es") -> Dict[str, Any]:
        """Return a simple textual diff between two versions.

        For now this is a very lightweight implementation that computes a
        line-based diff. In a production setting you would want a much
        richer, structure-aware diff as en el paper.
        """
        text_a = self.get_text_for_version(version_id_a, language=language) or ""
        text_b = self.get_text_for_version(version_id_b, language=language) or ""

        if not text_a and not text_b:
            return {
                "status": "error",
                "message": "No se pudo obtener texto para ninguna de las versiones.",
            }

        import difflib

        diff_lines = list(
            difflib.unified_diff(
                text_a.splitlines(),
                text_b.splitlines(),
                fromfile=version_id_a,
                tofile=version_id_b,
                lineterm="",
            )
        )

        return {
            "status": "ok",
            "version_a": version_id_a,
            "version_b": version_id_b,
            "diff": diff_lines,
        }


__all__ = ["SATGraphAPI", "SATGraphConfig", "VersionInfo", "ActionInfo"]


