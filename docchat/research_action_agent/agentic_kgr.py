"""Agentic-KGR - Co-evolutionary Knowledge Graph Construction (simplificado).

Basado en la idea de:
  "Agentic-KGR: Co-evolutionary Knowledge Graph Construction through Multi-Agent RL"

Objetivo:
- Proveer una interfaz para que el R&A Agent pueda:
  - detectar obsolescencia en el grafo,
  - proponer actualizaciones,
  - aplicar cambios (de forma controlada).

La implementación aquí es un esqueleto seguro:
- No altera el grafo si no se llama explícitamente a `apply_updates`.
- Se apoya en GraphRAGEngine para inspeccionar el grafo actual.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from langchain_core.language_models import BaseLanguageModel
from langchain_core.messages import HumanMessage

from .graphrag_engine import GraphRAGEngine


@dataclass
class GraphUpdateProposal:
    """Propuesta de actualización de grafo."""

    action: str  # "add_node", "add_edge", "update_prop", "delete"
    payload: Dict[str, Any]
    reason: str
    confidence: float


class AgenticKGR:
    """Co-evolutionary KGR manager."""

    def __init__(self, llm: BaseLanguageModel, graph_engine: Optional[GraphRAGEngine] = None):
        self.llm = llm
        self.graph_engine = graph_engine or GraphRAGEngine()

    # ------------------------------------------------------------------
    # Detección de obsolescencia
    # ------------------------------------------------------------------

    def detect_obsolescence(self, context_description: str) -> List[GraphUpdateProposal]:
        """Analiza el contexto y propone cambios al grafo."""
        prompt = (
            "Eres un agente de mantenimiento de grafos de conocimiento.\n"
            "Recibirás una descripción de cambios recientes en la realidad o en la normativa,\n"
            "y debes proponer actualizaciones al grafo.\n"
            "Devuelve SOLO una lista JSON de objetos con:\n"
            '{ "action": "...", "payload": {...}, "reason": "...", "confidence": 0.0-1.0 }\n\n'
            f"Contexto:\n{context_description}\n"
        )
        resp = self.llm.invoke([HumanMessage(content=prompt)])
        content = getattr(resp, "content", "").strip()
        try:
            import json

            data = json.loads(content)
            proposals: List[GraphUpdateProposal] = []
            if isinstance(data, list):
                for item in data:
                    proposals.append(
                        GraphUpdateProposal(
                            action=str(item.get("action", "")),
                            payload=item.get("payload", {}) or {},
                            reason=str(item.get("reason", "")),
                            confidence=float(item.get("confidence", 0.0)),
                        )
                    )
            return proposals
        except Exception:
            return []

    # ------------------------------------------------------------------
    # Aplicación de cambios (opcional)
    # ------------------------------------------------------------------

    def apply_updates(self, proposals: List[GraphUpdateProposal], min_confidence: float = 0.8) -> List[Dict[str, Any]]:
        """Aplica propuestas de actualización que superen el umbral de confianza.

        IMPORTANTE:
        - Esta implementación es deliberadamente conservadora.
        - Por defecto, devuelve las queries que se ejecutarían SIN ejecutarlas.
        - Para activar escrituras reales, se debería añadir un flag explícito y
          revisar exhaustivamente las acciones.
        """
        applied: List[Dict[str, Any]] = []
        for p in proposals:
            if p.confidence < min_confidence:
                continue
            # Construir query Cypher aproximada (NO se ejecuta aquí)
            cypher = self._build_update_cypher(p)
            applied.append(
                {
                    "action": p.action,
                    "payload": p.payload,
                    "reason": p.reason,
                    "confidence": p.confidence,
                    "cypher": cypher,
                }
            )
        return applied

    def _build_update_cypher(self, proposal: GraphUpdateProposal) -> str:
        """Construye una query Cypher aproximada para la propuesta."""
        action = proposal.action
        payload = proposal.payload
        if action == "add_node":
            label = payload.get("label", "Entity")
            props = payload.get("properties", {})
            props_str = ", ".join(f"{k}: '{v}'" for k, v in props.items())
            return f"CREATE (n:{label} {{{props_str}}})"
        if action == "add_edge":
            rel = payload.get("type", "RELATES_TO")
            from_id = payload.get("from_id")
            to_id = payload.get("to_id")
            return (
                "MATCH (a),(b) "
                f"WHERE a.id = '{from_id}' AND b.id = '{to_id}' "
                f"CREATE (a)-[:{rel}]->(b)"
            )
        if action == "update_prop":
            node_id = payload.get("id")
            key = payload.get("key")
            value = payload.get("value")
            return f"MATCH (n) WHERE n.id = '{node_id}' SET n.{key} = '{value}'"
        if action == "delete":
            node_id = payload.get("id")
            return f"MATCH (n) WHERE n.id = '{node_id}' DETACH DELETE n"
        return ""


__all__ = ["AgenticKGR", "GraphUpdateProposal"]


