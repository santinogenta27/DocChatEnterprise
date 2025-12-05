"""Data Sight Mode - Clon de Enterprise API para análisis de datos e insights.

Este modo hereda TODO el comportamiento de `EnterpriseAPIMode`, pero está
optimizado para análisis de datos, visualización de insights y generación
de reportes analíticos.
"""

from __future__ import annotations

from typing import Iterator, List, Dict, Any, Optional

from .enterprise_api import EnterpriseAPIMode
from .data_sight_automation import DataSightAutomation


class DataSightMode(EnterpriseAPIMode):
    """
    Modo Data Sight: clon del Modo Enterprise API.

    - Mantiene exactamente la misma lógica de procesamiento que `EnterpriseAPIMode`
    - Optimizado para análisis de datos, visualización e insights
    - Enfocado en transformar documentos en información accionable y métricas
    """

    def __init__(self, config, provider: str = "openai"):
        super().__init__(config, provider=provider)
        # Data Sight se enfoca en análisis de datos e insights
        self.mode_type: str = "data_sight"
        # Sistema de automatización inteligente
        self.automation: Optional[DataSightAutomation] = None

    def process_enterprise_documents_streaming(
        self,
        files: List,
        auto_detect: bool = True,
        rules: Optional[List[Dict]] = None
    ) -> Iterator[str]:
        """
        Procesa documentos con streaming, añadiendo un encabezado específico
        para Data Sight, pero reutilizando TODO el pipeline base de `EnterpriseAPIMode`.
        """
        # Encabezado específico de Data Sight
        yield "## 🔍 Data Sight - Análisis de Datos e Insights\n\n"
        yield "Este modo está optimizado para:\n"
        yield "- Extracción y análisis de datos estructurados\n"
        yield "- Visualización de métricas y tendencias\n"
        yield "- Generación de insights accionables\n"
        yield "- Transformación de documentos en información cuantificable\n\n"

        # Luego delegamos TODO el procesamiento al modo Enterprise API original
        for chunk in super().process_enterprise_documents_streaming(
            files=files,
            auto_detect=auto_detect,
            rules=rules
        ):
            yield chunk

    def process_data_sight_pipeline(
        self,
        files: List,
        auto_detect: bool = True,
        rules: Optional[List[Dict]] = None,
    ) -> str:
        """
        Ejecuta el pipeline base de Enterprise API y luego genera un
        informe final adaptado para análisis de datos e insights.
        """
        # Inicializar automatización si no está inicializada
        if self.automation is None:
            self.automation = DataSightAutomation(self.config, self)
        
        # Procesar documentos con automatización inteligente
        automation_results = []
        for file in files:
            try:
                file_path = file.name if hasattr(file, 'name') else str(file)
                auto_result = self.automation.process_document_automatically(file_path)
                automation_results.append(auto_result)
            except Exception as e:
                print(f"⚠️ Error en automatización para {file}: {e}")
        
        # 1) Ejecutar pipeline base (no streaming)
        base_results = self.process_enterprise_documents(
            files=files,
            auto_detect=auto_detect,
            rules=rules,
            stream=False,
        )

        # 2) Construir informe específico para Data Sight
        lines: list[str] = []

        # Encabezado Data Sight
        lines.append("## 🔍 Data Sight - Análisis de Datos e Insights\n\n")
        lines.append(
            "Enfoque: transformación de documentos en datos estructurados, "
            "métricas cuantificables e insights accionables.\n\n"
        )

        # 3) Resumen general del procesamiento base
        docs_count = base_results.get("documents_processed", 0)
        chunks_count = base_results.get("chunks_generated", 0)
        lines.append(
            f"**Documentos procesados**: {docs_count}  \n**Chunks generados**: {chunks_count}\n\n"
        )

        # 4) Vista rápida de problemas/oportunidades
        problems = base_results.get("problems_detected", []) or []
        opportunities = base_results.get("opportunities_detected", []) or []

        # Selección simple: problemas críticos primero
        critical_problems = [
            p for p in problems if str(p.get("severity", "")).lower() == "alta"
        ]

        if critical_problems:
            lines.append("### 🔴 Alertas Críticas Detectadas\n\n")
            for p in critical_problems[:10]:
                desc = p.get("description", "")[:300]
                ptype = p.get("type", "N/A")
                src = p.get("source", "N/A")
                lines.append(f"- **{ptype}** — {desc}  \n  📄 Origen: {src}\n")
            lines.append("\n")

        if opportunities:
            lines.append("### 💡 Oportunidades de Optimización\n\n")
            for o in opportunities[:10]:
                desc = o.get("description", "")[:300]
                otype = o.get("type", "N/A")
                src = o.get("source", "N/A")
                lines.append(f"- **{otype}** — {desc}  \n  📄 Origen: {src}\n")
            lines.append("\n")

        # 5) Tabla de documentos con tipo y resumen corto
        summaries = base_results.get("summaries", {}) or {}
        if summaries:
            lines.append("### 📊 Documentos Analizados - Vista de Datos\n\n")
            lines.append(
                "| Documento | Tipo | Resumen Ejecutivo (corto) |\n"
                "|----------|------|---------------------------|\n"
            )
            for fname, sdata in list(summaries.items())[:50]:
                doc_type = sdata.get("document_type", "N/A")
                summary_short = (sdata.get("summary", "") or "").replace("\n", " ")
                if len(summary_short) > 140:
                    summary_short = summary_short[:140] + "..."
                lines.append(
                    f"| {fname} | {doc_type} | {summary_short} |\n"
                )
            lines.append("\n")

        # 6) Insights generales del pipeline base al final
        insights = base_results.get("insights", []) or []
        if insights:
            lines.append("### 📈 Insights y Métricas Generales\n\n")
            for ins in insights:
                title = ins.get("title", "Insight")
                content = ins.get("content", "")
                lines.append(f"#### {title}\n\n{content}\n\n")

        return "".join(lines)

