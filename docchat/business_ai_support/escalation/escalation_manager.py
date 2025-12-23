"""Sistema de Escalación Automática para Business AI Support.

Reglas automáticas de escalación basadas en:
- Frustration score
- Palabras clave de escalación
- Confianza baja en respuesta
"""

from __future__ import annotations

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime


@dataclass
class EscalationRule:
    """Regla de escalación."""
    name: str
    condition: str  # "frustration", "keyword", "confidence", "custom"
    threshold: float
    keywords: List[str] = None
    reason: str = ""


class EscalationManager:
    """Gestor de escalación automática."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Inicializa el gestor de escalación.
        
        Args:
            config: Configuración con thresholds personalizados
        """
        self.config = config or {}
        
        # Thresholds por defecto
        self.frustration_threshold = self.config.get("frustration_threshold", 7.0)
        self.confidence_threshold = self.config.get("confidence_threshold", 0.5)
        
        # Palabras clave que indican necesidad de humano
        self.escalation_keywords = self.config.get("escalation_keywords", [
            "quiero hablar con humano",
            "quiero hablar con una persona",
            "hablar con alguien",
            "hablar con agente",
            "hablar con representante",
            "escalar",
            "supervisor",
            "manager",
            "gerente",
            "no me ayudas",
            "no entiendo",
            "no funciona",
            "estoy enojado",
            "estoy molesto",
            "reclamo",
            "queja formal"
        ])
        
        # Reglas de escalación
        self.rules = [
            EscalationRule(
                name="Frustración Alta",
                condition="frustration",
                threshold=self.frustration_threshold,
                reason="Frustración del cliente por encima del umbral"
            ),
            EscalationRule(
                name="Palabras Clave de Escalación",
                condition="keyword",
                threshold=0.0,
                keywords=self.escalation_keywords,
                reason="Cliente solicitó hablar con humano"
            ),
            EscalationRule(
                name="Confianza Baja",
                condition="confidence",
                threshold=self.confidence_threshold,
                reason="Confianza en respuesta por debajo del umbral"
            ),
        ]
    
    def should_escalate(
        self,
        message: str,
        frustration_score: float,
        confidence: float,
        session_data: Optional[Dict[str, Any]] = None
    ) -> tuple[bool, str]:
        """
        Determina si se debe escalar a humano.
        
        Returns:
            (should_escalate: bool, reason: str)
        """
        message_lower = message.lower()
        
        # Regla 1: Frustración alta
        if frustration_score >= self.frustration_threshold:
            return True, f"Frustración alta ({frustration_score:.1f}/10) - Escalación automática"
        
        # Regla 2: Palabras clave
        for keyword in self.escalation_keywords:
            if keyword in message_lower:
                return True, f"Cliente solicitó hablar con humano (detectado: '{keyword}')"
        
        # Regla 3: Confianza baja
        if confidence < self.confidence_threshold:
            return True, f"Confianza baja ({confidence:.1%}) - Escalación para mejor atención"
        
        # Regla 4: Múltiples intentos fallidos (si hay session_data)
        if session_data:
            failed_attempts = session_data.get("failed_resolution_attempts", 0)
            if failed_attempts >= 3:
                return True, f"Múltiples intentos fallidos ({failed_attempts}) - Escalación necesaria"
        
        return False, ""
    
    def get_escalation_priority(
        self,
        frustration_score: float,
        has_keyword: bool = False
    ) -> str:
        """Determina la prioridad del ticket escalado."""
        if has_keyword or frustration_score >= 9.0:
            return "high"
        elif frustration_score >= 7.0:
            return "medium"
        else:
            return "normal"




