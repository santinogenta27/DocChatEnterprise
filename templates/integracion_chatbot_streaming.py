"""
Template con Streaming: Muestra respuesta mientras se genera

Útil para mejorar la experiencia del usuario mostrando la respuesta
palabra por palabra mientras se genera.
"""

from docchat.chatbot_sdk import DocChatClient

# ==================== CONFIGURACIÓN ====================
CHATBOT_ID = "tu-chatbot-id-aqui"
API_KEY = "tu-api-key-aqui"
API_URL = "https://tu-servidor.com"

client = DocChatClient(CHATBOT_ID, API_KEY, API_URL)


def responder_cliente_streaming(pregunta_cliente: str):
    """
    Responde con streaming (palabra por palabra).
    
    Útil para mostrar la respuesta mientras se genera.
    
    Args:
        pregunta_cliente: Pregunta del cliente
    
    Yields:
        Fragmentos de la respuesta mientras se genera
    """
    for chunk in client.preguntar_stream(pregunta_cliente):
        yield chunk


# ==================== EJEMPLO DE USO ====================
if __name__ == "__main__":
    pregunta = "¿Cuál es la política de devoluciones?"
    
    print(f"Cliente pregunta: {pregunta}\n")
    print("Respuesta (streaming): ", end="", flush=True)
    
    # Mostrar respuesta palabra por palabra
    for chunk in responder_cliente_streaming(pregunta):
        print(chunk, end="", flush=True)
    
    print("\n")  # Nueva línea al final


