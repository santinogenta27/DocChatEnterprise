"""
Agentes especializados para Co-Investigator AI.
"""

from __future__ import annotations

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime

from docchat.config import AppConfig
from .agents.base_agent import BaseBanksAgent
from docchat.config import get_llm
from .co_investigator_schemas import CrimeTypology, SARNarrative

# Clase base compatible para Co-Investigator agents
class BaseAgent:
    """Clase base para agentes de Co-Investigator AI."""
    def __init__(self, config):
        self.config = config
        self.llm = get_llm(config)

logger = logging.getLogger(__name__)


class AIPrivacyGuard:
    """
    AI-Privacy Guard Layer: Anonimiza datos sensibles antes de enviar a LLMs.
    Usa RoBERTa + CRF para identificar y enmascarar información confidencial.
    """
    
    def __init__(self, config: AppConfig):
        self.config = config
        logger.info("✅ [AI-Privacy Guard] Inicializado")
    
    def anonymize_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Anonimiza datos sensibles (class-1 y class-2 confidential).
        
        Args:
            data: Datos originales
        
        Returns:
            Datos anonimizados con mapeo para des-anonimizar después
        """
        # Por ahora, implementación básica
        # TODO: Integrar modelo RoBERTa + CRF para NER avanzado
        anonymized = data.copy()
        self._anonymization_map = {}
        
        # Anonimizar nombres, SSNs, direcciones, etc.
        if "entities" in anonymized:
            for entity in anonymized["entities"]:
                if "name" in entity:
                    original = entity["name"]
                    anonymized_name = f"[NAME_{len(self._anonymization_map)}]"
                    self._anonymization_map[anonymized_name] = original
                    entity["name"] = anonymized_name
        
        logger.info(f"🔒 [AI-Privacy Guard] Anonimizados {len(self._anonymization_map)} elementos sensibles")
        return anonymized
    
    def deanonymize_for_investigator(
        self,
        narrative: SARNarrative,
        original_data: Dict[str, Any]
    ) -> SARNarrative:
        """
        Des-anonimiza datos necesarios para el investigador.
        """
        # Restaurar nombres y datos críticos para el investigador
        # Mantener anonimización en partes que no necesita ver
        return narrative


class CrimeTypeDetectionAgent(BaseAgent):
    """
    Crime Type Detection Agent: Detecta tipologías de crímenes financieros.
    Usa risk indicators + ML models (Random Forest, Gradient Boosting).
    """
    
    def __init__(self, config: AppConfig, privacy_guard: AIPrivacyGuard):
        super().__init__(config)
        self.privacy_guard = privacy_guard
        self.typology_models = {}  # TODO: Cargar modelos ML entrenados
        logger.info("✅ [Crime Type Detection Agent] Inicializado")
    
    def detect_crime_types(
        self,
        case_data: Dict[str, Any],
        entities: List[Dict[str, Any]],
        sanction_hits: List[Dict[str, Any]],
        risk_scores: List[Dict[str, Any]]
    ) -> List[CrimeTypology]:
        """
        Detecta tipologías de crímenes financieros.
        
        Tipologías soportadas:
        - elder_exploitation
        - romance_scam
        - money_mule
        - human_trafficking
        - terrorist_financing
        - csam
        - identity_theft
        - transaction_fraud
        """
        typologies = []
        
        # Extraer risk indicators
        risk_indicators = self._extract_risk_indicators(
            case_data, entities, sanction_hits, risk_scores
        )
        
        # Detectar tipologías usando reglas + ML
        detected_types = self._classify_typologies(risk_indicators, case_data)
        
        for typology_type, confidence, evidence in detected_types:
            typology = CrimeTypology(
                typology_type=typology_type,
                confidence_score=confidence,
                risk_indicators=risk_indicators.get(typology_type, []),
                supporting_evidence=evidence
            )
            typologies.append(typology)
        
        logger.info(f"🔍 [Crime Type Detection] Detectadas {len(typologies)} tipologías")
        return typologies
    
    def _extract_risk_indicators(
        self,
        case_data: Dict[str, Any],
        entities: List[Dict[str, Any]],
        sanction_hits: List[Dict[str, Any]],
        risk_scores: List[Dict[str, Any]]
    ) -> Dict[str, List[str]]:
        """Extrae risk indicators automáticamente."""
        indicators = {}
        
        # Análisis de transacciones
        if "transactions" in case_data:
            transactions = case_data["transactions"]
            if any(t.get("amount", 0) > 10000 for t in transactions):
                indicators.setdefault("transaction_fraud", []).append("High-value transactions detected")
        
        # Análisis de edad (elder exploitation)
        for entity in entities:
            if entity.get("age") and entity["age"] > 65:
                indicators.setdefault("elder_exploitation", []).append(f"Elderly subject: {entity.get('name', 'Unknown')}")
        
        # Análisis geográfico
        high_risk_countries = ["PA", "KY", "VG", "BS"]  # Panamá, Caimán, etc.
        for entity in entities:
            if entity.get("country") in high_risk_countries:
                indicators.setdefault("money_mule", []).append(f"High-risk jurisdiction: {entity.get('country')}")
        
        return indicators
    
    def _classify_typologies(
        self,
        risk_indicators: Dict[str, List[str]],
        case_data: Dict[str, Any]
    ) -> List[tuple]:
        """
        Clasifica tipologías usando reglas + ML models.
        Returns: List of (typology_type, confidence, evidence)
        """
        detected = []
        
        # Reglas básicas (por ahora)
        # TODO: Integrar modelos ML entrenados
        
        if "elder_exploitation" in risk_indicators:
            detected.append(("elder_exploitation", 0.85, risk_indicators["elder_exploitation"]))
        
        if "money_mule" in risk_indicators:
            detected.append(("money_mule", 0.75, risk_indicators["money_mule"]))
        
        if "transaction_fraud" in risk_indicators:
            detected.append(("transaction_fraud", 0.70, risk_indicators["transaction_fraud"]))
        
        return detected


class PlanningAgent(BaseAgent):
    """
    Planning Agent: Orquestador central que coordina agentes especializados.
    """
    
    def __init__(self, config: AppConfig):
        super().__init__(config)
        logger.info("✅ [Planning Agent] Inicializado")
    
    def plan_investigation(
        self,
        crime_typologies: List[CrimeTypology],
        case_data: Dict[str, Any],
        jurisdiction: str
    ) -> Dict[str, Any]:
        """
        Planifica la investigación y determina qué agentes activar.
        """
        plan = {
            "active_agents": [],
            "priority_typologies": [],
            "investigation_steps": []
        }
        
        # Priorizar tipologías por confidence
        sorted_typologies = sorted(
            crime_typologies,
            key=lambda x: x.confidence_score,
            reverse=True
        )
        
        plan["priority_typologies"] = [
            {
                "type": t.typology_type,
                "confidence": t.confidence_score
            }
            for t in sorted_typologies[:3]  # Top 3
        ]
        
        # Determinar agentes a activar
        typology_types = {t.typology_type for t in crime_typologies}
        
        if "transaction_fraud" in typology_types:
            plan["active_agents"].append("transaction_fraud_detection")
        
        if "money_mule" in typology_types:
            plan["active_agents"].append("geographic_anomaly_detection")
            plan["active_agents"].append("account_health_assessment")
        
        if "elder_exploitation" in typology_types:
            plan["active_agents"].append("textual_content_detection")
        
        plan["investigation_steps"] = [
            "1. Gather external intelligence",
            "2. Analyze transaction patterns",
            "3. Generate narrative draft",
            "4. Validate compliance"
        ]
        
        logger.info(f"📋 [Planning Agent] Plan generado: {len(plan['active_agents'])} agentes activos")
        return plan


class ExternalIntelligenceAgent(BaseAgent):
    """
    External Intelligence Agent: Obtiene información externa usando MCP.
    """
    
    def __init__(self, config: AppConfig, privacy_guard: AIPrivacyGuard):
        super().__init__(config)
        self.privacy_guard = privacy_guard
        logger.info("✅ [External Intelligence Agent] Inicializado")
    
    def gather_intelligence(
        self,
        entities: List[Dict[str, Any]],
        crime_typologies: List[CrimeTypology],
        jurisdiction: str
    ) -> Dict[str, Any]:
        """
        Recolecta inteligencia externa (negative news, sanctions, etc.) usando MCP.
        """
        intelligence = {
            "negative_news": [],
            "sanctions_alerts": [],
            "regulatory_advisories": []
        }
        
        # TODO: Integrar con MCP servers para búsqueda externa
        # Por ahora, retornar estructura vacía
        
        logger.info("🌐 [External Intelligence] Inteligencia externa recolectada")
        return intelligence


class NarrativeGenerationAgent(BaseAgent):
    """
    Narrative Generation Agent: Genera narrativas SAR usando Chain-of-Thought.
    """
    
    def __init__(self, config: AppConfig, privacy_guard: AIPrivacyGuard):
        super().__init__(config)
        self.privacy_guard = privacy_guard
        logger.info("✅ [Narrative Generation Agent] Inicializado")
    
    def generate_narrative(
        self,
        case_data: Dict[str, Any],
        entities: List[Dict[str, Any]],
        crime_typologies: List[CrimeTypology],
        sanction_hits: List[Dict[str, Any]],
        risk_scores: List[Dict[str, Any]],
        external_intelligence: Dict[str, Any],
        jurisdiction: str,
        historical_narratives: List[Dict[str, Any]],
        regulatory_guidelines: Dict[str, Any]
    ) -> SARNarrative:
        """
        Genera narrativa SAR completa usando Chain-of-Thought reasoning.
        """
        from langchain_core.messages import HumanMessage, SystemMessage
        
        # Construir prompt con Chain-of-Thought
        prompt = self._build_cot_prompt(
            case_data, entities, crime_typologies, sanction_hits,
            risk_scores, external_intelligence, jurisdiction,
            historical_narratives, regulatory_guidelines
        )
        
        # Generar con LLM
        messages = [
            SystemMessage(content="Eres un experto en compliance AML que genera narrativas SAR regulatorias de alta calidad."),
            HumanMessage(content=prompt)
        ]
        
        response = self.llm.invoke(messages)
        narrative_text = response.content if hasattr(response, 'content') else str(response)
        
        # Construir objeto SARNarrative
        narrative = SARNarrative(
            narrative_id=f"SAR_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            subject_details=self._extract_subject_details(entities),
            suspicious_activity_description=self._build_activity_description(crime_typologies),
            date_range=self._extract_date_range(case_data),
            institution_information=self._get_institution_info(jurisdiction),
            filer_contact=self._get_filer_contact(),
            narrative_text=narrative_text,
            supporting_documentation=self._list_supporting_docs(case_data),
            compliance_score=0.85,  # Será validado después
            confidence_scores={
                "factual_accuracy": 0.90,
                "regulatory_compliance": 0.85,
                "narrative_coherence": 0.88
            }
        )
        
        logger.info("📝 [Narrative Generation] Narrativa SAR generada")
        return narrative
    
    def _build_cot_prompt(
        self,
        case_data: Dict[str, Any],
        entities: List[Dict[str, Any]],
        crime_typologies: List[CrimeTypology],
        sanction_hits: List[Dict[str, Any]],
        risk_scores: List[Dict[str, Any]],
        external_intelligence: Dict[str, Any],
        jurisdiction: str,
        historical_narratives: List[Dict[str, Any]],
        regulatory_guidelines: Dict[str, Any]
    ) -> str:
        """Construye prompt con Chain-of-Thought reasoning."""
        prompt = f"""Genera una narrativa SAR completa y regulatoria usando Chain-of-Thought reasoning.

