"""Graph-R1 - Self-improvement loop for multi-hop reasoning.

Inspirado en ideas de RL para mejorar rutas en grafos:
- Rejuega consultas
- Ajusta preferencias de paths
- Registra métricas de mejora
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class GraphR1Stats:
    total_queries: int = 0
    improved_queries: int = 0
    last_improvements: List[Dict[str, Any]] = field(default_factory=list)


class GraphR1:
    """Módulo ligero de auto-mejora para razonamiento multi-hop."""

    def __init__(self):
        self.stats = GraphR1Stats()

    def record_result(self, query: str, base_score: float, new_score: float, details: Dict[str, Any]) -> None:
        self.stats.total_queries += 1
        if new_score > base_score:
            self.stats.improved_queries += 1
            self.stats.last_improvements.append(
                {
                    "query": query,
                    "base_score": base_score,
                    "new_score": new_score,
                    "details": details,
                }
            )
            # Limitar historial
            if len(self.stats.last_improvements) > 100:
                self.stats.last_improvements = self.stats.last_improvements[-100:]

    def get_metrics(self) -> Dict[str, Any]:
        ratio = (
            float(self.stats.improved_queries) / float(self.stats.total_queries)
            if self.stats.total_queries > 0
            else 0.0
        )
        return {
            "total_queries": self.stats.total_queries,
            "improved_queries": self.stats.improved_queries,
            "improvement_ratio": ratio,
        }


__all__ = ["GraphR1", "GraphR1Stats"]


