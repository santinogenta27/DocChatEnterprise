"""Intent Classifier - Clasifica la intención del usuario."""

from typing import Dict, Any, List
from langchain_core.language_models import BaseLanguageModel
from langchain_core.messages import SystemMessage, HumanMessage, BaseMessage


class IntentClassifier:
    """Clasificador de intenciones usando LLM."""
    
    INTENTS = [
        "pregunta_general",
        "consulta_productos",
        "soporte_tecnico",
        "tracking_envio",
        "devolucion_reclamo",
        "compra_asistencia",
        "conversacion_sentimiento_negativo",
        "escalamiento_humano"
    ]
    
    def __init__(self, llm: BaseLanguageModel):
        self.llm = llm
        
        self.system_prompt = """Eres un clasificador de intenciones para un agente de customer service.

Clasifica la intención del usuario en UNA de estas categorías:

1. pregunta_general - Preguntas generales sobre la empresa, productos, políticas
2. consulta_productos - Búsqueda o consulta sobre productos específicos
3. soporte_tecnico - Problemas técnicos, troubleshooting, errores
4. tracking_envio - Consulta sobre estado de envío o pedido
5. devolucion_reclamo - Solicitudes de devolución, reembolso, reclamos
6. compra_asistencia - Ayuda para completar una compra, checkout
7. conversacion_sentimiento_negativo - Frustración, enojo detectado
8. escalamiento_humano - Solicitud explícita de hablar con humano

Responde SOLO con el nombre de la intención en una línea, sin explicaciones.

Formato: intent_name|confidence (0.0-1.0)
Ejemplo: consulta_productos|0.95"""

    def classify(self, user_message: str, conversation_history: List[BaseMessage] = None) -> Dict[str, Any]:
        """Clasifica la intención del mensaje del usuario.
        
        Returns:
            {
                "intent": str,
                "confidence": float
            }
        """
        try:
            messages = [SystemMessage(content=self.system_prompt)]
            
            # Agregar historial reciente si existe (últimos 3 mensajes)
            if conversation_history:
                for msg in conversation_history[-3:]:
                    if hasattr(msg, 'content'):
                        messages.append(msg)
            
            messages.append(HumanMessage(content=f"Mensaje del usuario: {user_message}\n\nClasifica la intención:"))
            
            response = self.llm.invoke(messages)
            response_text = response.content.strip() if hasattr(response, 'content') else str(response)
            
            # Parsear respuesta
            if "|" in response_text:
                intent_part, confidence_part = response_text.split("|", 1)
                intent = intent_part.strip().lower()
                try:
                    confidence = float(confidence_part.strip())
                except:
                    confidence = 0.7
            else:
                intent = response_text.strip().lower()
                confidence = 0.7
            
            # Validar que la intención sea válida
            if intent not in self.INTENTS:
                # Si no coincide exactamente, buscar la más similar
                intent = "pregunta_general"  # Fallback
                confidence = 0.5
            
            return {
                "intent": intent,
                "confidence": min(max(confidence, 0.0), 1.0)  # Clamp entre 0 y 1
            }
        except Exception as e:
            print(f"⚠️ Error clasificando intención: {e}")
            return {
                "intent": "pregunta_general",
                "confidence": 0.5
            }

