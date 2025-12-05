"""CLAUSE - Neuro-Symbolic Reasoning layer for R&A Agent.

Proporciona:
- Dynamic context engineering
- Step constraints (reglas)
- Explanation trees
- Provenance tracking
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from langchain_core.language_models import BaseLanguageModel
from langchain_core.messages import HumanMessage


@dataclass
class ExplanationNode:
    step: str
    description: str
    children: List["ExplanationNode"] = field(default_factory=list)
    sources: List[Dict[str, Any]] = field(default_factory=list)


class CLAUSEReasoner:
    """Capa neuro-simbólica ligera."""

    def __init__(self, llm: BaseLanguageModel):
        self.llm = llm

    def build_explanation_tree(
        self, question: str, evidences: List[Dict[str, Any]], actions: Optional[List[Dict[str, Any]]] = None
    ) -> ExplanationNode:
        """Construye un árbol de explicación en base a evidencias y acciones."""
        text_evidences = "\n".join(str(e) for e in evidences[:10])
        text_actions = "\n".join(str(a) for a in (actions or [])[:10])
        prompt = (
            "Eres un sistema de razonamiento explicable.\n"
            "Debes generar una explicación en pasos de cómo se llegó a una conclusión,\n"
            "dado un conjunto de evidencias y acciones.\n\n"
            f"Pregunta: {question}\n\n"
            f"Evidencias (resumen JSON):\n{text_evidences}\n\n"
            f"Acciones (si las hay):\n{text_actions}\n\n"
            "Devuelve SOLO un JSON con estructura:\n"
            "{\n"
            '  "step": "texto",\n'
            '  "description": "texto",\n'
            '  "children": [ ... ]\n'
            "}\n"
        )
        resp = self.llm.invoke([HumanMessage(content=prompt)])
        content = getattr(resp, "content", "").strip()
        try:
            import json

            data = json.loads(content)
            return self._from_dict(data)
        except Exception:
            return ExplanationNode(step="root", description=content)

    def _from_dict(self, data: Dict[str, Any]) -> ExplanationNode:
        node = ExplanationNode(
            step=str(data.get("step", "")),
            description=str(data.get("description", "")),
            sources=data.get("sources", []) or [],
        )
        for child in data.get("children", []) or []:
            node.children.append(self._from_dict(child))
        return node


__all__ = ["CLAUSEReasoner", "ExplanationNode"]


