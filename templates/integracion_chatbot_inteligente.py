"""
Template Inteligente: Usa RAG solo cuando sea necesario

Este template decide automáticamente si usar RAG o responder directamente.
Más eficiente y rápido.
"""

from docchat.chatbot_sdk import DocChatClient
from typing import Optional

# ==================== CONFIGURACIÓN ====================
CHATBOT_ID = "tu-chatbot-id-aqui"
API_KEY = "tu-api-key-aqui"
API_URL = "https://tu-servidor.com"

client = DocChatClient(CHATBOT_ID, API_KEY, API_URL)


def responder_cliente_inteligente(
    pregunta_cliente: str,
    respuesta_directa: Optional[str] = None
) -> str:
    """
    Responde inteligentemente:
    - Si tienes respuesta directa y no necesita RAG → usa respuesta directa
    - Si no tienes respuesta o necesita RAG → usa DocChat Enterprise
    
    Args:
        pregunta_cliente: Pregunta del cliente
        respuesta_directa: Respuesta que ya tienes (opcional)
    
    Returns:
        La mejor respuesta
    """
    # Si tienes respuesta directa, intenta usarla primero
    if respuesta_directa:
        # Verifica si necesita RAG
        necesita_rag = client.necesita_rag(pregunta_cliente)
        
        if not necesita_rag:
            # No necesita RAG, usa respuesta directa
            return respuesta_directa
    
    # Necesita RAG o no hay respuesta directa, consulta DocChat Enterprise
    return client.preguntar(pregunta_cliente)


# ==================== EJEMPLO DE USO ====================
if __name__ == "__main__":
    # Caso 1: Pregunta simple (saludo) - No necesita RAG
    pregunta1 = "Hola, ¿cómo estás?"
    respuesta1 = responder_cliente_inteligente(
        pregunta1,
        respuesta_directa="¡Hola! Estoy muy bien, gracias por preguntar. ¿En qué puedo ayudarte?"
    )
    print(f"Pregunta: {pregunta1}")
    print(f"Respuesta: {respuesta1}\n")
    
    # Caso 2: Pregunta sobre políticas - Necesita RAG
    pregunta2 = "¿Cuál es la política de devoluciones?"
    respuesta2 = responder_cliente_inteligente(pregunta2)
    print(f"Pregunta: {pregunta2}")
    print(f"Respuesta: {respuesta2}")


