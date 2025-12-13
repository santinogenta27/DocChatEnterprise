"""Contract Workflow - Procesamiento automático de contratos."""

from __future__ import annotations

from typing import List, Dict, Any
import json
from datetime import datetime

from .base_workflow import BaseWorkflow
from ..orchestrator.decision_orchestrator import ClassifiedDocument


class ContractWorkflow(BaseWorkflow):
    """
    Workflow para procesamiento de contratos.
    
    Extrae:
    - Partes involucradas
    - Fechas (inicio, fin, vigencia)
    - Obligaciones
    - Cláusulas críticas
    - Montos
    - Jurisdicción
    
    Acciones:
    - Detectar riesgos
    - Detectar cláusulas faltantes
    - Generar resumen legal
    """
    
    def extract_fields(self, documents: List[ClassifiedDocument]) -> Dict[str, Any]:
        """Extrae campos de contratos."""
        extracted = {
            "contracts": [],
            "total_contracts": len(documents)
        }
        
        for doc in documents:
            text = doc.text
            metadata = doc.document.metadata
            
            prompt = f"""Extrae los siguientes campos de este contrato:

TEXTO DEL CONTRATO:
{text[:8000]}

Extrae y devuelve ÚNICAMENTE un JSON válido con estos campos:
{{
    "contract_type": "tipo de contrato (servicios, arrendamiento, etc.)",
    "parties": [
        {{
            "name": "nombre de la parte",
            "role": "rol (contratante, contratista, etc.)"
        }}
    ],
    "effective_date": "fecha de inicio YYYY-MM-DD o N/A",
    "expiration_date": "fecha de fin YYYY-MM-DD o N/A",
    "jurisdiction": "jurisdicción o ley aplicable",
    "total_amount": número decimal o 0,
    "currency": "moneda o N/A",
    "payment_terms": "términos de pago",
    "key_obligations": [
        "obligación 1",
        "obligación 2"
    ],
    "critical_clauses": [
        {{
            "clause_name": "nombre de la cláusula",
            "description": "descripción"
        }}
    ],
    "risks_detected": [
        "riesgo 1",
        "riesgo 2"
    ],
    "missing_clauses": [
        "cláusula faltante 1"
    ],
    "signatures_required": número o 0
}}

IMPORTANTE:
- Si un campo no existe, usa "N/A" o []
- Devuelve SOLO el JSON, sin explicaciones"""
            
            try:
                response = self.llm.invoke(prompt).content.strip()
                
                if response.startswith("```json"):
                    response = response.replace("```json", "").replace("```", "").strip()
                elif response.startswith("```"):
                    response = response.replace("```", "").strip()
                
                contract_data = json.loads(response)
                contract_data["source_file"] = metadata.get("source", "unknown")
                contract_data["confidence"] = doc.confidence
                
                extracted["contracts"].append(contract_data)
                
            except Exception as e:
                # Fallback básico
                extracted["contracts"].append({
                    "contract_type": "unknown",
                    "parties": [],
                    "source_file": metadata.get("source", "unknown"),
                    "confidence": 0.3
                })
        
        return extracted
    
    def validate(self, extracted_fields: Dict[str, Any]) -> tuple[bool, List[str]]:
        """Valida los campos extraídos."""
        errors = []
        
        if not extracted_fields.get("contracts"):
            errors.append("No se encontraron contratos")
            return False, errors
        
        for contract in extracted_fields["contracts"]:
            if not contract.get("parties") or len(contract.get("parties", [])) < 2:
                errors.append("Contrato sin partes suficientes identificadas")
            
            if not contract.get("effective_date") or contract.get("effective_date") == "N/A":
                errors.append("Fecha de inicio no encontrada")
        
        return len(errors) == 0, errors
    
    def execute_actions(self, extracted_fields: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Ejecuta acciones automáticas."""
        actions = []
        
        # 1. Generar JSON
        json_result = self.action_layer.produce_json(
            data=extracted_fields,
            filename=f"contracts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        actions.append(json_result.to_dict())
        
        # 2. Para cada contrato con riesgos, crear alerta
        for contract in extracted_fields.get("contracts", []):
            risks = contract.get("risks_detected", [])
            if risks:
                alert_result = self.action_layer.emit_alert(
                    level="warning",
                    message=f"Contrato {contract.get('contract_type', 'N/A')} tiene {len(risks)} riesgos detectados",
                    channel="email",
                    metadata={"contract_type": contract.get("contract_type"), "risks": risks}
                )
                actions.append(alert_result.to_dict())
            
            # Si faltan cláusulas críticas, crear ticket
            missing = contract.get("missing_clauses", [])
            if missing:
                ticket_result = self.action_layer.create_ticket(
                    title=f"Contrato con cláusulas faltantes: {contract.get('contract_type', 'N/A')}",
                    description=f"Cláusulas faltantes detectadas: {', '.join(missing)}",
                    priority="high",
                    metadata={"contract_type": contract.get("contract_type"), "missing_clauses": missing}
                )
                actions.append(ticket_result.to_dict())
        
        # 3. Generar reporte HTML
        html_content = self._generate_contract_report_html(extracted_fields)
        report_result = self.action_layer.generate_report_html(
            title="Análisis de Contratos",
            content=html_content,
            filename=f"contract_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        )
        actions.append(report_result.to_dict())
        
        return actions
    
    def _generate_contract_report_html(self, extracted_fields: Dict[str, Any]) -> str:
        """Genera contenido HTML para el reporte."""
        html = f"<h2>Análisis de {extracted_fields.get('total_contracts', 0)} Contratos</h2>"
        
        for contract in extracted_fields.get("contracts", []):
            html += f"<h3>Contrato: {contract.get('contract_type', 'N/A')}</h3>"
            html += f"<p><strong>Partes:</strong> {len(contract.get('parties', []))}</p>"
            html += f"<p><strong>Vigencia:</strong> {contract.get('effective_date', 'N/A')} - {contract.get('expiration_date', 'N/A')}</p>"
            
            risks = contract.get("risks_detected", [])
            if risks:
                html += f"<p><strong>⚠️ Riesgos detectados ({len(risks)}):</strong></p><ul>"
                for risk in risks:
                    html += f"<li>{risk}</li>"
                html += "</ul>"
            
            html += "<hr>"
        
        return html

