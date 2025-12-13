"""Bank Statement Workflow - Procesamiento de extractos bancarios."""

from __future__ import annotations

from typing import List, Dict, Any
import json
import re
from datetime import datetime

from .base_workflow import BaseWorkflow
from ..orchestrator.decision_orchestrator import ClassifiedDocument


class BankStatementWorkflow(BaseWorkflow):
    """
    Workflow para extractos bancarios.
    
    Extrae:
    - Transacciones
    - Categorización automática
    - Ingresos y egresos
    - Saldo inicial y final
    
    Acciones:
    - Preparar para reconciliación financiera
    """
    
    def extract_fields(self, documents: List[ClassifiedDocument]) -> Dict[str, Any]:
        """Extrae campos de extractos bancarios."""
        extracted = {
            "statements": [],
            "total_transactions": 0,
            "total_income": 0.0,
            "total_expenses": 0.0
        }
        
        for doc in documents:
            text = doc.text
            metadata = doc.document.metadata
            
            prompt = f"""Extrae los siguientes campos de este extracto bancario:

TEXTO DEL EXTRACTO:
{text[:8000]}

Extrae y devuelve ÚNICAMENTE un JSON válido con estos campos:
{{
    "account_number": "número de cuenta o N/A",
    "bank_name": "nombre del banco o N/A",
    "statement_period": "período del extracto (ej: Enero 2024) o N/A",
    "opening_balance": número decimal o 0,
    "closing_balance": número decimal o 0,
    "currency": "moneda o N/A",
    "transactions": [
        {{
            "date": "fecha YYYY-MM-DD",
            "description": "descripción de la transacción",
            "amount": número decimal (positivo para ingresos, negativo para egresos),
            "type": "income o expense",
            "category": "categoría (salario, transferencia, pago, etc.)",
            "balance_after": número decimal o 0
        }}
    ]
}}

IMPORTANTE:
- Devuelve SOLO el JSON, sin explicaciones
- Las transacciones deben tener amount positivo (ingresos) o negativo (egresos)"""
            
            try:
                response = self.llm.invoke(prompt).content.strip()
                
                if response.startswith("```json"):
                    response = response.replace("```json", "").replace("```", "").strip()
                elif response.startswith("```"):
                    response = response.replace("```", "").strip()
                
                statement_data = json.loads(response)
                statement_data["source_file"] = metadata.get("source", "unknown")
                statement_data["confidence"] = doc.confidence
                
                # Calcular totales
                transactions = statement_data.get("transactions", [])
                for txn in transactions:
                    amount = float(txn.get("amount", 0))
                    if amount > 0:
                        extracted["total_income"] += amount
                    else:
                        extracted["total_expenses"] += abs(amount)
                
                extracted["total_transactions"] += len(transactions)
                extracted["statements"].append(statement_data)
                
            except Exception as e:
                # Fallback básico
                extracted["statements"].append({
                    "account_number": "N/A",
                    "source_file": metadata.get("source", "unknown"),
                    "confidence": 0.3
                })
        
        return extracted
    
    def validate(self, extracted_fields: Dict[str, Any]) -> tuple[bool, List[str]]:
        """Valida los campos extraídos."""
        errors = []
        
        if not extracted_fields.get("statements"):
            errors.append("No se encontraron extractos bancarios")
            return False, errors
        
        for statement in extracted_fields["statements"]:
            if not statement.get("account_number") or statement.get("account_number") == "N/A":
                errors.append("Número de cuenta no encontrado")
            
            transactions = statement.get("transactions", [])
            if not transactions:
                errors.append("No se encontraron transacciones")
        
        return len(errors) == 0, errors
    
    def execute_actions(self, extracted_fields: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Ejecuta acciones automáticas."""
        actions = []
        
        # 1. Generar JSON
        json_result = self.action_layer.produce_json(
            data=extracted_fields,
            filename=f"bank_statements_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        actions.append(json_result.to_dict())
        
        # 2. Generar reporte HTML
        html_content = self._generate_statement_report_html(extracted_fields)
        report_result = self.action_layer.generate_report_html(
            title="Análisis de Extractos Bancarios",
            content=html_content,
            filename=f"bank_statement_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        )
        actions.append(report_result.to_dict())
        
        # 3. Guardar en DB para reconciliación
        db_result = self.action_layer.save_to_db(
            table="bank_statements",
            data=extracted_fields,
            operation="insert"
        )
        actions.append(db_result.to_dict())
        
        return actions
    
    def _generate_statement_report_html(self, extracted_fields: Dict[str, Any]) -> str:
        """Genera contenido HTML para el reporte."""
        html = f"<h2>Análisis de Extractos Bancarios</h2>"
        html += f"<p><strong>Total de transacciones:</strong> {extracted_fields.get('total_transactions', 0)}</p>"
        html += f"<p><strong>Total ingresos:</strong> ${extracted_fields.get('total_income', 0):,.2f}</p>"
        html += f"<p><strong>Total egresos:</strong> ${extracted_fields.get('total_expenses', 0):,.2f}</p>"
        html += f"<p><strong>Balance neto:</strong> ${extracted_fields.get('total_income', 0) - extracted_fields.get('total_expenses', 0):,.2f}</p>"
        
        return html

