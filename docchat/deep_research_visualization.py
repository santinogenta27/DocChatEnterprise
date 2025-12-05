"""
Visualization Agent para Deep Research.

Este módulo proporciona un agente ligero de visualización que genera
gráficos simples (por ahora, un gráfico de barras dummy) y devuelve
las rutas de los archivos de imagen para que luego se incrusten en
los reportes de Deep Research.

El objetivo es tener un "Visualization Agent" dedicado, integrable
en el flujo sin añadir complejidad excesiva.
"""

from __future__ import annotations

from pathlib import Path
from typing import List

import matplotlib.pyplot as plt  # type: ignore


class VisualizationAgent:
    """
    Agente de visualización muy simple para Deep Research.

    En esta primera versión genera un gráfico de barras dummy que
    puede usarse como placeholder visual en los reportes.
    """

    def __init__(self, base_dir: Path) -> None:
        self.base_dir = Path(base_dir)
        self.charts_dir = self.base_dir / "charts"
        self.charts_dir.mkdir(parents=True, exist_ok=True)

    def generate_placeholder_charts(self, count: int = 1) -> List[Path]:
        """
        Genera uno o varios gráficos de ejemplo y devuelve las rutas.

        Args:
            count: número de gráficos a generar (máx. 3 para evitar ruido).
        """
        paths: List[Path] = []
        count = max(1, min(count, 3))

        for idx in range(count):
            fig, ax = plt.subplots(figsize=(4, 3))
            ax.bar(["A", "B", "C"], [3, 5, 2], color="#4B9CD3")
            ax.set_title("Deep Research - Visualización de ejemplo")
            ax.set_ylabel("Valor relativo")
            file_path = self.charts_dir / f"deep_research_chart_{idx+1}.png"
            fig.tight_layout()
            fig.savefig(file_path)
            plt.close(fig)
            paths.append(file_path)

        return paths


__all__ = ["VisualizationAgent"]



