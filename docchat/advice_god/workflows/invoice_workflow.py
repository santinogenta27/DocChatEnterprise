"""Invoice Workflow - Procesamiento automático de facturas."""

from __future__ import annotations

from typing import List, Dict, Any
import re
import json
from datetime import datetime

from .base_workflow import BaseWorkflow
from ..orchestrator.decision_orchestrator import ClassifiedDocument
from ..actions.action_layer import ActionType


class InvoiceWorkflow(BaseWorkflow):
    """
    Workflow para procesamiento de facturas.
    
    Extrae:
    - Fecha
    - Monto total
    - Proveedor
    - Line items
    - Impuestos
    - Número de factura
    - Orden de compra
    
    Acciones:
    - Validar consistencia
    - Generar JSON estándar
    - Preparar para conciliación contable
    """
    
    def extract_fields(self, documents: List[ClassifiedDocument]) -> Dict[str, Any]:
        """Extrae campos de facturas."""
        extracted = {
            "invoices": [],
            "total_amount": 0.0,
            "total_invoices": len(documents)
        }
        
        for doc in documents:
            text = doc.text
            metadata = doc.document.metadata
            
            # Extraer usando LLM
            prompt = f"""Extrae los siguientes campos de esta factura:

TEXTO DE LA FACTURA:
{text[:5000]}

Extrae y devuelve ÚNICAMENTE un JSON válido con estos campos:
{{
    "invoice_number": "número de factura o N/A",
    "invoice_date": "fecha en formato YYYY-MM-DD o N/A",
    "supplier": "nombre del proveedor o N/A",
    "total_amount": número decimal o 0,
    "subtotal": número decimal o 0,
    "tax_amount": número decimal o 0,
    "tax_rate": número decimal o 0,
    "currency": "moneda (USD, EUR, etc.) o N/A",
    "purchase_order": "número de orden de compra o N/A",
    "line_items": [
        {{
            "description": "descripción del item",
            "quantity": número,
            "unit_price": número decimal,
            "total": número decimal
        }}
    ],
    "payment_terms": "términos de pago o N/A",
    "due_date": "fecha de vencimiento YYYY-MM-DD o N/A"
}}

IMPORTANTE:
- Si un campo no existe, usa "N/A" o 0
- Los montos deben ser números, no texto
- Devuelve SOLO el JSON, sin explicaciones"""
            
            try:
                response = self.llm.invoke(prompt).content.strip()
                
                # Limpiar respuesta (remover markdown si existe)
                if response.startswith("```json"):
                    response = response.replace("```json", "").replace("```", "").strip()
                elif response.startswith("```"):
                    response = response.replace("```", "").strip()
                
                invoice_data = json.loads(response)
                
                # Validar y limpiar datos
                invoice_data["source_file"] = metadata.get("source", "unknown")
                invoice_data["confidence"] = doc.confidence
                
                # Convertir montos a float
                for field in ["total_amount", "subtotal", "tax_amount", "tax_rate"]:
                    if field in invoice_data:
                        try:
                            if isinstance(invoice_data[field], str):
                                # Extraer número de string
                                numbers = re.findall(r'\d+\.?\d*', invoice_data[field].replace(',', ''))
                                if numbers:
                                    invoice_data[field] = float(numbers[0])
                                else:
                                    invoice_data[field] = 0.0
                            else:
                                invoice_data[field] = float(invoice_data[field])
                        except:
                            invoice_data[field] = 0.0
                
                extracted["invoices"].append(invoice_data)
                extracted["total_amount"] += invoice_data.get("total_amount", 0.0)
                
            except Exception as e:
                # Si falla la extracción con LLM, intentar extracción básica con regex
                invoice_basic = self._extract_basic_invoice_fields(text, metadata)
                if invoice_basic:
                    extracted["invoices"].append(invoice_basic)
                    extracted["total_amount"] += invoice_basic.get("total_amount", 0.0)
        
        return extracted
    
    def _extract_basic_invoice_fields(self, text: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Extracción básica con regex como fallback."""
        text_lower = text.lower()
        
        # Buscar número de factura
        invoice_num_match = re.search(r'(?:factura|invoice)\s*#?\s*:?\s*(\w+)', text_lower)
        invoice_number = invoice_num_match.group(1) if invoice_num_match else "N/A"
        
        # Buscar monto total
        total_match = re.search(r'(?:total|monto total)\s*:?\s*\$?\s*([\d,]+\.?\d*)', text_lower)
        total_amount = 0.0
        if total_match:
            try:
                total_amount = float(total_match.group(1).replace(',', ''))
            except:
                pass
        
        # Buscar proveedor (líneas que contengan "proveedor", "supplier", "vendor")
        supplier_match = re.search(r'(?:proveedor|supplier|vendor)\s*:?\s*([^\n]+)', text_lower)
        supplier = supplier_match.group(1).strip() if supplier_match else "N/A"
        
        return {
            "invoice_number": invoice_number,
            "invoice_date": "N/A",
            "supplier": supplier,
            "total_amount": total_amount,
            "subtotal": 0.0,
            "tax_amount": 0.0,
            "tax_rate": 0.0,
            "currency": "N/A",
            "purchase_order": "N/A",
            "line_items": [],
            "payment_terms": "N/A",
            "due_date": "N/A",
            "source_file": metadata.get("source", "unknown"),
            "confidence": 0.5
        }
    
    def validate(self, extracted_fields: Dict[str, Any]) -> tuple[bool, List[str]]:
        """Valida los campos extraídos."""
        errors = []
        
        if not extracted_fields.get("invoices"):
            errors.append("No se encontraron facturas en los documentos")
            return False, errors
        
        for invoice in extracted_fields["invoices"]:
            # Validar monto total
            if invoice.get("total_amount", 0) <= 0:
                errors.append(f"Factura {invoice.get('invoice_number', 'N/A')}: Monto total inválido")
            
            # Validar que tenga proveedor
            if not invoice.get("supplier") or invoice.get("supplier") == "N/A":
                errors.append(f"Factura {invoice.get('invoice_number', 'N/A')}: Proveedor no encontrado")
            
            # Validar consistencia: subtotal + tax = total (aproximado)
            subtotal = invoice.get("subtotal", 0)
            tax = invoice.get("tax_amount", 0)
            total = invoice.get("total_amount", 0)
            
            if subtotal > 0 and tax > 0 and total > 0:
                calculated_total = subtotal + tax
                if abs(calculated_total - total) > 0.01:  # Tolerancia de 1 centavo
                    errors.append(
                        f"Factura {invoice.get('invoice_number', 'N/A')}: "
                        f"Inconsistencia en montos (subtotal + tax ≠ total)"
                    )
        
        return len(errors) == 0, errors
    
    def execute_actions(self, extracted_fields: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Ejecuta acciones automáticas."""
        actions = []
        
        # 1. Generar JSON estructurado
        json_result = self.action_layer.produce_json(
            data=extracted_fields,
            filename=f"invoices_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        actions.append(json_result.to_dict())
        
        # 2. Generar reporte HTML
        html_content = self._generate_invoice_report_html(extracted_fields)
        report_result = self.action_layer.generate_report_html(
            title="Reporte de Facturas Procesadas",
            content=html_content,
            filename=f"invoice_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        )
        actions.append(report_result.to_dict())
        
        # 3. Para cada factura, crear ticket si hay inconsistencias
        for invoice in extracted_fields.get("invoices", []):
            if invoice.get("purchase_order") == "N/A" or not invoice.get("purchase_order"):
                # Factura sin orden de compra - crear ticket
                ticket_result = self.action_layer.create_ticket(
                    title=f"Factura sin PO: {invoice.get('invoice_number', 'N/A')}",
                    description=f"Factura de {invoice.get('supplier', 'N/A')} por ${invoice.get('total_amount', 0):.2f} sin orden de compra asociada.",
                    priority="medium",
                    metadata={"invoice_number": invoice.get("invoice_number"), "workflow": "invoice"}
                )
                actions.append(ticket_result.to_dict())
        
        # 4. Guardar en base de datos (preparar para conciliación)
        db_result = self.action_layer.save_to_db(
            table="invoices",
            data=extracted_fields,
            operation="insert"
        )
        actions.append(db_result.to_dict())
        
        return actions
    
    def _generate_invoice_report_html(self, extracted_fields: Dict[str, Any]) -> str:
        """Genera contenido HTML para el reporte de facturas."""
        html = "<h2>Resumen de Facturas Procesadas</h2>"
        html += f"<p><strong>Total de facturas:</strong> {extracted_fields.get('total_invoices', 0)}</p>"
        html += f"<p><strong>Monto total:</strong> ${extracted_fields.get('total_amount', 0):,.2f}</p>"
        html += "<hr>"
        
        html += "<h3>Detalle de Facturas</h3>"
        html += "<table border='1' cellpadding='5' style='border-collapse: collapse; width: 100%;'>"
        html += "<tr><th>Número</th><th>Proveedor</th><th>Fecha</th><th>Monto</th><th>PO</th></tr>"
        
        for invoice in extracted_fields.get("invoices", []):
            html += f"""
            <tr>
                <td>{invoice.get('invoice_number', 'N/A')}</td>
                <td>{invoice.get('supplier', 'N/A')}</td>
                <td>{invoice.get('invoice_date', 'N/A')}</td>
                <td>${invoice.get('total_amount', 0):,.2f}</td>
                <td>{invoice.get('purchase_order', 'N/A')}</td>
            </tr>
            """
        
        html += "</table>"
        
        return html

