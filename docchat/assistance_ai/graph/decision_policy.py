"""Decision Policy - Decide qué acción tomar basado en el estado."""

from typing import Dict, Any, Literal
from .state import CustomerServiceState


class DecisionPolicy:
    """Policy de decisión para el agente.
    
    Decide entre:
    - responder: El agente puede responder con confianza
    - ask_clarification: Necesita más información
    - escalate: Debe escalar a humano
    - reject: Rechazar por baja confianza
    """
    
    # Thresholds configurables
    MIN_CONFIDENCE_TO_RESPOND = 0.75
    MIN_CONFIDENCE_TO_CLARIFY = 0.50
    ESCALATION_CONFIDENCE_THRESHOLD = 0.30
    ESCALATION_SENTIMENT_THRESHOLD = 0.8  # Sentimiento negativo alto
    
    def decide(self, state: CustomerServiceState) -> Literal["respond", "ask_clarification", "escalate", "reject"]:
        """Decide la acción basada en el estado actual.
        
        Returns:
            Una de las acciones posibles: "respond", "ask_clarification", "escalate", "reject"
        """
        confidence = state.get("confidence", 0.0)
        intent = state.get("intent")
        escalation_flag = state.get("escalation_flag", False)
        
        # Si ya hay flag de escalamiento, escalar
        if escalation_flag:
            return "escalate"
        
        # Intención de escalamiento explícita
        if intent == "escalamiento_humano":
            return "escalate"
        
        # Sentimiento negativo extremo
        metadata = state.get("metadata", {})
        sentiment_score = metadata.get("sentiment_score", 0.5)
        if sentiment_score > self.ESCALATION_SENTIMENT_THRESHOLD and intent == "conversacion_sentimiento_negativo":
            return "escalate"
        
        # Confianza demasiado baja -> rechazar o escalar
        if confidence < self.ESCALATION_CONFIDENCE_THRESHOLD:
            # Si la confianza es extremadamente baja, rechazar
            if confidence < 0.2:
                return "reject"
            # Si es baja pero no extremadamente, escalar
            return "escalate"
        
        # Confianza baja pero recuperable -> pedir aclaración
        if confidence < self.MIN_CONFIDENCE_TO_RESPOND:
            if confidence >= self.MIN_CONFIDENCE_TO_CLARIFY:
                return "ask_clarification"
            else:
                # Entre 0.3 y 0.5: intentar clarificar una vez, si no funciona escalar
                clarification_count = state.get("metadata", {}).get("clarification_count", 0)
                if clarification_count < 1:
                    return "ask_clarification"
                else:
                    return "escalate"
        
        # Confianza suficiente -> responder
        return "respond"

