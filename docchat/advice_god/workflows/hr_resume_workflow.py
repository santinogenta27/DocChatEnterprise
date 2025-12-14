"""HR Resume Workflow - Procesamiento de CVs y documentos de recursos humanos."""

from __future__ import annotations

from typing import List, Dict, Any
import json
from datetime import datetime

from .base_workflow import BaseWorkflow
from ..orchestrator.decision_orchestrator import ClassifiedDocument


class HRResumeWorkflow(BaseWorkflow):
    """
    Workflow para CVs y documentos HR.
    
    Extrae:
    - Skills
    - Experiencia
    - Seniority
    - Educación
    
    Acciones:
    - Matchear contra job description
    - Score del candidato
    """
    
    def extract_fields(self, documents: List[ClassifiedDocument]) -> Dict[str, Any]:
        """Extrae campos de CVs."""
        extracted = {
            "resumes": [],
            "total_resumes": len(documents)
        }
        
        for doc in documents:
            text = doc.text
            metadata = doc.document.metadata
            
            prompt = f"""Extrae los siguientes campos de este currículum:

TEXTO DEL CV:
{text[:8000]}

Extrae y devuelve ÚNICAMENTE un JSON válido con estos campos:
{{
    "candidate_name": "nombre del candidato o N/A",
    "email": "email o N/A",
    "phone": "teléfono o N/A",
    "location": "ubicación o N/A",
    "years_of_experience": número o 0,
    "seniority_level": "junior, mid, senior, executive o N/A",
    "skills": [
        "skill1",
        "skill2"
    ],
    "languages": [
        {{
            "language": "idioma",
            "level": "nivel (nativo, avanzado, intermedio, básico)"
        }}
    ],
    "education": [
        {{
            "degree": "título",
            "institution": "institución",
            "year": "año o N/A"
        }}
    ],
    "experience": [
        {{
            "company": "empresa",
            "position": "cargo",
            "duration": "duración",
            "description": "descripción"
        }}
    ],
    "certifications": [
        "certificación 1"
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
                
                resume_data = json.loads(response)
                resume_data["source_file"] = metadata.get("source", "unknown")
                resume_data["confidence"] = doc.confidence
                
                # Calcular score básico
                resume_data["score"] = self._calculate_resume_score(resume_data)
                
                extracted["resumes"].append(resume_data)
                
            except Exception as e:
                extracted["resumes"].append({
                    "candidate_name": "N/A",
                    "source_file": metadata.get("source", "unknown"),
                    "confidence": 0.3,
                    "score": 0.0
                })
        
        return extracted
    
    def _calculate_resume_score(self, resume_data: Dict[str, Any]) -> float:
        """Calcula un score básico del CV."""
        score = 0.0
        
        # Experiencia (máx 40 puntos)
        years = resume_data.get("years_of_experience", 0)
        score += min(years * 2, 40)
        
        # Skills (máx 20 puntos)
        skills_count = len(resume_data.get("skills", []))
        score += min(skills_count * 2, 20)
        
        # Educación (máx 20 puntos)
        education_count = len(resume_data.get("education", []))
        score += min(education_count * 5, 20)
        
        # Certificaciones (máx 10 puntos)
        certs_count = len(resume_data.get("certifications", []))
        score += min(certs_count * 2, 10)
        
        # Experiencia laboral (máx 10 puntos)
        exp_count = len(resume_data.get("experience", []))
        score += min(exp_count * 2, 10)
        
        return min(score, 100.0)
    
    def validate(self, extracted_fields: Dict[str, Any]) -> tuple[bool, List[str]]:
        """Valida los campos extraídos."""
        errors = []
        
        if not extracted_fields.get("resumes"):
            errors.append("No se encontraron CVs")
            return False, errors
        
        for resume in extracted_fields["resumes"]:
            if not resume.get("candidate_name") or resume.get("candidate_name") == "N/A":
                errors.append("Nombre del candidato no encontrado")
        
        return len(errors) == 0, errors
    
    def execute_actions(self, extracted_fields: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Ejecuta acciones automáticas."""
        actions = []
        
        # 1. Generar JSON
        json_result = self.action_layer.produce_json(
            data=extracted_fields,
            filename=f"resumes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        actions.append(json_result.to_dict())
        
        # 2. Para cada CV con score alto, crear alerta
        for resume in extracted_fields.get("resumes", []):
            score = resume.get("score", 0)
            if score >= 70:
                alert_result = self.action_layer.emit_alert(
                    level="info",
                    message=f"Candidato destacado: {resume.get('candidate_name', 'N/A')} (Score: {score:.1f})",
                    channel="email",
                    metadata={"candidate": resume.get("candidate_name"), "score": score}
                )
                actions.append(alert_result.to_dict())
        
        # 3. Generar reporte HTML
        html_content = self._generate_resume_report_html(extracted_fields)
        report_result = self.action_layer.generate_report_html(
            title="Análisis de CVs",
            content=html_content,
            filename=f"resume_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        )
        actions.append(report_result.to_dict())
        
        return actions
    
    def _generate_resume_report_html(self, extracted_fields: Dict[str, Any]) -> str:
        """Genera contenido HTML para el reporte."""
        html = f"<h2>Análisis de {extracted_fields.get('total_resumes', 0)} CVs</h2>"
        
        # Ordenar por score
        resumes = sorted(
            extracted_fields.get("resumes", []),
            key=lambda x: x.get("score", 0),
            reverse=True
        )
        
        html += "<table border='1' cellpadding='5' style='border-collapse: collapse; width: 100%;'>"
        html += "<tr><th>Candidato</th><th>Experiencia (años)</th><th>Seniority</th><th>Skills</th><th>Score</th></tr>"
        
        for resume in resumes:
            html += f"""
            <tr>
                <td>{resume.get('candidate_name', 'N/A')}</td>
                <td>{resume.get('years_of_experience', 0)}</td>
                <td>{resume.get('seniority_level', 'N/A')}</td>
                <td>{len(resume.get('skills', []))}</td>
                <td><strong>{resume.get('score', 0):.1f}</strong></td>
            </tr>
            """
        
        html += "</table>"
        
        return html

