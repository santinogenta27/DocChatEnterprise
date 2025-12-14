"""Generic Workflow - Workflow genérico para documentos no identificados."""

from __future__ import annotations

from typing import List, Dict, Any
import json
from datetime import datetime

from .base_workflow import BaseWorkflow
from ..orchestrator.decision_orchestrator import ClassifiedDocument


class GenericWorkflow(BaseWorkflow):
    """
    Workflow genérico para documentos no clasificados.
    
    Extrae:
    - Información esencial
    - Metadatos básicos
    
    Acciones:
    - Generar JSON limpio
    - Reporte básico
    """
    
    def extract_fields(self, documents: List[ClassifiedDocument]) -> Dict[str, Any]:
        """Extrae información genérica de documentos."""
        extracted = {
            "documents": [],
            "total_documents": len(documents)
        }
        
        for doc in documents:
            text = doc.text
            metadata = doc.document.metadata
            
            prompt = f"""Extrae información esencial de este documento:

TEXTO DEL DOCUMENTO:
{text[:5000]}

Extrae y devuelve ÚNICAMENTE un JSON válido con estos campos:
{{
    "document_title": "título o tema principal del documento",
    "document_type": "tipo inferido del documento",
    "key_entities": [
        "entidad 1",
        "entidad 2"
    ],
    "key_dates": [
        "fecha 1",
        "fecha 2"
    ],
    "key_amounts": [
        "monto 1",
        "monto 2"
    ],
    "summary": "resumen breve del documento (2-3 oraciones)",
    "main_topics": [
        "tema 1",
        "tema 2"
    ]
}}

IMPORTANTE:
- Devuelve SOLO el JSON, sin explicaciones"""
            
            try:
                response = self.llm.invoke(prompt).content.strip()
                
                if response.startswith("```json"):
                    response = response.replace("```json", "").replace("```", "").strip()
                elif response.startswith("```"):
                    response = response.replace("```", "").strip()
                
                doc_data = json.loads(response)
                doc_data["source_file"] = metadata.get("source", "unknown")
                doc_data["confidence"] = doc.confidence
                
                extracted["documents"].append(doc_data)
                
            except Exception as e:
                # Fallback mínimo
                extracted["documents"].append({
                    "document_title": "Documento sin título",
                    "source_file": metadata.get("source", "unknown"),
                    "confidence": 0.2,
                    "summary": "No se pudo extraer información del documento"
                })
        
        return extracted
    
    def validate(self, extracted_fields: Dict[str, Any]) -> tuple[bool, List[str]]:
        """Valida los campos extraídos."""
        errors = []
        
        if not extracted_fields.get("documents"):
            errors.append("No se encontraron documentos")
            return False, errors
        
        return len(errors) == 0, errors
    
    def execute_actions(self, extracted_fields: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Ejecuta acciones automáticas."""
        actions = []
        
        # 1. Generar JSON
        json_result = self.action_layer.produce_json(
            data=extracted_fields,
            filename=f"generic_documents_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        actions.append(json_result.to_dict())
        
        # 2. Generar reporte HTML básico
        html_content = self._generate_generic_report_html(extracted_fields)
        report_result = self.action_layer.generate_report_html(
            title="Análisis de Documentos Genéricos",
            content=html_content,
            filename=f"generic_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        )
        actions.append(report_result.to_dict())
        
        return actions
    
    def _generate_generic_report_html(self, extracted_fields: Dict[str, Any]) -> str:
        """Genera contenido HTML para el reporte."""
        html = f"<h2>Análisis de {extracted_fields.get('total_documents', 0)} Documentos</h2>"
        
        for doc in extracted_fields.get("documents", []):
            html += f"<h3>{doc.get('document_title', 'Sin título')}</h3>"
            html += f"<p><strong>Tipo:</strong> {doc.get('document_type', 'N/A')}</p>"
            html += f"<p><strong>Resumen:</strong> {doc.get('summary', 'N/A')}</p>"
            
            topics = doc.get("main_topics", [])
            if topics:
                html += "<p><strong>Temas principales:</strong> " + ", ".join(topics) + "</p>"
            
            html += "<hr>"
        
        return html

