"""GraphSearch - Deep Searching Workflow over GraphRAGEngine.

Implementa un workflow de búsqueda profunda:
- Depth-first search (DFS)
- Breadth-first search (BFS)
- Path ranking simple

Se apoya en GraphRAGEngine, pero es agnóstico al esquema concreto.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .graphrag_engine import GraphRAGEngine


@dataclass
class GraphPath:
    nodes: List[Dict[str, Any]]
    relationships: List[Dict[str, Any]]
    score: float


class GraphSearch:
    """Deep search (DFS/BFS) helper on top of GraphRAGEngine."""

    def __init__(self, graph_engine: Optional[GraphRAGEngine] = None):
        self.graph_engine = graph_engine or GraphRAGEngine()

    def dfs(self, start_id: str, max_depth: int = 2) -> List[GraphPath]:
        """Explora caminos desde un nodo dado usando DFS de profundidad limitada."""
        cypher = (
            "MATCH (start {id: $id})-[:`*`*1..$depth]-(n) "
            "WITH collect(start) + collect(n) AS nodes "
            "RETURN nodes"
        )
        # Esta query es genérica y puede requerir adaptación; en modo mock no hará nada.
        try:
            rows = self.graph_engine.execute_cypher(
                "MATCH (start {id: $id})-[r*1..$depth]-(n) RETURN start, n, r",
                {"id": start_id, "depth": max_depth},
            )
        except Exception:
            rows = []
        paths: List[GraphPath] = []
        for row in rows:
            nodes = []
            rels = []
            for n in row.get("n", []):
                if isinstance(n, dict):
                    nodes.append(n)
            for r in row.get("r", []):
                if isinstance(r, dict):
                    rels.append(r)
            if nodes or rels:
                paths.append(GraphPath(nodes=nodes, relationships=rels, score=1.0))
        return paths

    def bfs(self, start_label: str, max_depth: int = 2, limit: int = 50) -> List[GraphPath]:
        """Exploración BFS aproximada a partir de un label."""
        try:
            rows = self.graph_engine.execute_cypher(
                """
                MATCH (n:{label})
                WITH n LIMIT $limit
                MATCH p = (n)-[r*1..$depth]-(m)
                RETURN nodes(p) AS nodes, relationships(p) AS rels
                """.format(
                    label=start_label
                ),
                {"depth": max_depth, "limit": limit},
            )
        except Exception:
            rows = []
        paths: List[GraphPath] = []
        for row in rows:
            nodes = row.get("nodes", [])
            rels = row.get("rels", [])
            if nodes or rels:
                paths.append(GraphPath(nodes=nodes, relationships=rels, score=1.0))
        return paths

    def rank_paths(self, paths: List[GraphPath]) -> List[GraphPath]:
        """Ordena paths por score (actualmente trivial)."""
        return sorted(paths, key=lambda p: p.score, reverse=True)


__all__ = ["GraphSearch", "GraphPath"]


