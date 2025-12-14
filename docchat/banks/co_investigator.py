"""
Co-Investigator AI: Sistema de agentes AI para generación inteligente de SARs.
Basado en el paper "Co-Investigator AI: The Rise of Agentic AI for Smarter, Trustworthy AML Compliance Narratives"
"""

from __future__ import annotations

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
import json

from docchat.config import AppConfig
from .co_investigator_schemas import CrimeTypology, SARNarrative

logger = logging.getLogger(__name__)


class CoInvestigatorAI:
    """
    Co-Investigator AI: Sistema de agentes para generación inteligente de SARs.
    
    Arquitectura modular con agentes especializados:
    - Crime Type Detection Agent
    - Planning Agent (orquestador)
    - Typology Detection Agents (especializados)
    - External Intelligence Agent (MCP)
    - Narrative Generation Agent
    - Compliance Validation Agent (Agent-as-a-Judge)
    - Feedback Agent
    - AI-Privacy Guard Layer
    - Dynamic Memory Management
    """
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.memory_dir = Path(config.memory_dir) / "co_investigator"
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        
        # Inicializar agentes
        self._initialize_agents()
        
        # Inicializar memoria dinámica
        self._initialize_memory()
        
        logger.info("✅ [Co-Investigator AI] Sistema inicializado")
    
    def _initialize_agents(self):
        """Inicializa todos los agentes especializados."""
        from .co_investigator_agents import (
            CrimeTypeDetectionAgent,
            PlanningAgent,
            NarrativeGenerationAgent,
            ComplianceValidationAgent,
            ExternalIntelligenceAgent,
            FeedbackAgent,
            AIPrivacyGuard
        )
        
        # AI-Privacy Guard (debe inicializarse primero)
        self.privacy_guard = AIPrivacyGuard(config=self.config)
        
        # Agentes principales
        self.crime_type_detector = CrimeTypeDetectionAgent(
            config=self.config,
            privacy_guard=self.privacy_guard
        )
        
        self.planning_agent = PlanningAgent(config=self.config)
        
        self.narrative_generator = NarrativeGenerationAgent(
            config=self.config,
            privacy_guard=self.privacy_guard
        )
        
        self.compliance_validator = ComplianceValidationAgent(
            config=self.config,
            privacy_guard=self.privacy_guard
        )
        
        self.external_intelligence = ExternalIntelligenceAgent(
            config=self.config,
            privacy_guard=self.privacy_guard
        )
        
        self.feedback_agent = FeedbackAgent(config=self.config)
        
        logger.info("✅ [Co-Investigator AI] Todos los agentes inicializados")
    
    def _initialize_memory(self):
        """Inicializa el sistema de memoria dinámica."""
        from .co_investigator_memory import DynamicMemoryManager
        
        self.memory = DynamicMemoryManager(
            memory_dir=self.memory_dir,
            config=self.config
        )
        
        logger.info("✅ [Co-Investigator AI] Memoria dinámica inicializada")
    
    def generate_sar_narrative(
        self,
        case_data: Dict[str, Any],
        extracted_entities: List[Dict[str, Any]],
        sanction_hits: List[Dict[str, Any]],
        risk_scores: List[Dict[str, Any]],
        jurisdiction: str = "US",
        investigator_feedback: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Genera una narrativa SAR completa usando el sistema de agentes.
        
        Args:
            case_data: Datos del caso (transacciones, comunicaciones, etc.)
            extracted_entities: Entidades extraídas por ExtractorAgent
            sanction_hits: Resultados de screening
            risk_scores: Risk scores calculados
            jurisdiction: Jurisdicción (US, EU, etc.)
            investigator_feedback: Feedback previo del investigador (opcional)
        
        Returns:
            Dict con SAR narrative completa y metadatos
        """
        logger.info("🔍 [Co-Investigator AI] Iniciando generación de SAR narrative...")
        
        try:
            # 1. AI-Privacy Guard: Anonimizar datos sensibles
            anonymized_data = self.privacy_guard.anonymize_sensitive_data(case_data)
            
            # 2. Crime Type Detection: Detectar tipologías de crímenes
            crime_typologies = self.crime_type_detector.detect_crime_types(
                case_data=anonymized_data,
                entities=extracted_entities,
                sanction_hits=sanction_hits,
                risk_scores=risk_scores
            )
            
            logger.info(f"✅ [Co-Investigator AI] Detectadas {len(crime_typologies)} tipologías de crímenes")
            
            # 3. Planning Agent: Orquestar agentes especializados
            planning_result = self.planning_agent.plan_investigation(
                crime_typologies=crime_typologies,
                case_data=anonymized_data,
                jurisdiction=jurisdiction
            )
            
            # 4. External Intelligence: Obtener información externa
            external_intel = self.external_intelligence.gather_intelligence(
                entities=extracted_entities,
                crime_typologies=crime_typologies,
                jurisdiction=jurisdiction
            )
            
            # 5. Narrative Generation: Generar narrativa con Chain-of-Thought
            narrative_draft = self.narrative_generator.generate_narrative(
                case_data=anonymized_data,
                entities=extracted_entities,
                crime_typologies=crime_typologies,
                sanction_hits=sanction_hits,
                risk_scores=risk_scores,
                external_intelligence=external_intel,
                jurisdiction=jurisdiction,
                historical_narratives=self.memory.get_historical_narratives(),
                regulatory_guidelines=self.memory.get_regulatory_guidelines(jurisdiction)
            )
            
            # 6. Compliance Validation: Validar con Agent-as-a-Judge
            validation_result = self.compliance_validator.validate_narrative(
                narrative=narrative_draft,
                case_data=anonymized_data,
                crime_typologies=crime_typologies,
                jurisdiction=jurisdiction,
                regulatory_memory=self.memory.get_regulatory_memory()
            )
            
            # 7. Aplicar feedback del investigador si existe
            if investigator_feedback:
                narrative_draft = self.feedback_agent.apply_feedback(
                    narrative=narrative_draft,
                    feedback=investigator_feedback
                )
            
            # 8. Des-anonimizar para el investigador (solo datos necesarios)
            final_narrative = self.privacy_guard.deanonymize_for_investigator(
                narrative=narrative_draft,
                original_data=case_data
            )
            
            # 9. Guardar en memoria dinámica
            self.memory.store_narrative(
                narrative=final_narrative,
                crime_typologies=crime_typologies,
                jurisdiction=jurisdiction
            )
            
            # 10. Preparar resultado final
            result = {
                "success": True,
                "narrative": final_narrative,
                "crime_typologies": [asdict(ct) for ct in crime_typologies],
                "compliance_validation": validation_result,
                "external_intelligence": external_intel,
                "confidence_scores": narrative_draft.confidence_scores,
                "compliance_score": validation_result.get("compliance_score", 0.0),
                "requires_review": validation_result.get("requires_review", True),
                "validation_issues": validation_result.get("issues", []),
                "generated_at": datetime.now().isoformat()
            }
            
            logger.info(f"✅ [Co-Investigator AI] SAR narrative generada exitosamente (compliance: {result['compliance_score']:.2%})")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ [Co-Investigator AI] Error generando SAR narrative: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "narrative": None
            }
    
    def refine_narrative_with_feedback(
        self,
        narrative_id: str,
        feedback: List[str],
        case_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Refina una narrativa existente con feedback del investigador.
        
        Args:
            narrative_id: ID de la narrativa a refinar
            feedback: Lista de comentarios/instrucciones del investigador
            case_data: Datos del caso actualizados
        
        Returns:
            Narrativa refinada
        """
        logger.info(f"🔄 [Co-Investigator AI] Refinando narrativa {narrative_id} con feedback...")
        
        # Obtener narrativa original de memoria
        original_narrative = self.memory.get_narrative(narrative_id)
        if not original_narrative:
            return {
                "success": False,
                "error": f"Narrativa {narrative_id} no encontrada"
            }
        
        # Aplicar feedback
        refined_narrative = self.feedback_agent.apply_feedback(
            narrative=original_narrative,
            feedback=feedback,
            case_data=case_data
        )
        
        # Re-validar
        validation_result = self.compliance_validator.validate_narrative(
            narrative=refined_narrative,
            case_data=case_data,
            crime_typologies=original_narrative.get("crime_typologies", []),
            jurisdiction=original_narrative.get("jurisdiction", "US")
        )
        
        # Actualizar en memoria
        self.memory.update_narrative(narrative_id, refined_narrative)
        
        return {
            "success": True,
            "narrative": refined_narrative,
            "compliance_validation": validation_result,
            "refined_at": datetime.now().isoformat()
        }

