"""
Closing Techniques - Técnicas de Cierre Avanzadas
Sistema de múltiples estrategias de cierre con selección automática
"""

from __future__ import annotations

from typing import Dict, Optional, List
from dataclasses import dataclass
from enum import Enum

from .behavior_analyzer import BehaviorAnalysis, CustomerSegment, PurchaseSignal, UrgencyLevel


class ClosingTechnique(Enum):
    """Técnicas de cierre disponibles."""
    ASSUMPTIVE_CLOSE = "assumptive_close"  # Asumir la venta
    ALTERNATIVE_CLOSE = "alternative_close"  # Cerrar con alternativa
    URGENCY_CLOSE = "urgency_close"  # Cerrar con urgencia
    SCARCITY_CLOSE = "scarcity_close"  # Cerrar con escasez
    QUESTION_CLOSE = "question_close"  # Cerrar con pregunta
    BENEFIT_CLOSE = "benefit_close"  # Cerrar destacando beneficios
    SOCIAL_PROOF_CLOSE = "social_proof_close"  # Cerrar con prueba social
    OBJECTION_CLOSE = "objection_close"  # Cerrar resolviendo objeción
    SOFT_CLOSE = "soft_close"  # Cierre suave


@dataclass
class ClosingStrategy:
    """Estrategia de cierre seleccionada."""
    technique: ClosingTechnique
    message_template: str
    context: str
    confidence: float  # 0.0 - 1.0
    rationale: str


