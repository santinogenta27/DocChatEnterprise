"""
Conversational Flow - Flujo conversacional mejorado con preguntas proactivas
y sugerencias inteligentes basadas en intención del usuario
"""

from __future__ import annotations

from enum import Enum
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from langchain_core.language_models import BaseLanguageModel
from langchain_core.messages import SystemMessage, HumanMessage
import json
import re


class UserIntent(Enum):
    """Intenciones del usuario."""
    DISCOVER = "discover"  # Descubrir productos
    COMPARE = "compare"  # Comparar productos
    BUY = "buy"  # Comprar
    ASK_QUESTION = "ask_question"  # Hacer pregunta
    CHECKOUT = "checkout"  # Proceder al checkout
    TRACK_ORDER = "track_order"  # Rastrear orden


@dataclass
class ProactiveQuestion:
    """Pregunta proactiva para hacer al usuario."""
    question: str
    intent: UserIntent
    context: Dict[str, Any]
    suggested_actions: List[str] = None
    
    def __post_init__(self):
        if self.suggested_actions is None:
            self.suggested_actions = []


class ConversationalFlow:
    """
    Gestor de flujo conversacional mejorado.
    
    Características:
    - Detecta intención del usuario
    - Hace preguntas proactivas
    - Sugiere productos relevantes
    - Guía el flujo de compra
    """
    
    def __init__(self, llm: BaseLanguageModel):
        """
        Inicializa el flujo conversacional.
        
        Args:
            llm: Modelo de lenguaje para análisis de intención
        """
        self.llm = llm
        self.conversation_history: List[Dict[str, Any]] = []
    
    def detect_intent(self, user_message: str, context: Optional[Dict[str, Any]] = None) -> UserIntent:
        """
        Detecta la intención del usuario.
        
        Args:
            user_message: Mensaje del usuario
            context: Contexto adicional (productos vistos, carrito, etc.)
        
        Returns:
            UserIntent detectado
        """
        prompt = f"""Analiza el siguiente mensaje del usuario y determina su intención:

Mensaje: "{user_message}"

Contexto:
{json.dumps(context or {}, indent=2)}

Intenciones posibles:
- DISCOVER: Quiere descubrir/buscar productos
- COMPARE: Quiere comparar productos
- BUY: Quiere comprar algo específico
- ASK_QUESTION: Hace una pregunta sobre productos
- CHECKOUT: Quiere proceder al checkout
- TRACK_ORDER: Quiere rastrear una orden

Responde SOLO con el nombre de la intención (ej: DISCOVER, BUY, etc.)"""
        
        try:
            response = self.llm.invoke([
                SystemMessage(content="Eres un experto en análisis de intención del usuario en e-commerce."),
                HumanMessage(content=prompt)
            ])
            
            content = response.content if hasattr(response, 'content') else str(response)
            content = content.strip().upper()
            
            # Mapear a enum
            for intent in UserIntent:
                if intent.value.upper() in content or intent.name in content:
                    return intent
            
            # Default: DISCOVER
            return UserIntent.DISCOVER
            
        except Exception as e:
            print(f"⚠️ Error detectando intención: {e}")
            return UserIntent.DISCOVER
    
    def generate_proactive_question(
        self,
        intent: UserIntent,
        context: Dict[str, Any],
        conversation_history: Optional[List[Dict[str, Any]]] = None
    ) -> Optional[ProactiveQuestion]:
        """
        Genera una pregunta proactiva basada en la intención y contexto.
        
        Args:
            intent: Intención del usuario
            context: Contexto actual (productos, carrito, etc.)
            conversation_history: Historial de conversación
        
        Returns:
            ProactiveQuestion o None
        """
        if intent == UserIntent.DISCOVER:
            return self._generate_discover_question(context)
        elif intent == UserIntent.COMPARE:
            return self._generate_compare_question(context)
        elif intent == UserIntent.BUY:
            return self._generate_buy_question(context)
        elif intent == UserIntent.ASK_QUESTION:
            return self._generate_question_response(context)
        elif intent == UserIntent.CHECKOUT:
            return self._generate_checkout_question(context)
        else:
            return None
    
    def _generate_discover_question(self, context: Dict[str, Any]) -> ProactiveQuestion:
        """Genera pregunta proactiva para descubrimiento."""
        products_viewed = context.get("products_viewed", [])
        
        if not products_viewed:
            question = "¿Qué tipo de producto estás buscando? Puedo ayudarte a encontrar exactamente lo que necesitas."
            suggested_actions = ["Buscar por categoría", "Ver productos populares", "Filtrar por precio"]
        else:
            question = f"Veo que has visto {len(products_viewed)} producto(s). ¿Te gustaría ver opciones similares o tienes alguna pregunta específica?"
            suggested_actions = ["Ver productos similares", "Comparar opciones", "Ver detalles"]
        
        return ProactiveQuestion(
            question=question,
            intent=UserIntent.DISCOVER,
            context=context,
            suggested_actions=suggested_actions
        )
    
    def _generate_compare_question(self, context: Dict[str, Any]) -> ProactiveQuestion:
        """Genera pregunta proactiva para comparación."""
        products_to_compare = context.get("products_to_compare", [])
        
        if len(products_to_compare) < 2:
            question = "¿Qué productos te gustaría comparar? Puedo ayudarte a ver las diferencias entre opciones."
            suggested_actions = ["Seleccionar productos", "Ver características"]
        else:
            question = f"Perfecto, tienes {len(products_to_compare)} productos para comparar. ¿En qué aspectos te gustaría compararlos? (precio, características, reviews, etc.)"
            suggested_actions = ["Comparar precios", "Comparar características", "Ver reviews"]
        
        return ProactiveQuestion(
            question=question,
            intent=UserIntent.COMPARE,
            context=context,
            suggested_actions=suggested_actions
        )
    
    def _generate_buy_question(self, context: Dict[str, Any]) -> ProactiveQuestion:
        """Genera pregunta proactiva para compra."""
        cart_items = context.get("cart_items", [])
        product = context.get("current_product")
        
        if product:
            question = f"¿Te gustaría agregar '{product.get('title', 'este producto')}' al carrito? También puedo ayudarte a elegir variantes (color, tamaño, etc.)."
            suggested_actions = ["Agregar al carrito", "Elegir variantes", "Ver más detalles"]
        elif cart_items:
            question = f"Tienes {len(cart_items)} producto(s) en tu carrito. ¿Te gustaría proceder al checkout o agregar más productos?"
            suggested_actions = ["Ir al checkout", "Seguir comprando", "Ver carrito"]
        else:
            question = "¿Qué producto te gustaría comprar? Puedo ayudarte a encontrarlo y agregarlo al carrito."
            suggested_actions = ["Buscar productos", "Ver categorías"]
        
        return ProactiveQuestion(
            question=question,
            intent=UserIntent.BUY,
            context=context,
            suggested_actions=suggested_actions
        )
    
    def _generate_question_response(self, context: Dict[str, Any]) -> ProactiveQuestion:
        """Genera respuesta a pregunta del usuario."""
        question = "¿Hay algo más en lo que pueda ayudarte? Puedo responder preguntas sobre productos, envíos, pagos, etc."
        suggested_actions = ["Preguntar sobre producto", "Información de envío", "Métodos de pago"]
        
        return ProactiveQuestion(
            question=question,
            intent=UserIntent.ASK_QUESTION,
            context=context,
            suggested_actions=suggested_actions
        )
    
    def _generate_checkout_question(self, context: Dict[str, Any]) -> ProactiveQuestion:
        """Genera pregunta proactiva para checkout."""
        cart_total = context.get("cart_total", 0)
        cart_items = context.get("cart_items", [])
        
        if cart_items:
            question = f"Perfecto, tienes {len(cart_items)} producto(s) por un total de ${cart_total:.2f}. ¿Estás listo para proceder al pago? Necesitaré tu dirección de envío y método de pago."
            suggested_actions = ["Proceder al pago", "Revisar carrito", "Agregar cupón"]
        else:
            question = "Tu carrito está vacío. ¿Te gustaría buscar productos para agregar?"
            suggested_actions = ["Buscar productos", "Ver categorías"]
        
        return ProactiveQuestion(
            question=question,
            intent=UserIntent.CHECKOUT,
            context=context,
            suggested_actions=suggested_actions
        )
    
    def suggest_next_step(
        self,
        intent: UserIntent,
        context: Dict[str, Any]
    ) -> str:
        """
        Sugiere el siguiente paso en el flujo de compra.
        
        Args:
            intent: Intención actual
            context: Contexto actual
        
        Returns:
            Sugerencia de siguiente paso
        """
        suggestions = {
            UserIntent.DISCOVER: "Puedo ayudarte a buscar productos. ¿Qué estás buscando?",
            UserIntent.COMPARE: "¿Qué productos te gustaría comparar?",
            UserIntent.BUY: "¿Qué producto te gustaría agregar al carrito?",
            UserIntent.ASK_QUESTION: "¿Sobre qué te gustaría saber más?",
            UserIntent.CHECKOUT: "¿Estás listo para proceder al pago?",
            UserIntent.TRACK_ORDER: "¿Cuál es el número de tu orden?"
        }
        
        return suggestions.get(intent, "¿En qué puedo ayudarte?")

