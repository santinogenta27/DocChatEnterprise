"""
Situational Reasoning Module - Instruction-Grounded, Context-Aware Reasoning
Implements Agentic Document Reasoning with:
- Synthesis: Combining info across many documents
- Abstraction: Summarizing at high mental level
- Inference: Reading between the lines
- Recommendation: Strategic advice
- Decision Support: Actionable insights
"""

from __future__ import annotations

import json
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

from langchain_core.language_models import BaseLanguageModel
from langchain_core.documents import Document


class ReasoningType(Enum):
    """Types of strategic reasoning"""
    SITUATION_ANALYSIS = "situation_analysis"  # "¿Qué nos está pasando?"
    IMPROVEMENT_RECOMMENDATIONS = "improvement"  # "¿Cómo podemos mejorar?"
    ACTION_PLAN = "action_plan"  # "¿Qué deberíamos hacer?"
    STRATEGIC_INSIGHTS = "strategic_insights"  # General strategic analysis
    DECISION_SUPPORT = "decision_support"  # Decision-making support


@dataclass
class SituationalInsight:
    """Represents a strategic insight extracted from documents"""
    category: str  # e.g., "Problem", "Opportunity", "Risk", "Strength"
    description: str
    evidence: List[str]  # Quotes from documents supporting this insight
    confidence: float  # 0.0 to 1.0
    priority: str  # "high", "medium", "low"
    impact: str  # "positive", "negative", "neutral"


@dataclass
class StrategicRecommendation:
    """Represents a strategic recommendation"""
    title: str
    description: str
    rationale: str  # Why this recommendation
    expected_impact: str
    implementation_steps: List[str]
    priority: str
    estimated_effort: str  # "low", "medium", "high"
    risk_level: str


@dataclass
class SituationAssessment:
    """Complete situation assessment from documents"""
    current_state: str  # What is happening
    key_findings: List[SituationalInsight]
    problems_identified: List[SituationalInsight]
    opportunities_identified: List[SituationalInsight]
    risks_identified: List[SituationalInsight]
    recommendations: List[StrategicRecommendation]
    synthesis: str  # High-level synthesis
    confidence_score: float