class ClosingTechniquesManager:
    """
    Gestor de técnicas de cierre avanzadas.
    
    Características:
    - Múltiples estrategias de cierre
    - Selección automática según perfil
    - Templates personalizables
    - Métricas de efectividad (futuro: A/B testing)
    """
    
    def __init__(self):
        """Inicializa el gestor de técnicas de cierre."""
        # Templates de mensajes por técnica
        self.templates = {
            ClosingTechnique.ASSUMPTIVE_CLOSE: [
                "Perfecto, ¿qué talla necesitas?",
                "Excelente elección. ¿Prefieres envío estándar o express?",
                "Genial, ¿tienes alguna pregunta antes de proceder con la compra?",
            ],
            ClosingTechnique.ALTERNATIVE_CLOSE: [
                "¿Prefieres la versión estándar o la Pro? Ambas son excelentes opciones.",
                "¿Te gustaría pagar ahora o prefieres ver más opciones primero?",
                "¿Quieres empezar con este producto o prefieres ver el paquete completo?",
            ],
            ClosingTechnique.URGENCY_CLOSE: [
                "Esta oferta termina mañana. ¿Te gustaría asegurarla ahora?",
                "Solo quedan {stock} unidades disponibles. ¿Quieres que reserve una para ti?",
                "Esta promoción es por tiempo limitado. ¿Te parece bien si procedemos?",
            ],
            ClosingTechnique.SCARCITY_CLOSE: [
                "Solo quedan {stock} unidades en stock. Es un producto muy popular.",
                "Este producto está casi agotado. ¿Te gustaría que lo agreguemos a tu carrito?",
                "Últimas unidades disponibles. ¿Te interesa?",
            ],
            ClosingTechnique.QUESTION_CLOSE: [
                "¿Qué te parece si te muestro el resumen de tu pedido?",
                "¿Hay algo más que necesites saber antes de decidir?",
                "¿Te gustaría que te guíe a través del proceso de compra?",
            ],
            ClosingTechnique.BENEFIT_CLOSE: [
                "Este producto te ahorrará tiempo y dinero a largo plazo. ¿Te parece bien si procedemos?",
                "Con esta compra, obtendrás {benefits}. ¿Te interesa?",
                "El valor que obtendrás es excelente. ¿Quieres continuar?",
            ],
            ClosingTechnique.SOCIAL_PROOF_CLOSE: [
                "Este producto es muy popular entre clientes como tú. ¿Te gustaría probarlo?",
                "Muchos clientes quedan satisfechos con esta opción. ¿Te parece bien?",
                "Este es uno de nuestros productos mejor valorados. ¿Te interesa?",
            ],
            ClosingTechnique.OBJECTION_CLOSE: [
                "Entiendo tu preocupación sobre {objection}. Sin embargo, {response}. ¿Esto resuelve tu duda?",
                "Comprendo que {objection}. ¿Qué te parece si {solution}?",
            ],
            ClosingTechnique.SOFT_CLOSE: [
                "Veo que estás interesado. ¿Te gustaría que te envíe más información?",
                "¿Hay algo específico en lo que pueda ayudarte a decidir?",
                "¿Te parece bien si te muestro las opciones que mejor encajan con lo que buscas?",
            ],
        }
        
        # Métricas de efectividad (para futuro A/B testing)
        self.effectiveness_metrics: Dict[ClosingTechnique, Dict[str, float]] = {}
    
    def select_technique(self,
                        behavior_analysis: BehaviorAnalysis,
                        conversation_context: Optional[Dict],
                        stock_available: Optional[int] = None) -> ClosingStrategy:
        """
        Selecciona la técnica de cierre más apropiada.
        
        Args:
            behavior_analysis: Análisis de comportamiento
            conversation_context: Contexto de conversación
            stock_available: Stock disponible (para escasez)
            
        Returns:
            ClosingStrategy seleccionada
        """
        # Determinar técnica según perfil y contexto
        technique = self._choose_technique(
            behavior_analysis, conversation_context, stock_available
        )
        
        # Seleccionar template
        templates = self.templates.get(technique, [])
        if not templates:
            # Fallback
            template = "¿Te gustaría continuar con tu compra?"
        else:
            template = templates[0]  # Por ahora usar el primero, luego A/B testing
        
        # Personalizar template
        personalized_template = self._personalize_template(
            template, behavior_analysis, stock_available
        )
        
        # Calcular confidence
        confidence = self._calculate_confidence(technique, behavior_analysis)
        
        # Rationale
        rationale = self._generate_rationale(technique, behavior_analysis)
        
        return ClosingStrategy(
            technique=technique,
            message_template=personalized_template,
            context=self._get_context_description(behavior_analysis),
            confidence=confidence,
            rationale=rationale
        )
    
    def _choose_technique(self,
                         behavior_analysis: BehaviorAnalysis,
                         conversation_context: Optional[Dict],
                         stock_available: Optional[int]) -> ClosingTechnique:
        """Elige la técnica de cierre más apropiada."""
        # Si hay urgencia crítica, usar urgency close
        if behavior_analysis.urgency_level == UrgencyLevel.CRITICAL:
            return ClosingTechnique.URGENCY_CLOSE
        
        # Si hay escasez de stock, usar scarcity close
        if stock_available and stock_available <= 5:
            return ClosingTechnique.SCARCITY_CLOSE
        
        # Si es hot lead, usar assumptive close
        if behavior_analysis.purchase_signal == PurchaseSignal.HIGH:
            if behavior_analysis.segment == CustomerSegment.HOT_LEAD:
                return ClosingTechnique.ASSUMPTIVE_CLOSE
        
        # Si hay objeciones previas, usar objection close
        if conversation_context and conversation_context.get("objections_raised"):
            return ClosingTechnique.OBJECTION_CLOSE
        
        # Si es price shopper, usar benefit close
        if behavior_analysis.segment == CustomerSegment.PRICE_SHOPPER:
            return ClosingTechnique.BENEFIT_CLOSE
        
        # Si es researcher, usar social proof close
        if behavior_analysis.segment == CustomerSegment.RESEARCHER:
            return ClosingTechnique.SOCIAL_PROOF_CLOSE
        
        # Si es warm lead, usar alternative close
        if behavior_analysis.purchase_signal == PurchaseSignal.MEDIUM:
            return ClosingTechnique.ALTERNATIVE_CLOSE
        
        # Default: soft close
        return ClosingTechnique.SOFT_CLOSE
    
    def _personalize_template(self,
                             template: str,
                             behavior_analysis: BehaviorAnalysis,
                             stock_available: Optional[int]) -> str:
        """Personaliza el template con información contextual."""
        # Reemplazar placeholders
        if "{stock}" in template and stock_available:
            template = template.replace("{stock}", str(stock_available))
        
        if "{benefits}" in template:
            template = template.replace("{benefits}", "calidad superior y garantía extendida")
        
        return template
    
    def _calculate_confidence(self,
                             technique: ClosingTechnique,
                             behavior_analysis: BehaviorAnalysis) -> float:
        """Calcula la confianza en la técnica seleccionada."""
        base_confidence = 0.5
        
        # Aumentar confianza según señal de compra
        if behavior_analysis.purchase_signal == PurchaseSignal.HIGH:
            base_confidence += 0.3
        elif behavior_analysis.purchase_signal == PurchaseSignal.MEDIUM:
            base_confidence += 0.15
        
        # Aumentar confianza según urgencia
        if behavior_analysis.urgency_level == UrgencyLevel.CRITICAL:
            base_confidence += 0.2
        
        # Aumentar confianza si es hot lead
        if behavior_analysis.segment == CustomerSegment.HOT_LEAD:
            base_confidence += 0.1
        
        return min(1.0, base_confidence)
    
    def _generate_rationale(self,
                           technique: ClosingTechnique,
                           behavior_analysis: BehaviorAnalysis) -> str:
        """Genera la justificación de la técnica seleccionada."""
        rationale_parts = []
        
        rationale_parts.append(f"Técnica: {technique.value}")
        rationale_parts.append(f"Señal de compra: {behavior_analysis.purchase_signal.value}")
        rationale_parts.append(f"Segmento: {behavior_analysis.segment.value}")
        
        if behavior_analysis.urgency_level != UrgencyLevel.NONE:
            rationale_parts.append(f"Urgencia: {behavior_analysis.urgency_level.value}")
        
        return " | ".join(rationale_parts)
    
    def _get_context_description(self, behavior_analysis: BehaviorAnalysis) -> str:
        """Obtiene descripción del contexto para logging."""
        return f"{behavior_analysis.segment.value}_{behavior_analysis.purchase_signal.value}"