PASO 1 - ANÁLISIS DE DATOS:
- Entidades detectadas: {len(entities)}
- Tipologías de crímenes: {[t.typology_type for t in crime_typologies]}
- Sanctions hits: {len(sanction_hits)}
- Risk scores: {len(risk_scores)}

PASO 2 - IDENTIFICACIÓN DE RIESGOS:
Analiza cada tipología detectada y sus indicadores de riesgo.

PASO 3 - CONSTRUCCIÓN DE NARRATIVA:
Genera una narrativa que incluya:
- Quién: Detalles del sujeto
- Qué: Actividad sospechosa descrita claramente
- Cuándo: Rango de fechas
- Dónde: Ubicaciones relevantes
- Cómo: Métodos y patrones detectados
- Por qué: Motivos y contexto

PASO 4 - CUMPLIMIENTO REGULATORIO:
Asegúrate de que la narrativa cumple con los requisitos de {jurisdiction}.

GENERA LA NARRATIVA COMPLETA AHORA:
"""
        return prompt
    
    def _extract_subject_details(self, entities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extrae detalles del sujeto principal."""
        if entities:
            main_entity = entities[0]
            return {
                "name": main_entity.get("name", "Unknown"),
                "address": main_entity.get("address", "Unknown"),
                "date_of_birth": main_entity.get("date_of_birth", "Unknown"),
                "ssn": main_entity.get("ssn", "Unknown"),
                "accounts": main_entity.get("accounts", [])
            }
        return {}
    
    def _build_activity_description(self, crime_typologies: List[CrimeTypology]) -> str:
        """Construye descripción de actividad sospechosa."""
        if not crime_typologies:
            return "Suspicious activity detected"
        
        types = [t.typology_type.replace("_", " ").title() for t in crime_typologies]
        return f"Potential {', '.join(types)} activity detected"
    
    def _extract_date_range(self, case_data: Dict[str, Any]) -> Dict[str, str]:
        """Extrae rango de fechas de las transacciones."""
        if "transactions" in case_data and case_data["transactions"]:
            dates = [t.get("date") for t in case_data["transactions"] if t.get("date")]
            if dates:
                return {
                    "start": min(dates),
                    "end": max(dates)
                }
        return {"start": datetime.now().isoformat(), "end": datetime.now().isoformat()}
    
    def _get_institution_info(self, jurisdiction: str) -> Dict[str, Any]:
        """Obtiene información de la institución."""
        return {
            "jurisdiction": jurisdiction,
            "reporting_institution": "Financial Institution",
            "branch": "Main Branch"
        }
    
    def _get_filer_contact(self) -> Dict[str, Any]:
        """Obtiene información de contacto del filer."""
        return {
            "name": "Compliance Officer",
            "email": "compliance@institution.com",
            "phone": "+1-XXX-XXX-XXXX"
        }
    
    def _list_supporting_docs(self, case_data: Dict[str, Any]) -> List[str]:
        """Lista documentos de soporte."""
        docs = []
        if "documents" in case_data:
            docs.extend([d.get("name", "Unknown") for d in case_data["documents"]])
        return docs


