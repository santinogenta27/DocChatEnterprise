"""Insurance Claim Workflow - Procesamiento de reclamos de seguros."""

from __future__ import annotations

from typing import List, Dict, Any
import json
from datetime import datetime

from .base_workflow import BaseWorkflow
from ..orchestrator.decision_orchestrator import ClassifiedDocument


class InsuranceClaimWorkflow(BaseWorkflow):
    """
    Workflow para reclamos de seguros.
    
    Extrae:
    - Tipo de reclamo
    - Monto estimado
    - Partes involucradas
    - Evidencias
    - Fecha del siniestro
    
    Acciones:
    - Evaluar consistencia
    - Generar JSON procesable
    """
    
    def extract_fields(self, documents: List[ClassifiedDocument]) -> Dict[str, Any]:
        """Extrae campos de reclamos."""
        extracted = {
            "claims": [],
            "total_claims": len(documents)
        }
        
        for doc in documents:
            text = doc.text
            metadata = doc.document.metadata
            
            prompt = f"""Extrae los siguientes campos de este reclamo de seguro:

TEXTO DEL RECLAMO:
{text[:8000]}

Extrae y devuelve ÚNICAMENTE un JSON válido con estos campos:
{{
    "claim_number": "número de reclamo o N/A",
    "policy_number": "número de póliza o N/A",
    "claim_type": "tipo de reclamo (accidente, robo, daño, etc.)",
    "incident_date": "fecha del siniestro YYYY-MM-DD o N/A",
    "claim_date": "fecha del reclamo YYYY-MM-DD o N/A",
    "insured_name": "nombre del asegurado o N/A",
    "estimated_amount": número decimal o 0,
    "currency": "moneda o N/A",
    "description": "descripción del incidente",
    "parties_involved": [
        "parte 1",
        "parte 2"
    ],
    "evidence_types": [
        "tipo de evidencia 1"
    ],
    "damage_description": "descripción de daños",
    "coverage_type": "tipo de cobertura",
    "deductible": número decimal o 0,
    "status": "estado del reclamo (pendiente, aprobado, rechazado) o N/A"
}}

IMPORTANTE:
- Devuelve SOLO el JSON, sin explicaciones"""
            
            try:
                response = self.llm.invoke(prompt).content.strip()
                
                if response.startswith("```json"):
                    response = response.replace("```json", "").replace("```", "").strip()
                elif response.startswith("```"):
                    response = response.replace("```", "").strip()
                
                claim_data = json.loads(response)
                claim_data["source_file"] = metadata.get("source", "unknown")
                claim_data["confidence"] = doc.confidence
                
                extracted["claims"].append(claim_data)
                
            except Exception as e:
                extracted["claims"].append({
                    "claim_number": "N/A",
                    "source_file": metadata.get("source", "unknown"),
                    "confidence": 0.3
                })
        
        return extracted
    
    def validate(self, extracted_fields: Dict[str, Any]) -> tuple[bool, List[str]]:
        """Valida los campos extraídos."""
        errors = []
        
        if not extracted_fields.get("claims"):
            errors.append("No se encontraron reclamos")
            return False, errors
        
        for claim in extracted_fields["claims"]:
            if not claim.get("policy_number") or claim.get("policy_number") == "N/A":
                errors.append("Número de póliza no encontrado")
            
            if claim.get("estimated_amount", 0) <= 0:
                errors.append("Monto estimado inválido o no encontrado")
        
        return len(errors) == 0, errors
    
    def execute_actions(self, extracted_fields: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Ejecuta acciones automáticas."""
        actions = []
        
        # 1. Generar JSON
        json_result = self.action_layer.produce_json(
            data=extracted_fields,
            filename=f"insurance_claims_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        actions.append(json_result.to_dict())
        
        # 2. Para reclamos de alto monto, crear alerta
        for claim in extracted_fields.get("claims", []):
            amount = claim.get("estimated_amount", 0)
            if amount > 10000:  # Umbral configurable
                alert_result = self.action_layer.emit_alert(
                    level="warning",
                    message=f"Reclamo de alto monto: ${amount:,.2f} - {claim.get('claim_number', 'N/A')}",
                    channel="email",
                    metadata={"claim_number": claim.get("claim_number"), "amount": amount}
                )
                actions.append(alert_result.to_dict())
        
        # 3. Generar reporte HTML
        html_content = self._generate_claim_report_html(extracted_fields)
        report_result = self.action_layer.generate_report_html(
            title="Análisis de Reclamos de Seguros",
            content=html_content,
            filename=f"insurance_claim_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        )
        actions.append(report_result.to_dict())
        
        return actions
    
    def _generate_claim_report_html(self, extracted_fields: Dict[str, Any]) -> str:
        """Genera contenido HTML para el reporte."""
        html = f"<h2>Análisis de {extracted_fields.get('total_claims', 0)} Reclamos</h2>"
        
        total_amount = sum(claim.get("estimated_amount", 0) for claim in extracted_fields.get("claims", []))
        html += f"<p><strong>Monto total estimado:</strong> ${total_amount:,.2f}</p>"
        
        html += "<table border='1' cellpadding='5' style='border-collapse: collapse; width: 100%;'>"
        html += "<tr><th>Número</th><th>Tipo</th><th>Fecha</th><th>Monto</th><th>Estado</th></tr>"
        
        for claim in extracted_fields.get("claims", []):
            html += f"""
            <tr>
                <td>{claim.get('claim_number', 'N/A')}</td>
                <td>{claim.get('claim_type', 'N/A')}</td>
                <td>{claim.get('incident_date', 'N/A')}</td>
                <td>${claim.get('estimated_amount', 0):,.2f}</td>
                <td>{claim.get('status', 'N/A')}</td>
            </tr>
            """
        
        html += "</table>"
        
        return html

