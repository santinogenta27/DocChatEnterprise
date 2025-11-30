"""
Template Super Simple para Integrar tu Chatbot con DocChat Enterprise

Este es el código más simple posible. Solo necesitas:
1. Instalar: pip install docchat-enterprise-sdk
2. Copiar este código
3. Cambiar chatbot_id y api_key
4. ¡Listo!
"""

from docchat.chatbot_sdk import DocChatClient

# ==================== CONFIGURACIÓN (CAMBIA ESTO) ====================
CHATBOT_ID = "tu-chatbot-id-aqui"  # Lo obtienes al registrar tu chatbot
API_KEY = "tu-api-key-aqui"  # Lo obtienes al registrar tu chatbot
API_URL = "https://tu-servidor.com"  # URL de tu servidor DocChat Enterprise

# ==================== INICIALIZAR CLIENTE ====================
client = DocChatClient(
    chatbot_id=CHATBOT_ID,
    api_key=API_KEY,
    api_url=API_URL
)

# ==================== FUNCIÓN PARA TU CHATBOT ====================
def responder_cliente(pregunta_cliente: str) -> str:
    """
    Esta función la llamas desde tu chatbot cuando un cliente pregunta algo.
    
    Args:
        pregunta_cliente: La pregunta que hace el cliente
    
    Returns:
        La respuesta basada en tus documentos privados
    """
    # Opción 1: Respuesta simple (recomendado para empezar)
    respuesta = client.preguntar(pregunta_cliente)
    return respuesta
    
    # Opción 2: Respuesta inteligente (usa RAG solo si es necesario)
    # respuesta = client.responder_inteligente(pregunta_cliente)
    # return respuesta


# ==================== EJEMPLO DE USO ====================
if __name__ == "__main__":
    # Ejemplo: Cliente pregunta algo
    pregunta = "¿Cuál es la política de devoluciones?"
    
    # Tu chatbot consulta DocChat Enterprise
    respuesta = responder_cliente(pregunta)
    
    # Muestras la respuesta al cliente en tu app
    print(f"Cliente pregunta: {pregunta}")
    print(f"Respuesta: {respuesta}")


