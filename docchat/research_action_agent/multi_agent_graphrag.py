"""Multi-Agent GraphRAG Engine for Research & Action Agent.

Este módulo implementa una versión simplificada pero estructurada del
GraphRAG multi-agente descrito en:
  "Multi-Agent GraphRAG: A Text-to-Cypher Framework for Labeled Property Graphs".

Componentes:
- EntityExtractor
- RelationshipExtractor
- CypherGenerator (usa TextToCypherPipeline)
- GraphRetriever (usa GraphRAGEngine)
- MultiHopReasoner
- EvidenceRanker

La intención es ofrecer un punto de integración realista sobre el que
podamos iterar, sin bloquear el producto si el grafo no está disponible.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage
from langchain_core.language_models import BaseLanguageModel

from .graphrag_engine import GraphRAGEngine
from .text_to_cypher import TextToCypherPipeline, CypherQueryResult


@dataclass
class GraphEvidence:
    """Evidencia extraída del grafo."""

    cypher: str
    rows: List[Dict[str, Any]]
    score: float
    description: str


class EntityExtractor:
    """Extrae entidades relevantes de una pregunta usando LLM."""

    def __init__(self, llm: BaseLanguageModel):
        self.llm = llm

    def extract(self, question: str) -> List[str]:
        prompt = (
            "Extrae las entidades principales de la siguiente pregunta para un grafo de conocimiento.\n"
            "Devuelve SOLO una lista JSON de strings.\n\n"
            f"Pregunta: {question}\n"
        )
        resp = self.llm.invoke([HumanMessage(content=prompt)])
        content = getattr(resp, "content", "").strip()
        try:
            import json

            entities = json.loads(content)
            if isinstance(entities, list):
                return [str(e) for e in entities]
        except Exception:
            pass
        return []


class RelationshipExtractor:
    """Extrae relaciones candidatas entre entidades usando LLM."""

    def __init__(self, llm: BaseLanguageModel):
        self.llm = llm

    def extract(self, question: str, entities: List[str]) -> List[str]:
        if not entities:
            return []
        prompt = (
            "Dada la pregunta y la lista de entidades, propone tipos de relaciones relevantes "
            "para un grafo (ej: OWNS, HAS_CONTRACT, LOCATED_IN). Devuelve SOLO lista JSON.\n\n"
            f"Pregunta: {question}\n"
            f"Entidades: {entities}\n"
        )
        resp = self.llm.invoke([HumanMessage(content=prompt)])
        content = getattr(resp, "content", "").strip()
        try:
            import json

            rels = json.loads(content)
            if isinstance(rels, list):
                return [str(r) for r in rels]
        except Exception:
            pass
        return []


class GraphRetriever:
    """Ejecuta queries Cypher y devuelve resultados normalizados."""

    def __init__(self, graph_engine: GraphRAGEngine):
        self.graph_engine = graph_engine

    def retrieve(self, cypher: str) -> List[Dict[str, Any]]:
        return self.graph_engine.execute_cypher(cypher)


class MultiHopReasoner:
    """Realiza razonamiento multi-hop sencillo sobre el grafo."""

    def __init__(self, graph_engine: GraphRAGEngine):
        self.graph_engine = graph_engine

    def expand_from_query(self, base_cypher: str, max_hops: int = 2) -> List[str]:
        """Genera queries adicionales simples a partir de una query base.

        Esta implementación es mínima: asume que la query base produce nodos
        con alias `n` y explora vecinos hasta max_hops.
        """
        queries = [base_cypher]
        for hop in range(1, max_hops + 1):
            q = (
                f"{base_cypher}\n"
                f"WITH n\n"
                f"MATCH (n)-[r*1..{hop}]-(m)\n"
                f"RETURN n, m, r"
            )
            queries.append(q)
        return queries


class EvidenceRanker:
    """Ordena evidencias de grafo por relevancia aproximada."""

    def rank(self, evidences: List[GraphEvidence]) -> List[GraphEvidence]:
        # Por ahora, solo ordena por score descendente; en el futuro incluirá
        # longitud de paths, tipos de nodos, etc.
        return sorted(evidences, key=lambda e: e.score, reverse=True)


class MultiAgentGraphRAGEngine:
    """Orquestador multi-agente de GraphRAG."""

    def __init__(self, llm: BaseLanguageModel, graph_engine: Optional[GraphRAGEngine] = None):
        self.llm = llm
        self.graph_engine = graph_engine or GraphRAGEngine()
        self.entity_extractor = EntityExtractor(llm)
        self.relationship_extractor = RelationshipExtractor(llm)
        self.cypher_generator = TextToCypherPipeline(llm=llm, graph_engine=self.graph_engine)
        self.graph_retriever = GraphRetriever(self.graph_engine)
        self.multi_hop_reasoner = MultiHopReasoner(self.graph_engine)
        self.evidence_ranker = EvidenceRanker()

    def deep_search(self, question: str, max_hops: int = 2) -> Dict[str, Any]:
        """Ejecución completa de GraphRAG multi-agente."""
        entities = self.entity_extractor.extract(question)
        relationships = self.relationship_extractor.extract(question, entities)

        # Primera query Cypher
        cypher_result: CypherQueryResult = self.cypher_generator.run(question=question)
        evidences: List[GraphEvidence] = []

        if cypher_result.success and cypher_result.cypher:
            # Guardar evidencia de primer hop
            evidences.append(
                GraphEvidence(
                    cypher=cypher_result.cypher,
                    rows=cypher_result.rows,
                    score=1.0,
                    description="Query base generada por TextToCypherPipeline",
                )
            )

            # Expandir a multi-hop
            expanded_queries = self.multi_hop_reasoner.expand_from_query(
                base_cypher=cypher_result.cypher, max_hops=max_hops
            )
            for q in expanded_queries[1:]:
                try:
                    rows = self.graph_retriever.retrieve(q)
                except Exception:
                    rows = []
                if rows:
                    evidences.append(
                        GraphEvidence(
                            cypher=q,
                            rows=rows,
                            score=0.7,  # Score heurístico
                            description="Query multi-hop generada automáticamente",
                        )
                    )

        ranked = self.evidence_ranker.rank(evidences)
        return {
            "question": question,
            "entities": entities,
            "relationships": relationships,
            "evidences": [
                {
                    "cypher": ev.cypher,
                    "rows_preview": ev.rows[:3],
                    "score": ev.score,
                    "description": ev.description,
                }
                for ev in ranked
            ],
        }


__all__ = [
    "GraphEvidence",
    "EntityExtractor",
    "RelationshipExtractor",
    "GraphRetriever",
    "MultiHopReasoner",
    "EvidenceRanker",
    "MultiAgentGraphRAGEngine",
]