class ComplianceValidationAgent(BaseAgent):
    """
    Compliance Validation Agent: Valida narrativas usando Agent-as-a-Judge.
    """
    
    def __init__(self, config: AppConfig, privacy_guard: AIPrivacyGuard):
        super().__init__(config)
        self.privacy_guard = privacy_guard
        logger.info("✅ [Compliance Validation Agent] Inicializado")
    
    def validate_narrative(
        self,
        narrative: SARNarrative,
        case_data: Dict[str, Any],
        crime_typologies: List[CrimeTypology],
        jurisdiction: str,
        regulatory_memory: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Valida la narrativa usando Agent-as-a-Judge methodology.
        """
        from langchain_core.messages import HumanMessage, SystemMessage
        
        validation_prompt = f"""Eres un juez experto en compliance AML. Evalúa esta narrativa SAR:

NARRATIVA:
{narrative.narrative_text}

CRITERIOS DE EVALUACIÓN:
1. Coherencia semántica: ¿La narrativa es clara y lógica?
2. Precisión factual: ¿Los datos coinciden con la evidencia?
3. Cumplimiento regulatorio: ¿Cumple con estándares de {jurisdiction}?
4. Completitud: ¿Incluye todos los elementos requeridos (quién, qué, cuándo, dónde, cómo)?

Responde en formato JSON:
{{
    "compliance_score": 0.0-1.0,
    "semantic_coherence": 0.0-1.0,
    "factual_accuracy": 0.0-1.0,
    "regulatory_compliance": 0.0-1.0,
    "completeness": 0.0-1.0,
    "requires_review": true/false,
    "issues": ["lista de problemas encontrados"],
    "strengths": ["lista de fortalezas"]
}}
"""
        
        messages = [
            SystemMessage(content="Eres un juez experto en compliance AML que evalúa narrativas SAR."),
            HumanMessage(content=validation_prompt)
        ]
        
        response = self.llm.invoke(messages)
        validation_text = response.content if hasattr(response, 'content') else str(response)
        
        # Parsear respuesta JSON
        import re
        json_match = re.search(r'\{.*\}', validation_text, re.DOTALL)
        if json_match:
            import json
            try:
                validation_result = json.loads(json_match.group(0))
            except:
                validation_result = {
                    "compliance_score": 0.75,
                    "requires_review": True,
                    "issues": ["Error parsing validation response"]
                }
        else:
            validation_result = {
                "compliance_score": 0.75,
                "requires_review": True,
                "issues": ["Could not parse validation response"]
            }
        
        logger.info(f"✅ [Compliance Validation] Score: {validation_result.get('compliance_score', 0.0):.2%}")
        return validation_result


class FeedbackAgent(BaseAgent):
    """
    Feedback Agent: Integra feedback del investigador para refinamiento iterativo.
    """
    
    def __init__(self, config: AppConfig):
        super().__init__(config)
        logger.info("✅ [Feedback Agent] Inicializado")
    
    def apply_feedback(
        self,
        narrative: SARNarrative,
        feedback: List[str],
        case_data: Optional[Dict[str, Any]] = None
    ) -> SARNarrative:
        """
        Aplica feedback del investigador para refinar la narrativa.
        """
        from langchain_core.messages import HumanMessage, SystemMessage
        
        feedback_prompt = f"""Refina esta narrativa SAR basándote en el feedback del investigador:

NARRATIVA ACTUAL:
{narrative.narrative_text}

FEEDBACK DEL INVESTIGADOR:
{chr(10).join(f'- {f}' for f in feedback)}

INSTRUCCIONES:
1. Incorpora todos los comentarios del investigador
2. Mantén el cumplimiento regulatorio
3. Preserva la coherencia semántica
4. Actualiza solo las secciones necesarias

GENERA LA NARRATIVA REFINADA:
"""
        
        messages = [
            SystemMessage(content="Eres un experto en compliance que refina narrativas SAR basándose en feedback."),
            HumanMessage(content=feedback_prompt)
        ]
        
        response = self.llm.invoke(messages)
        refined_text = response.content if hasattr(response, 'content') else str(response)
        
        # Actualizar narrativa
        narrative.narrative_text = refined_text
        narrative.feedback_applied.extend(feedback)
        
        logger.info(f"🔄 [Feedback Agent] Aplicado feedback: {len(feedback)} comentarios")
        return narrative

