"""Stargate PDF Mode - Clon de Enterprise API para procesamiento masivo de PDFs.

Este modo hereda TODO el comportamiento de `EnterpriseAPIMode`, pero permite
anotar un tipo de pipeline de negocio (legal, crédito, seguros, etc.) para
personalizar el encabezado y el contexto sin romper la lógica base.
"""

from __future__ import annotations

from typing import Iterator, List, Dict, Any, Optional

from .enterprise_api import EnterpriseAPIMode


class StargatePDFMode(EnterpriseAPIMode):
    """
    Modo Stargate PDF: clon del Modo Enterprise API.

    - Mantiene exactamente la misma lógica de procesamiento que `EnterpriseAPIMode`
    - Añade un campo `pipeline_type` para seleccionar distintos "pipelines de negocio"
      (Due Diligence Legal, Análisis Crediticio, Procesamiento de Reclamaciones, etc.)
    - El pipeline base (ingesta → resúmenes → detección → reglas → insights → memoria)
      permanece intacto.
    """

    def __init__(self, config, provider: str = "openai"):
        super().__init__(config, provider=provider)
        # Tipo de pipeline de negocio seleccionado desde la UI (string simple)
        self.pipeline_type: str = "general"

    def process_enterprise_documents_streaming(
        self,
        files: List,
        auto_detect: bool = True,
        rules: Optional[List[Dict]] = None
    ) -> Iterator[str]:
        """
        Procesa documentos con streaming, añadiendo un encabezado específico
        según el pipeline de negocio seleccionado, pero reutilizando TODO el
        pipeline base de `EnterpriseAPIMode`.
        """
        # Encabezado previo según pipeline_type
        pipeline = getattr(self, "pipeline_type", "general") or "general"

        if pipeline == "legal_due_diligence":
            yield "## 🏛️ Pipeline: Due Diligence Legal\n\n"
            yield "Este pipeline está optimizado para:\n- Contratos de fusión/adquisición\n- NDAs y cláusulas de riesgo\n- Fechas de vencimiento críticas\n\n"
        elif pipeline == "credit_analysis":
            yield "## 🏦 Pipeline: Análisis Crediticio Automatizado\n\n"
            yield "Este pipeline está optimizado para:\n- Solicitudes de préstamo\n- Estados financieros de empresas\n- Historiales crediticios y scoring de riesgo\n\n"
        elif pipeline == "insurance_claims":
            yield "## 🏥 Pipeline: Procesamiento de Reclamaciones de Seguros\n\n"
            yield "Este pipeline está optimizado para:\n- Reclamaciones\n- Facturas médicas\n- Reportes de peritos y evidencias\n\n"
        elif pipeline == "financial_audit":
            yield "## 📊 Pipeline: Auditoría Financiera\n\n"
            yield "Este pipeline está optimizado para:\n- Estados financieros\n- Notas a los estados\n- Identificación de inconsistencias y riesgos contables\n\n"
        elif pipeline == "regulatory_compliance":
            yield "## ⚖️ Pipeline: Cumplimiento Normativo\n\n"
            yield "Este pipeline está optimizado para:\n- Políticas internas\n- Normativas y regulaciones\n- Brechas de cumplimiento y riesgos regulatorios\n\n"
        elif pipeline == "ecommerce_risk":
            yield "## 🛒 Pipeline: E‑commerce / Riesgo de Transacciones\n\n"
            yield "Este pipeline está optimizado para:\n- Órdenes y facturas de e‑commerce\n- Devoluciones y reclamos\n- Detección de patrones anómalos en compras y pagos\n\n"
        elif pipeline == "hr_people":
            yield "## 👥 Pipeline: HR / People Analytics\n\n"
            yield "Este pipeline está optimizado para:\n- Evaluaciones de desempeño\n- Encuestas de clima\n- Documentos de políticas de RRHH y casos disciplinarios\n\n"
        elif pipeline == "healthcare_clinical":
            yield "## 🧬 Pipeline: Salud / Documentos Clínicos\n\n"
            yield "Este pipeline está optimizado para:\n- Informes clínicos y de laboratorio\n- Órdenes médicas\n- Protocolos y guías de tratamiento\n\n"
        elif pipeline == "manufacturing_maintenance":
            yield "## 🏭 Pipeline: Manufactura / Mantenimiento\n\n"
            yield "Este pipeline está optimizado para:\n- Reportes de mantenimiento\n- Logs de fallas\n- Manuales técnicos y boletines de servicio\n\n"
        elif pipeline == "gov_procurement_audit":
            yield "## 🏛️ Pipeline: Gobierno / Compras y Auditoría\n\n"
            yield "Este pipeline está optimizado para:\n- Pliegos y contratos de compras públicas\n- Informes de auditoría\n- Normas y resoluciones asociadas\n\n"
        else:
            # Pipeline general (el mismo que Enterprise API)
            yield "## 🌀 Pipeline General Stargate PDF (Enterprise API clone)\n\n"

        # Luego delegamos TODO el procesamiento al modo Enterprise API original
        for chunk in super().process_enterprise_documents_streaming(
            files=files,
            auto_detect=auto_detect,
            rules=rules
        ):
            yield chunk

    def process_stargate_pipeline(
        self,
        files: List,
        auto_detect: bool = True,
        rules: Optional[List[Dict]] = None,
    ) -> str:
        """
        Ejecuta el pipeline base de Enterprise API y luego genera un
        informe final adaptado al pipeline de negocio seleccionado.
        """
        # 1) Ejecutar pipeline base (no streaming)
        base_results = self.process_enterprise_documents(
            files=files,
            auto_detect=auto_detect,
            rules=rules,
            stream=False,
        )

        # 2) Construir informe específico por pipeline
        pipeline = getattr(self, "pipeline_type", "general") or "general"
        lines: list[str] = []

        # Encabezado según pipeline
        if pipeline == "legal_due_diligence":
            lines.append("## 🏛️ Pipeline: Due Diligence Legal\n")
            lines.append(
                "Enfoque: detección de cláusulas de riesgo, fechas críticas y banderas rojas en contratos.\n\n"
            )
        elif pipeline == "credit_analysis":
            lines.append("## 🏦 Pipeline: Análisis Crediticio Automatizado\n")
            lines.append(
                "Enfoque: riesgo crediticio, documentos incompletos y señales de impago.\n\n"
            )
        elif pipeline == "insurance_claims":
            lines.append("## 🏥 Pipeline: Procesamiento de Reclamaciones de Seguros\n")
            lines.append(
                "Enfoque: detección de fraude, reclamaciones críticas y tiempos de respuesta.\n\n"
            )
        elif pipeline == "financial_audit":
            lines.append("## 📊 Pipeline: Auditoría Financiera\n")
            lines.append(
                "Enfoque: inconsistencias contables, riesgos financieros y notas sensibles.\n\n"
            )
        elif pipeline == "regulatory_compliance":
            lines.append("## ⚖️ Pipeline: Cumplimiento Normativo\n")
            lines.append(
                "Enfoque: brechas de cumplimiento, obligaciones regulatorias y riesgos de sanción.\n\n"
            )
        elif pipeline == "ecommerce_risk":
            lines.append("## 🛒 Pipeline: E‑commerce / Riesgo de Transacciones\n")
            lines.append(
                "Enfoque: patrones anómalos en pedidos, devoluciones y pagos.\n\n"
            )
        elif pipeline == "hr_people":
            lines.append("## 👥 Pipeline: HR / People Analytics\n")
            lines.append(
                "Enfoque: riesgos laborales, señales en clima organizacional y documentación de RRHH.\n\n"
            )
        elif pipeline == "healthcare_clinical":
            lines.append("## 🧬 Pipeline: Salud / Documentos Clínicos\n")
            lines.append(
                "Enfoque: consistencia clínica, riesgos en protocolos y hallazgos críticos.\n\n"
            )
        elif pipeline == "manufacturing_maintenance":
            lines.append("## 🏭 Pipeline: Manufactura / Mantenimiento\n")
            lines.append(
                "Enfoque: fallas recurrentes, criticidad de equipos y riesgos operativos.\n\n"
            )
        elif pipeline == "gov_procurement_audit":
            lines.append("## 🏛️ Pipeline: Gobierno / Compras y Auditoría\n")
            lines.append(
                "Enfoque: anomalías en compras, riesgos de corrupción y hallazgos de auditoría.\n\n"
            )
        else:
            lines.append("## 🌀 Pipeline General Stargate PDF\n\n")

        # 3) Resumen general del procesamiento base
        docs_count = base_results.get("documents_processed", 0)
        chunks_count = base_results.get("chunks_generated", 0)
        lines.append(
            f"**Documentos procesados**: {docs_count}  \n**Chunks generados**: {chunks_count}\n\n"
        )

        # 4) Vista rápida de problemas/oportunidades según pipeline
        problems = base_results.get("problems_detected", []) or []
        opportunities = base_results.get("opportunities_detected", []) or []

        # Selección simple: problemas críticos primero
        critical_problems = [
            p for p in problems if str(p.get("severity", "")).lower() == "alta"
        ]

        if critical_problems:
            lines.append("### 🔴 Problemas Críticos Detectados\n\n")
            for p in critical_problems:
                desc = p.get("description", "")
                ptype = p.get("type", "N/A")
                src = p.get("source", "N/A")
                lines.append(f"- **{ptype}** — {desc}  \n  📄 Origen: {src}\n")
            lines.append("\n")

        if opportunities:
            lines.append("### 💡 Oportunidades Relevantes\n\n")
            for o in opportunities:
                desc = o.get("description", "")
                otype = o.get("type", "N/A")
                src = o.get("source", "N/A")
                lines.append(f"- **{otype}** — {desc}  \n  📄 Origen: {src}\n")
            lines.append("\n")

        # 5) Documentos con tipo y resumen COMPLETO (sin límite)
        summaries = base_results.get("summaries", {}) or {}
        if summaries:
            lines.append("### 📄 Documentos Analizados\n\n")
            for fname, sdata in summaries.items():
                doc_type = sdata.get("document_type", "N/A")
                summary_full = sdata.get("summary", "") or ""
                key_points = sdata.get("key_points", []) or []
                topics = sdata.get("topics", []) or []
                business_value = sdata.get("business_value", "") or ""
                entities = sdata.get("entities", []) or []
                
                lines.append(f"#### 📄 {fname}\n\n")
                lines.append(f"**Tipo de Documento**: {doc_type}\n\n")
                lines.append(f"**Resumen Ejecutivo**:\n{summary_full}\n\n")
                
                if key_points:
                    lines.append(f"**Puntos Clave** ({len(key_points)}):\n")
                    for i, point in enumerate(key_points, 1):
                        lines.append(f"{i}. {point}\n")
                    lines.append("\n")
                
                if topics:
                    lines.append(f"**Temas**: {', '.join(topics)}\n\n")
                
                if business_value:
                    lines.append(f"**Valor para el Negocio**: {business_value}\n\n")
                
                if entities:
                    lines.append(f"**Entidades Principales**: {', '.join(entities)}\n\n")
                
                lines.append("---\n\n")

        # 6) Reusar insights generales del pipeline base al final
        insights = base_results.get("insights", []) or []
        if insights:
            lines.append("### 📊 Insights Generales del Motor Base\n\n")
            for ins in insights:
                title = ins.get("title", "Insight")
                content = ins.get("content", "")
                lines.append(f"#### {title}\n\n{content}\n\n")

        return "".join(lines)




