"""
Proactive Suggestions - Proactividad Inteligente
Sistema que anticipa necesidades y sugiere acciones proactivas
"""

from __future__ import annotations

from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

from .behavior_analyzer import BehaviorAnalysis, PurchaseSignal, UrgencyLevel, CustomerSegment


class ProactiveActionType(Enum):
    """Tipos de acciones proactivas."""
    SUGGEST_PRODUCT = "suggest_product"
    ADDRESS_ABANDONMENT = "address_abandonment"
    FOLLOW_UP = "follow_up"
    OFFER_HELP = "offer_help"
    REMIND_ABANDONED_CART = "remind_abandoned_cart"
    CROSS_SELL = "cross_sell"
    UPSELL = "upsell"
    CREATE_URGENCY = "create_urgency"
    PROVIDE_INFO = "provide_info"


@dataclass
class ProactiveSuggestion:
    """Sugerencia proactiva."""
    action_type: ProactiveActionType
    message: str
    priority: int  # 1-10, 10 = mÃ¡xima prioridad
    context: str
    trigger_reason: str


class ProactiveSuggestionsEngine:
    """
    Motor de sugerencias proactivas.
    
    Detecta oportunidades para:
    - Sugerir productos
    - Abordar abandono
    - Follow-ups
    - Recordatorios de carritos
    """
    
    def __init__(self):
        """Inicializa el motor de sugerencias proactivas."""
        pass
    
    def generate_suggestions(self,
                           behavior_analysis: BehaviorAnalysis,
                           conversation_context: Optional[Dict],
                           products_viewed: List[str],
                           time_since_last_message: Optional[float] = None,
                           cart_items: Optional[List[Dict]] = None) -> List[ProactiveSuggestion]:
        """
        Genera sugerencias proactivas basÃ¡ndose en el anÃ¡lisis de comportamiento.
        
        Args:
            behavior_analysis: AnÃ¡lisis de comportamiento del usuario
            conversation_context: Contexto de la conversaciÃ³n
            products_viewed: Productos que ha visto
            time_since_last_message: Tiempo desde Ãºltimo mensaje (segundos)
            cart_items: Items en el carrito (si hay)
            
        Returns:
            Lista de sugerencias proactivas ordenadas por prioridad
        """
        suggestions = []
        
        # 1. Detectar riesgo de abandono y abordar
        if behavior_analysis.risk_of_abandonment > 0.6:
            suggestion = ProactiveSuggestion(
                action_type=ProactiveActionType.ADDRESS_ABANDONMENT,
                message="Veo que estÃ¡s indeciso. Â¿Hay algo especÃ­fico en lo que pueda ayudarte a decidir?",
                priority=9,
                context="high_abandonment_risk",
                trigger_reason=f"Riesgo de abandono: {behavior_analysis.risk_of_abandonment:.2f}"
            )
            suggestions.append(suggestion)
        
        # 2. Recordatorio de carrito abandonado
        if cart_items and len(cart_items) > 0:
            if time_since_last_message and time_since_last_message > 300:  # 5 minutos
                suggestion = ProactiveSuggestion(
                    action_type=ProactiveActionType.REMIND_ABANDONED_CART,
                    message=f"Veo que tienes {len(cart_items)} producto(s) en tu carrito. Â¿Te gustarÃ­a continuar con tu compra? Puedo ayudarte con cualquier duda.",
                    priority=8,
                    context="abandoned_cart",
                    trigger_reason=f"Carrito con {len(cart_items)} items, {time_since_last_message/60:.1f} minutos sin actividad"
                )
                suggestions.append(suggestion)
        
        # 3. Si es hot lead, sugerir cerrar venta
        if behavior_analysis.purchase_signal == PurchaseSignal.HIGH:
            if behavior_analysis.urgency_level == UrgencyLevel.CRITICAL:
                suggestion = ProactiveSuggestion(
                    action_type=ProactiveActionType.CREATE_URGENCY,
                    message="Perfecto, veo que estÃ¡s listo. Â¿Te gustarÃ­a proceder con la compra ahora? Puedo ayudarte con el proceso.",
                    priority=10,
                    context="hot_lead_urgent",
                    trigger_reason="Hot lead con urgencia crÃ­tica"
                )
                suggestions.append(suggestion)
        
        # 4. Cross-sell si hay productos de interÃ©s
        if products_viewed and len(products_viewed) >= 1:
            if behavior_analysis.purchase_signal in [PurchaseSignal.HIGH, PurchaseSignal.MEDIUM]:
                suggestion = ProactiveSuggestion(
                    action_type=ProactiveActionType.CROSS_SELL,
                    message="Veo que te interesan estos productos. TambiÃ©n tengo algunos complementos que podrÃ­an ser Ãºtiles. Â¿Te gustarÃ­a que te los muestre?",
                    priority=6,
                    context="cross_sell_opportunity",
                    trigger_reason=f"Productos de interÃ©s: {len(products_viewed)}"
                )
                suggestions.append(suggestion)
        
        # 5. Ofrecer ayuda si estÃ¡ explorando
        if behavior_analysis.segment == CustomerSegment.RESEARCHER:
            suggestion = ProactiveSuggestion(
                action_type=ProactiveActionType.OFFER_HELP,
                message="Veo que estÃ¡s comparando opciones. Â¿Te gustarÃ­a que te ayude a encontrar la mejor opciÃ³n para tus necesidades?",
                priority=7,
                context="researcher_needs_help",
                trigger_reason="Cliente investigando opciones"
            )
            suggestions.append(suggestion)
        
        # 6. Follow-up si es warm lead sin actividad
        if behavior_analysis.purchase_signal == PurchaseSignal.MEDIUM:
            if time_since_last_message and time_since_last_message > 180:  # 3 minutos
                suggestion = ProactiveSuggestion(
                    action_type=ProactiveActionType.FOLLOW_UP,
                    message="Â¿Tienes alguna pregunta sobre los productos que vimos? Estoy aquÃ­ para ayudarte.",
                    priority=5,
                    context="warm_lead_followup",
                    trigger_reason="Warm lead sin actividad reciente"
                )
                suggestions.append(suggestion)
        
        # Ordenar por prioridad (mayor primero)
        suggestions.sort(key=lambda x: x.priority, reverse=True)
        
        return suggestions
    
    def should_be_proactive(self, suggestions: List[ProactiveSuggestion], min_priority: int = 7) -> bool:
        """
        Determina si deberÃ­a ser proactivo ahora.
        
        Args:
            suggestions: Lista de sugerencias
            min_priority: Prioridad mÃ­nima para ser proactivo
            
        Returns:
            True si deberÃ­a ser proactivo
        """
        if not suggestions:
            return False
        
        # Ser proactivo si hay sugerencias de alta prioridad
        return any(s.priority >= min_priority for s in suggestions)