class SituationalReasoner:
    """
    Performs instruction-grounded, context-aware reasoning over documents.
    Implements Agentic Document Reasoning with synthesis, abstraction, inference,
    and strategic recommendations.
    """
    
    def __init__(
        self,
        llm: BaseLanguageModel,
        config: Any
    ):
        self.llm = llm
        self.config = config
        
    def _detect_reasoning_type(self, query: str) -> ReasoningType:
        """Detect what type of strategic reasoning is requested"""
        query_lower = query.lower()
        
        # Situation analysis patterns
        situation_patterns = [
            "qué nos está pasando",
            "what is happening",
            "cuál es la situación",
            "what's going on",
            "qué está pasando",
            "current state",
            "situación actual"
        ]
        
        # Improvement patterns
        improvement_patterns = [
            "cómo podemos mejorar",
            "how can we improve",
            "qué mejoras",
            "what improvements",
            "cómo mejorar",
            "mejoras posibles",
            "optimización"
        ]
        
        # Action plan patterns
        action_patterns = [
            "qué deberíamos hacer",
            "what should we do",
            "qué hacer",
            "action plan",
            "plan de acción",
            "próximos pasos",
            "next steps",
            "recomendaciones"
        ]
        
        # Decision support patterns
        decision_patterns = [
            "qué decisión",
            "what decision",
            "deberíamos",
            "should we",
            "decision support",
            "apoyo decisión"
        ]
        
        if any(pattern in query_lower for pattern in situation_patterns):
            return ReasoningType.SITUATION_ANALYSIS
        elif any(pattern in query_lower for pattern in improvement_patterns):
            return ReasoningType.IMPROVEMENT_RECOMMENDATIONS
        elif any(pattern in query_lower for pattern in action_patterns):
            return ReasoningType.ACTION_PLAN
        elif any(pattern in query_lower for pattern in decision_patterns):
            return ReasoningType.DECISION_SUPPORT
        else:
            return ReasoningType.STRATEGIC_INSIGHTS
    
    def _extract_relevant_documents(
        self,
        documents: List[Document],
        query: str,
        reasoning_type: ReasoningType
    ) -> List[Document]:
        """Extract most relevant documents for strategic reasoning"""
        # For strategic reasoning, we want a broad set of documents
        # to enable synthesis across multiple sources
        if len(documents) <= 20:
            return documents
        
        # For large document sets, prioritize:
        # 1. Recent documents
        # 2. Documents with strategic keywords
        # 3. Documents with metrics/numbers (indicating data-driven content)
        
        strategic_keywords = [
            "problema", "problem", "oportunidad", "opportunity",
            "riesgo", "risk", "mejora", "improvement", "recomendación",
            "recommendation", "estrategia", "strategy", "objetivo", "goal",
            "resultado", "result", "performance", "rendimiento", "eficiencia",
            "efficiency", "calidad", "quality", "cliente", "customer",
            "ventas", "sales", "ingresos", "revenue", "costos", "costs"
        ]
        
        scored_docs = []
        for doc in documents:
            score = 0.0
            content_lower = doc.page_content.lower()
            
            # Check for strategic keywords
            keyword_matches = sum(1 for kw in strategic_keywords if kw in content_lower)
            score += keyword_matches * 0.1
            
            # Prefer longer documents (more context)
            score += min(len(doc.page_content) / 10000, 0.3)
            
            # Check for numbers/metrics (data-driven content)
            if any(char.isdigit() for char in doc.page_content[:500]):
                score += 0.2
            
            scored_docs.append((score, doc))
        
        # Sort by score and take top documents
        scored_docs.sort(key=lambda x: x[0], reverse=True)
        return [doc for _, doc in scored_docs[:50]]  # Top 50 for synthesis
    
    def _generate_situation_analysis(
        self,
        documents: List[Document],
        query: str
    ) -> SituationAssessment:
        """Generate comprehensive situation analysis"""
        
        # Extract relevant documents
        relevant_docs = self._extract_relevant_documents(
            documents, query, ReasoningType.SITUATION_ANALYSIS
        )
        
        # Build context from documents
        context = "\n\n".join([
            f"[Document {i+1}]\n{doc.page_content[:2000]}"
            for i, doc in enumerate(relevant_docs[:30])  # Limit context size
        ])
        
        prompt = f"""Eres un consultor estratégico de nivel McKinsey analizando una situación empresarial compleja.

DOCUMENTOS ANALIZADOS ({len(relevant_docs)} documentos):
{context}

PREGUNTA DEL CLIENTE: {query}

Tu tarea es realizar un análisis situacional completo y generar insights estratégicos de alto nivel.

Realiza el siguiente análisis:

1. **ESTADO ACTUAL (Current State)**: 
   - ¿Qué está pasando actualmente?
   - Describe la situación en términos claros y concisos
   - Identifica los factores clave que están influyendo

2. **HALLAZGOS CLAVE (Key Findings)**:
   - Extrae los insights más importantes de los documentos
   - Identifica patrones, tendencias, y anomalías
   - Categoriza cada hallazgo como: Problema, Oportunidad, Riesgo, o Fortaleza

3. **PROBLEMAS IDENTIFICADOS**:
   - Lista los problemas críticos encontrados
   - Para cada problema, proporciona evidencia específica (citas de documentos)
   - Asigna prioridad (alta, media, baja) y nivel de confianza (0.0-1.0)

4. **OPORTUNIDADES IDENTIFICADAS**:
   - Lista las oportunidades de mejora o crecimiento
   - Para cada oportunidad, proporciona evidencia específica
   - Evalúa el impacto potencial (positivo, negativo, neutral)

5. **RIESGOS IDENTIFICADOS**:
   - Identifica riesgos potenciales o amenazas
   - Evalúa la probabilidad y el impacto de cada riesgo

6. **SÍNTESIS DE ALTO NIVEL**:
   - Proporciona una síntesis ejecutiva que combine toda la información
   - Lee entre líneas para identificar insights no obvios
   - Conecta información de múltiples documentos para crear una visión holística

7. **RECOMENDACIONES ESTRATÉGICAS**:
   - Genera recomendaciones accionables basadas en el análisis
   - Para cada recomendación, incluye:
     * Título claro
     * Descripción detallada
     * Justificación (por qué esta recomendación)
     * Impacto esperado
     * Pasos de implementación
     * Prioridad (alta, media, baja)
     * Esfuerzo estimado (bajo, medio, alto)
     * Nivel de riesgo

IMPORTANTE:
- Sé específico y basado en evidencia (cita documentos cuando sea posible)
- No inventes información que no esté en los documentos
- Proporciona insights de alto nivel, no solo resúmenes
- Piensa como un consultor estratégico senior
- Conecta información de múltiples fuentes para crear insights únicos

Devuelve tu respuesta en formato JSON estructurado con las siguientes secciones:
{{
    "current_state": "Descripción del estado actual",
    "key_findings": [
        {{
            "category": "Problema|Oportunidad|Riesgo|Fortaleza",
            "description": "Descripción del hallazgo",
            "evidence": ["Cita 1", "Cita 2"],
            "confidence": 0.85,
            "priority": "alta|media|baja",
            "impact": "positivo|negativo|neutral"
        }}
    ],
    "problems_identified": [...],
    "opportunities_identified": [...],
    "risks_identified": [...],
    "recommendations": [
        {{
            "title": "Título de la recomendación",
            "description": "Descripción detallada",
            "rationale": "Por qué esta recomendación",
            "expected_impact": "Impacto esperado",
            "implementation_steps": ["Paso 1", "Paso 2"],
            "priority": "alta|media|baja",
            "estimated_effort": "bajo|medio|alto",
            "risk_level": "bajo|medio|alto"
        }}
    ],
    "synthesis": "Síntesis ejecutiva de alto nivel",
    "confidence_score": 0.85
}}
"""
        
        try:
            response = self.llm.invoke(prompt)
            content = response.content.strip()
            
            # Clean JSON response
            if content.startswith("```json"):
                content = content.replace("```json", "").replace("```", "").strip()
            elif content.startswith("```"):
                content = content.replace("```", "").strip()
            
            # Parse JSON
            data = json.loads(content)
            
            # Convert to structured objects
            key_findings = [
                SituationalInsight(**item) for item in data.get("key_findings", [])
            ]
            problems = [
                SituationalInsight(**item) for item in data.get("problems_identified", [])
            ]
            opportunities = [
                SituationalInsight(**item) for item in data.get("opportunities_identified", [])
            ]
            risks = [
                SituationalInsight(**item) for item in data.get("risks_identified", [])
            ]
            recommendations = [
                StrategicRecommendation(**item) for item in data.get("recommendations", [])
            ]
            
            return SituationAssessment(
                current_state=data.get("current_state", ""),
                key_findings=key_findings,
                problems_identified=problems,
                opportunities_identified=opportunities,
                risks_identified=risks,
                recommendations=recommendations,
                synthesis=data.get("synthesis", ""),
                confidence_score=data.get("confidence_score", 0.0)
            )
            
        except Exception as e:
            # Fallback to simple analysis
            return SituationAssessment(
                current_state=f"Error en análisis: {str(e)}",
                key_findings=[],
                problems_identified=[],
                opportunities_identified=[],
                risks_identified=[],
                recommendations=[],
                synthesis="",
                confidence_score=0.0
            )
    
    def _format_assessment_report(
        self,
        assessment: SituationAssessment,
        reasoning_type: ReasoningType
    ) -> str:
        """Format situation assessment as a readable report"""
        
        report = []
        
        # Header based on reasoning type
        if reasoning_type == ReasoningType.SITUATION_ANALYSIS:
            report.append("# 📊 ANÁLISIS SITUACIONAL")
        elif reasoning_type == ReasoningType.IMPROVEMENT_RECOMMENDATIONS:
            report.append("# 🚀 RECOMENDACIONES DE MEJORA")
        elif reasoning_type == ReasoningType.ACTION_PLAN:
            report.append("# ✅ PLAN DE ACCIÓN ESTRATÉGICO")
        elif reasoning_type == ReasoningType.DECISION_SUPPORT:
            report.append("# 🎯 APOYO A LA DECISIÓN")
        else:
            report.append("# 🧠 ANÁLISIS ESTRATÉGICO")
        
        report.append("")
        report.append("---")
        report.append("")
        
        # Current State
        report.append("## 📍 ESTADO ACTUAL")
        report.append(assessment.current_state)
        report.append("")
        
        # Key Findings
        if assessment.key_findings:
            report.append("## 🔍 HALLAZGOS CLAVE")
            for i, finding in enumerate(assessment.key_findings, 1):
                report.append(f"### {i}. {finding.category.upper()}: {finding.description}")
                if finding.evidence:
                    report.append("**Evidencia:**")
                    for evidence in finding.evidence[:3]:  # Limit to 3 quotes
                        report.append(f"- \"{evidence}\"")
                report.append(f"**Prioridad:** {finding.priority.upper()} | **Confianza:** {finding.confidence*100:.0f}%")
                report.append("")
        
        # Problems
        if assessment.problems_identified:
            report.append("## ⚠️ PROBLEMAS IDENTIFICADOS")
            for i, problem in enumerate(assessment.problems_identified, 1):
                report.append(f"### {i}. {problem.description}")
                if problem.evidence:
                    report.append("**Evidencia:**")
                    for evidence in problem.evidence[:2]:
                        report.append(f"- \"{evidence}\"")
                report.append(f"**Prioridad:** {problem.priority.upper()} | **Impacto:** {problem.impact.upper()}")
                report.append("")
        
        # Opportunities
        if assessment.opportunities_identified:
            report.append("## 💡 OPORTUNIDADES IDENTIFICADAS")
            for i, opp in enumerate(assessment.opportunities_identified, 1):
                report.append(f"### {i}. {opp.description}")
                if opp.evidence:
                    report.append("**Evidencia:**")
                    for evidence in opp.evidence[:2]:
                        report.append(f"- \"{evidence}\"")
                report.append(f"**Prioridad:** {opp.priority.upper()} | **Impacto:** {opp.impact.upper()}")
                report.append("")
        
        # Risks
        if assessment.risks_identified:
            report.append("## 🚨 RIESGOS IDENTIFICADOS")
            for i, risk in enumerate(assessment.risks_identified, 1):
                report.append(f"### {i}. {risk.description}")
                if risk.evidence:
                    report.append("**Evidencia:**")
                    for evidence in risk.evidence[:2]:
                        report.append(f"- \"{evidence}\"")
                report.append(f"**Prioridad:** {risk.priority.upper()}")
                report.append("")
        
        # Recommendations
        if assessment.recommendations:
            report.append("## 🎯 RECOMENDACIONES ESTRATÉGICAS")
            for i, rec in enumerate(assessment.recommendations, 1):
                report.append(f"### {i}. {rec.title}")
                report.append(f"**Descripción:** {rec.description}")
                report.append(f"**Justificación:** {rec.rationale}")
                report.append(f"**Impacto Esperado:** {rec.expected_impact}")
                report.append(f"**Prioridad:** {rec.priority.upper()} | **Esfuerzo:** {rec.estimated_effort.upper()} | **Riesgo:** {rec.risk_level.upper()}")
                if rec.implementation_steps:
                    report.append("**Pasos de Implementación:**")
                    for step in rec.implementation_steps:
                        report.append(f"- {step}")
                report.append("")
        
        # Synthesis
        if assessment.synthesis:
            report.append("## 🧠 SÍNTESIS EJECUTIVA")
            report.append(assessment.synthesis)
            report.append("")
        
        # Confidence Score
        report.append("---")
        report.append(f"**Nivel de Confianza del Análisis:** {assessment.confidence_score*100:.0f}%")
        report.append("")
        report.append("*Análisis generado mediante reasoning estratégico sobre documentos*")
        
        return "\n".join(report)
    
    def analyze_situation(
        self,
        query: str,
        documents: List[Document]
    ) -> Tuple[str, SituationAssessment]:
        """
        Main method: Performs instruction-grounded, context-aware reasoning.
        
        Returns:
            Tuple of (formatted_report, situation_assessment)
        """
        # Detect reasoning type
        reasoning_type = self._detect_reasoning_type(query)
        
        # Generate situation analysis
        assessment = self._generate_situation_analysis(documents, query)
        
        # Format as report
        report = self._format_assessment_report(assessment, reasoning_type)
        
        return report, assessment












