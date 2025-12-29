"""
Calificación de Lead BANT (Budget, Authority, Need, Timeline) para STAR AGENT.

Implementa calificación inteligente de leads según etapa de venta.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from enum import Enum

from ..state.customer_session import CustomerSessionState


class BANTScore(str, Enum):
    """Niveles de calificación BANT"""
    QUALIFIED = "qualified"  # Calificado - listo para comprar
    PARTIAL = "partial"  # Parcialmente calificado
    UNQUALIFIED = "unqualified"  # No calificado


@dataclass
class BANTQualification:
    """Resultado de calificación BANT"""
    budget: Optional[bool] = None  # Tiene presupuesto
    authority: Optional[bool] = None  # Tiene autoridad para decidir
    need: Optional[bool] = None  # Tiene necesidad
    timeline: Optional[bool] = None  # Tiene timeline definido
    score: BANTScore = BANTScore.UNQUALIFIED
    confidence: float = 0.0  # 0.0 a 1.0
    questions_to_ask: List[str] = None


class LeadQualifier:
    """
    Calificador de Leads BANT simplificado.
    
    Pregunta inteligente según etapa:
    - INTEREST: Preguntas sobre necesidad
    - CONSIDERATION: Preguntas sobre presupuesto y autoridad
    - READY: Confirmar timeline y cerrar
    """
    
    def __init__(self):
        self.qualification_history: Dict[str, BANTQualification] = {}
    
    def qualify_lead(
        self,
        session: CustomerSessionState,
        conversation_history: List[str],
    ) -> BANTQualification:
        """
        Califica lead basado en sesión e historial de conversación.
        
        Args:
            session: Estado de sesión del cliente
            conversation_history: Historial de mensajes
            
        Returns:
            BANTQualification con resultados
        """
        session_id = session.profile.user_id if session.profile else "unknown"
        
        # Analizar conversación para extraer señales BANT
        conversation_text = " ".join(conversation_history).lower()
        
        # Budget (Presupuesto)
        budget_signals = [
            "presupuesto", "budget", "cuánto", "precio", "cuesta",
            "puedo pagar", "tengo dinero", "disponible para"
        ]
        budget = any(signal in conversation_text for signal in budget_signals)
        
        # Authority (Autoridad)
        authority_signals = [
            "decido yo", "soy el dueño", "tengo autoridad", "puedo decidir",
            "necesito consultar", "hablar con mi jefe", "mi empresa"
        ]
        authority = any(signal in conversation_text for signal in authority_signals)
        if "necesito consultar" in conversation_text or "hablar con" in conversation_text:
            authority = False
        
        # Need (Necesidad)
        need_signals = [
            "necesito", "requiero", "busco", "quiero", "me interesa",
            "problema", "solución", "me ayudaría"
        ]
        need = any(signal in conversation_text for signal in need_signals)
        
        # Timeline (Tiempo)
        timeline_signals = [
            "urgente", "pronto", "esta semana", "este mes", "inmediato",
            "ahora", "ya", "cuando", "fecha límite"
        ]
        timeline = any(signal in conversation_text for signal in timeline_signals)
        
        # Calcular score
        scores = [budget, authority, need, timeline]
        positive_count = sum(1 for s in scores if s)
        confidence = positive_count / 4.0
        
        if positive_count >= 3:
            score = BANTScore.QUALIFIED
        elif positive_count >= 2:
            score = BANTScore.PARTIAL
        else:
            score = BANTScore.UNQUALIFIED
        
        qualification = BANTQualification(
            budget=budget,
            authority=authority,
            need=need,
            timeline=timeline,
            score=score,
            confidence=confidence,
            questions_to_ask=self._generate_questions(budget, authority, need, timeline),
        )
        
        # Guardar en historial
        self.qualification_history[session_id] = qualification
        
        return qualification
    
    def _generate_questions(
        self,
        budget: bool,
        authority: bool,
        need: bool,
        timeline: bool,
    ) -> List[str]:
        """Genera preguntas inteligentes según lo que falta"""
        questions = []
        
        if not need:
            questions.append("¿Qué problema específico estás tratando de resolver?")
        
        if not budget:
            questions.append("¿Tienes un presupuesto aproximado para esta solución?")
        
        if not authority:
            questions.append("¿Eres quien toma la decisión final o necesitas consultar con alguien?")
        
        if not timeline:
            questions.append("¿Cuándo necesitarías tener esto implementado?")
        
        return questions
    
    def get_next_question(
        self,
        qualification: BANTQualification,
        sales_stage: str,
    ) -> Optional[str]:
        """
        Obtiene la siguiente pregunta según etapa de venta y calificación.
        
        Args:
            qualification: Calificación BANT actual
            sales_stage: Etapa de venta (interest, consideration, ready)
            
        Returns:
            Pregunta a hacer o None si está completo
        """
        if qualification.score == BANTScore.QUALIFIED:
            return None  # Ya está calificado
        
        # Según etapa, priorizar diferentes aspectos
        if sales_stage == "interest":
            # En interés, priorizar necesidad
            if not qualification.need and qualification.questions_to_ask:
                return qualification.questions_to_ask[0]
        
        elif sales_stage == "consideration":
            # En consideración, priorizar presupuesto y autoridad
            if not qualification.budget:
                return "¿Tienes un presupuesto aproximado para esta solución?"
            if not qualification.authority:
                return "¿Eres quien toma la decisión final o necesitas consultar con alguien?"
        
        elif sales_stage == "ready":
            # Listo, confirmar timeline
            if not qualification.timeline:
                return "¿Cuándo te gustaría comenzar?"
        
        # Por defecto, primera pregunta pendiente
        if qualification.questions_to_ask:
            return qualification.questions_to_ask[0]
        
        return None

