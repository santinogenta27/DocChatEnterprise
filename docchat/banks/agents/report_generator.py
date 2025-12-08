"""
Agent 6: Report Generator - Genera SARs y reportes en formatos estándar.
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

try:
    from weasyprint import HTML
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False
    HTML = None
    logging.warning("weasyprint no disponible, usando fallback")

from jinja2 import Template

from .base_agent import BaseBanksAgent
from ..schemas import SARData, RiskScore
from ....config import AppConfig

logger = logging.getLogger(__name__)


class ReportGeneratorAgent(BaseBanksAgent):
    """Agente que genera SARs y reportes en formatos estándar."""
    
    def __init__(self, config: AppConfig):
        super().__init__(config, "report_generator")
        self.output_dir = Path(config.cache_dir) / "banks" / "reports"
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Genera reportes (SARs, PDFs, etc.) basado en los resultados.
        
        Input state:
            - extracted_entities: List[EntityExtraction]
            - risk_scores: List[RiskScore]
            - sanction_hits: List[SanctionHit]
            - jurisdiction: str (opcional, default "US")
        
        Output state:
            - generated_reports: List[Dict] con paths y metadata
        """
        entities = state.get("extracted_entities", [])
        risk_scores = state.get("risk_scores", [])
        sanction_hits = state.get("sanction_hits", [])
        jurisdiction = state.get("jurisdiction", "US")
        
        generated_reports = []
        
        # Generar SAR para cada entidad con score alto o hits
        for i, entity in enumerate(entities):
            risk_score = risk_scores[i] if i < len(risk_scores) else None
            
            # Solo generar SAR si hay riesgo significativo
            if risk_score:
                score_value = risk_score.get("total_score") if isinstance(risk_score, dict) else getattr(risk_score, "total_score", 0)
            else:
                score_value = 0
            
            if score_value >= 50 or sanction_hits:
                try:
                    sar = self._generate_sar(entity, risk_score, sanction_hits, jurisdiction)
                    if sar:
                        # Guardar SAR
                        sar_path = self._save_sar(sar, jurisdiction)
                        generated_reports.append({
                            "type": "SAR",
                            "path": str(sar_path),
                            "entity": entity.get("name") if isinstance(entity, dict) else getattr(entity, "name", "Unknown"),
                            "risk_score": score_value,
                            "jurisdiction": jurisdiction
                        })
                except Exception as e:
                    logger.error(f"Error generando SAR: {e}")
        
        # Generar reporte consolidado PDF
        try:
            pdf_path = self._generate_consolidated_pdf(entities, risk_scores, sanction_hits)
            if pdf_path:
                generated_reports.append({
                    "type": "PDF",
                    "path": str(pdf_path),
                    "description": "Reporte consolidado de compliance"
                })
        except Exception as e:
            logger.error(f"Error generando PDF: {e}")
        
        # Log de auditoría
        self.log_audit(
            action="report_generation",
            input_data={"entities_count": len(entities)},
            output_data={"reports_generated": len(generated_reports)}
        )
        
        state["generated_reports"] = generated_reports
        return state
    
    def _generate_sar(
        self,
        entity: Any,
        risk_score: Optional[Any],
        sanction_hits: List[Any],
        jurisdiction: str
    ) -> Optional[SARData]:
        """Genera un SAR (Suspicious Activity Report)."""
        
        # Extraer datos de la entidad
        if isinstance(entity, dict):
            name = entity.get("name", "Unknown")
            id_number = entity.get("id_number", "")
            transactions = entity.get("transactions", [])
        else:
            name = getattr(entity, "name", "Unknown")
            id_number = getattr(entity, "id_number", "")
            transactions = getattr(entity, "transactions", [])
        
        # Determinar actividad sospechosa
        suspicious_activity = self._describe_suspicious_activity(risk_score, sanction_hits, transactions)
        
        # Calcular importe total
        total_amount = sum(
            t.get("amount", 0) if isinstance(t, dict) else getattr(t, "amount", 0)
            for t in transactions
        )
        
        # Obtener score
        score_value = 0
        if risk_score:
            score_value = risk_score.get("total_score") if isinstance(risk_score, dict) else getattr(risk_score, "total_score", 0)
        
        # Crear evidencia
        evidence = []
        if sanction_hits:
            for hit in sanction_hits:
                evidence.append({
                    "type": "sanction_hit",
                    "list": hit.get("list_name") if isinstance(hit, dict) else getattr(hit, "list_name", ""),
                    "match": hit.get("name") if isinstance(hit, dict) else getattr(hit, "name", "")
                })
        
        if risk_score:
            risk_evidence = risk_score.get("evidence") if isinstance(risk_score, dict) else getattr(risk_score, "evidence", [])
            evidence.extend(risk_evidence)
        
        sar = SARData(
            report_id=f"SAR_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{name.replace(' ', '_')}",
            client_name=name,
            client_id=id_number,
            report_type="SAR",
            jurisdiction=jurisdiction,
            suspicious_activity=suspicious_activity,
            amount=total_amount if total_amount > 0 else None,
            currency="USD",
            risk_score=score_value,
            evidence=evidence,
            status="draft"
        )
        
        return sar
    
    def _describe_suspicious_activity(
        self,
        risk_score: Optional[Any],
        sanction_hits: List[Any],
        transactions: List[Any]
    ) -> str:
        """Describe la actividad sospechosa."""
        parts = []
        
        if sanction_hits:
            parts.append(f"Hit en {len(sanction_hits)} lista(s) de sanciones")
        
        if risk_score:
            if isinstance(risk_score, dict):
                explanation = risk_score.get("explanation", "")
            else:
                explanation = getattr(risk_score, "explanation", "")
            parts.append(explanation)
        
        if transactions:
            high_risk_txns = [
                t for t in transactions
                if (t.get("amount", 0) if isinstance(t, dict) else getattr(t, "amount", 0)) > 10000
            ]
            if high_risk_txns:
                parts.append(f"{len(high_risk_txns)} transacción(es) de alto valor detectada(s)")
        
        return ". ".join(parts) if parts else "Actividad sospechosa detectada por sistema de scoring automático"
    
    def _save_sar(self, sar: SARData, jurisdiction: str) -> Path:
        """Guarda un SAR en formato XML (FinCEN) o formato local."""
        
        if jurisdiction == "US":
            # Formato FinCEN XML
            xml_path = self.output_dir / f"{sar.report_id}.xml"
            self._generate_fincen_xml(sar, xml_path)
            return xml_path
        elif jurisdiction in ["MX", "CO"]:
            # Formatos locales (SAGRILAFT, etc.)
            json_path = self.output_dir / f"{sar.report_id}.json"
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(sar.model_dump(mode='json', default=str), f, indent=2, ensure_ascii=False)
            return json_path
        else:
            # Formato genérico JSON
            json_path = self.output_dir / f"{sar.report_id}.json"
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(sar.model_dump(mode='json', default=str), f, indent=2, ensure_ascii=False)
            return json_path
    
    def _generate_fincen_xml(self, sar: SARData, output_path: Path):
        """Genera XML en formato FinCEN."""
        root = ET.Element("SAR")
        root.set("version", "1.0")
        
        # Header
        header = ET.SubElement(root, "Header")
        ET.SubElement(header, "ReportID").text = sar.report_id
        ET.SubElement(header, "ReportType").text = sar.report_type
        ET.SubElement(header, "FilingDate").text = datetime.now().strftime("%Y-%m-%d")
        
        # Subject
        subject = ET.SubElement(root, "Subject")
        ET.SubElement(subject, "Name").text = sar.client_name
        ET.SubElement(subject, "ID").text = sar.client_id or ""
        
        # Activity
        activity = ET.SubElement(root, "Activity")
        ET.SubElement(activity, "Description").text = sar.suspicious_activity
        if sar.amount:
            ET.SubElement(activity, "Amount").text = str(sar.amount)
            ET.SubElement(activity, "Currency").text = sar.currency
        
        # Risk
        risk = ET.SubElement(root, "Risk")
        ET.SubElement(risk, "Score").text = str(sar.risk_score)
        
        # Evidence
        evidence_elem = ET.SubElement(root, "Evidence")
        for ev in sar.evidence:
            ev_elem = ET.SubElement(evidence_elem, "Item")
            for key, value in ev.items():
                ET.SubElement(ev_elem, key).text = str(value)
        
        # Guardar XML
        tree = ET.ElementTree(root)
        ET.indent(tree, space="  ")
        tree.write(output_path, encoding='utf-8', xml_declaration=True)
    
    def _generate_consolidated_pdf(
        self,
        entities: List[Any],
        risk_scores: List[Any],
        sanction_hits: List[Any]
    ) -> Optional[Path]:
        """Genera un PDF consolidado con todos los resultados."""
        
        # Template HTML
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Compliance Report</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                h1 { color: #2c3e50; }
                .entity { margin: 20px 0; padding: 15px; border: 1px solid #ddd; }
                .risk-high { background-color: #ffebee; }
                .risk-medium { background-color: #fff3e0; }
                .risk-low { background-color: #e8f5e9; }
            </style>
        </head>
        <body>
            <h1>Compliance Report - {{ date }}</h1>
            <p>Total entities: {{ entities_count }}</p>
            <p>Sanction hits: {{ hits_count }}</p>
            
            {% for entity in entities %}
            <div class="entity risk-{{ entity.risk_level }}">
                <h2>{{ entity.name }}</h2>
                <p><strong>Risk Score:</strong> {{ entity.risk_score }}/100</p>
                <p><strong>ID:</strong> {{ entity.id_number }}</p>
                {% if entity.explanation %}
                <p><strong>Explanation:</strong> {{ entity.explanation }}</p>
                {% endif %}
            </div>
            {% endfor %}
        </body>
        </html>
        """
        
        # Preparar datos
        entities_data = []
        for i, entity in enumerate(entities):
            risk_score = risk_scores[i] if i < len(risk_scores) else None
            score_value = 0
            explanation = ""
            
            if risk_score:
                score_value = risk_score.get("total_score") if isinstance(risk_score, dict) else getattr(risk_score, "total_score", 0)
                explanation = risk_score.get("explanation", "") if isinstance(risk_score, dict) else getattr(risk_score, "explanation", "")
            
            if score_value >= 70:
                risk_level = "high"
            elif score_value >= 40:
                risk_level = "medium"
            else:
                risk_level = "low"
            
            name = entity.get("name") if isinstance(entity, dict) else getattr(entity, "name", "Unknown")
            id_number = entity.get("id_number") if isinstance(entity, dict) else getattr(entity, "id_number", "")
            
            entities_data.append({
                "name": name,
                "id_number": id_number,
                "risk_score": score_value,
                "risk_level": risk_level,
                "explanation": explanation
            })
        
        # Renderizar HTML
        template = Template(html_template)
        html_content = template.render(
            date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            entities_count=len(entities),
            hits_count=len(sanction_hits),
            entities=entities_data
        )
        
        # Generar PDF
        if WEASYPRINT_AVAILABLE and HTML:
            pdf_path = self.output_dir / f"compliance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            HTML(string=html_content).write_pdf(pdf_path)
            return pdf_path
        else:
            # Fallback: guardar HTML
            html_path = self.output_dir / f"compliance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            return html_path

