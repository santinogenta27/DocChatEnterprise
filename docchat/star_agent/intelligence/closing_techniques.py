"""
Closing Techniques - TÃ©cnicas de Cierre Avanzadas
Sistema de mÃºltiples estrategias de cierre con selecciÃ³n automÃ¡tica
"""

from __future__ import annotations

from typing import Dict, Optional, List
from dataclasses import dataclass
from enum import Enum

from .behavior_analyzer import BehaviorAnalysis, CustomerSegment, PurchaseSignal, UrgencyLevel


class ClosingTechnique(Enum):
    """TÃ©cnicas de cierre disponibles."""
    ASSUMPTIVE_CLOSE = "assumptive_close"  # Asumir la venta
    ALTERNATIVE_CLOSE = "alternative_close"  # Cerrar con alternativa
    URGENCY_CLOSE = "urgency_close"  # Cerrar con urgencia
    SCARCITY_CLOSE = "scarcity_close"  # Cerrar con escasez
    QUESTION_CLOSE = "question_close"  # Cerrar con pregunta
    BENEFIT_CLOSE = "benefit_close"  # Cerrar destacando beneficios
    SOCIAL_PROOF_CLOSE = "social_proof_close"  # Cerrar con prueba social
    OBJECTION_CLOSE = "objection_close"  # Cerrar resolviendo objeciÃ³n
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
    Gestor de tÃ©cnicas de cierre avanzadas.
    
    CaracterÃ­sticas:
    - MÃºltiples estrategias de cierre
    - SelecciÃ³n automÃ¡tica segÃºn perfil
    - Templates personalizables
    - MÃ©tricas de efectividad (futuro: A/B testing)
    """
    
    def __init__(self):
        """Inicializa el gestor de tÃ©cnicas de cierre."""
        # Templates de mensajes por tÃ©cnica
        self.templates = {
            ClosingTechnique.ASSUMPTIVE_CLOSE: [
                "Perfecto, Â¿quÃ© talla necesitas?",
                "Excelente elecciÃ³n. Â¿Prefieres envÃ­o estÃ¡ndar o express?",
                "Genial, Â¿tienes alguna pregunta antes de proceder con la compra?",
            ],
            ClosingTechnique.ALTERNATIVE_CLOSE: [
                "Â¿Prefieres la versiÃ³n estÃ¡ndar o la Pro? Ambas son excelentes opciones.",
                "Â¿Te gustarÃ­a pagar ahora o prefieres ver mÃ¡s opciones primero?",
                "Â¿Quieres empezar con este producto o prefieres ver el paquete completo?",
            ],
            ClosingTechnique.URGENCY_CLOSE: [
                "Esta oferta termina maÃ±ana. Â¿Te gustarÃ­a asegurarla ahora?",
                "Solo quedan {stock} unidades disponibles. Â¿Quieres que reserve una para ti?",
                "Esta promociÃ³n es por tiempo limitado. Â¿Te parece bien si procedemos?",
            ],
            ClosingTechnique.SCARCITY_CLOSE: [
                "Solo quedan {stock} unidades en stock. Es un producto muy popular.",
                "Este producto estÃ¡ casi agotado. Â¿Te gustarÃ­a que lo agreguemos a tu carrito?",
                "Ãšltimas unidades disponibles. Â¿Te interesa?",
            ],
            ClosingTechnique.QUESTION_CLOSE: [
                "Â¿QuÃ© te parece si te muestro el resumen de tu pedido?",
                "Â¿Hay algo mÃ¡s que necesites saber antes de decidir?",
                "Â¿Te gustarÃ­a que te guÃ­e a travÃ©s del proceso de compra?",
            ],
            ClosingTechnique.BENEFIT_CLOSE: [
                "Este producto te ahorrarÃ¡ tiempo y dinero a largo plazo. Â¿Te parece bien si procedemos?",
                "Con esta compra, obtendrÃ¡s {benefits}. Â¿Te interesa?",
                "El valor que obtendrÃ¡s es excelente. Â¿Quieres continuar?",
            ],
            ClosingTechnique.SOCIAL_PROOF_CLOSE: [
                "Este producto es muy popular entre clientes como tÃº. Â¿Te gustarÃ­a probarlo?",
                "Muchos clientes quedan satisfechos con esta opciÃ³n. Â¿Te parece bien?",
                "Este es uno de nuestros productos mejor valorados. Â¿Te interesa?",
            ],
            ClosingTechnique.OBJECTION_CLOSE: [
                "Entiendo tu preocupaciÃ³n sobre {objection}. Sin embargo, {response}. Â¿Esto resuelve tu duda?",
                "Comprendo que {objection}. Â¿QuÃ© te parece si {solution}?",
            ],
            ClosingTechnique.SOFT_CLOSE: [
                "Veo que estÃ¡s interesado. Â¿Te gustarÃ­a que te envÃ­e mÃ¡s informaciÃ³n?",
                "Â¿Hay algo especÃ­fico en lo que pueda ayudarte a decidir?",
                "Â¿Te parece bien si te muestro las opciones que mejor encajan con lo que buscas?",
            ],
        }
        
        # MÃ©tricas de efectividad (para futuro A/B testing)
        self.effectiveness_metrics: Dict[ClosingTechnique, Dict[str, float]] = {}
    
    def select_technique(self,
                        behavior_analysis: BehaviorAnalysis,
                        conversation_context: Optional[Dict],
                        stock_available: Optional[int] = None) -> ClosingStrategy:
        """
        Selecciona la tÃ©cnica de cierre mÃ¡s apropiada.
        
        Args:
            behavior_analysis: AnÃ¡lisis de comportamiento
            conversation_context: Contexto de conversaciÃ³n
            stock_available: Stock disponible (para escasez)
            
        Returns:
            ClosingStrategy seleccionada
        """
        # Determinar tÃ©cnica segÃºn perfil y contexto
        technique = self._choose_technique(
            behavior_analysis, conversation_context, stock_available
        )
        
        # Seleccionar template
        templates = self.templates.get(technique, [])
        if not templates:
            # Fallback
            template = "Â¿Te gustarÃ­a continuar con tu compra?"
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
        """Elige la tÃ©cnica de cierre mÃ¡s apropiada."""
        # Si hay urgencia crÃ­tica, usar urgency close
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
        """Personaliza el template con informaciÃ³n contextual."""
        # Reemplazar placeholders
        if "{stock}" in template and stock_available:
            template = template.replace("{stock}", str(stock_available))
        
        if "{benefits}" in template:
            template = template.replace("{benefits}", "calidad superior y garantÃ­a extendida")
        
        return template
    
    def _calculate_confidence(self,
                             technique: ClosingTechnique,
                             behavior_analysis: BehaviorAnalysis) -> float:
        """Calcula la confianza en la tÃ©cnica seleccionada."""
        base_confidence = 0.5
        
        # Aumentar confianza segÃºn seÃ±al de compra
        if behavior_analysis.purchase_signal == PurchaseSignal.HIGH:
            base_confidence += 0.3
        elif behavior_analysis.purchase_signal == PurchaseSignal.MEDIUM:
            base_confidence += 0.15
        
        # Aumentar confianza segÃºn urgencia
        if behavior_analysis.urgency_level == UrgencyLevel.CRITICAL:
            base_confidence += 0.2
        
        # Aumentar confianza si es hot lead
        if behavior_analysis.segment == CustomerSegment.HOT_LEAD:
            base_confidence += 0.1
        
        return min(1.0, base_confidence)
    
    def _generate_rationale(self,
                           technique: ClosingTechnique,
                           behavior_analysis: BehaviorAnalysis) -> str:
        """Genera la justificaciÃ³n de la tÃ©cnica seleccionada."""
        rationale_parts = []
        
        rationale_parts.append(f"TÃ©cnica: {technique.value}")
        rationale_parts.append(f"SeÃ±al de compra: {behavior_analysis.purchase_signal.value}")
        rationale_parts.append(f"Segmento: {behavior_analysis.segment.value}")
        
        if behavior_analysis.urgency_level != UrgencyLevel.NONE:
            rationale_parts.append(f"Urgencia: {behavior_analysis.urgency_level.value}")
        
        return " | ".join(rationale_parts)
    
    def _get_context_description(self, behavior_analysis: BehaviorAnalysis) -> str:
        """Obtiene descripciÃ³n del contexto para logging."""
        return f"{behavior_analysis.segment.value}_{behavior_analysis.purchase_signal.value}"


