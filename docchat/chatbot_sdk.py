"""
SDK Simple para Integración de Chatbots con DocChat Enterprise

Diseñado para ser super fácil de usar, incluso para no técnicos.
Solo necesitas 3 líneas de código para integrar.
"""

from __future__ import annotations

import requests
from typing import Optional, Dict, Any, Iterator
import json


class DocChatClient:
    """
    Cliente simple para conectar tu chatbot con DocChat Enterprise.
    
    Uso super simple (3 líneas):
    
    ```python
    client = DocChatClient(chatbot_id="tu-id", api_key="tu-key", api_url="https://tu-servidor.com")
    respuesta = client.preguntar("¿Cuál es la política de devoluciones?")
    print(respuesta)
    ```
    """
    
    def __init__(
        self,
        chatbot_id: str,
        api_key: str,
        api_url: str = "http://localhost:8000"
    ):
        """
        Inicializa el cliente.
        
        Args:
            chatbot_id: ID de tu chatbot (lo obtienes al registrarlo)
            api_key: Tu API key (la obtienes al registrarlo)
            api_url: URL del servidor DocChat Enterprise
        """
        self.chatbot_id = chatbot_id
        self.api_key = api_key
        self.api_url = api_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({"X-API-Key": api_key})
    
    def preguntar(
        self,
        pregunta: str,
        usar_reranking: bool = True,
        max_chunks: int = 5
    ) -> str:
        """
        Hace una pregunta y obtiene la respuesta.
        
        Esta es la función principal que usarás en tu chatbot.
        
        Args:
            pregunta: La pregunta del cliente
            usar_reranking: Si True, mejora la precisión (recomendado)
            max_chunks: Máximo de documentos a usar (5 es bueno)
        
        Returns:
            La respuesta basada en tus documentos privados
        """
        try:
            response = self.session.post(
                f"{self.api_url}/api/chatbot/{self.chatbot_id}/query",
                json={
                    "question": pregunta,
                    "use_reranking": usar_reranking,
                    "max_chunks": max_chunks
                },
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            return data.get("answer", "No pude generar una respuesta.")
        except requests.exceptions.RequestException as e:
            return f"Error al consultar: {str(e)}"
    
    def preguntar_completo(
        self,
        pregunta: str,
        usar_reranking: bool = True,
        max_chunks: int = 5
    ) -> Dict[str, Any]:
        """
        Hace una pregunta y obtiene respuesta completa con metadatos.
        
        Returns:
            Dict con: answer, sources, confidence, chunks_used, etc.
        """
        try:
            response = self.session.post(
                f"{self.api_url}/api/chatbot/{self.chatbot_id}/query",
                json={
                    "question": pregunta,
                    "use_reranking": usar_reranking,
                    "max_chunks": max_chunks
                },
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {
                "answer": f"Error al consultar: {str(e)}",
                "sources": [],
                "confidence": 0.0,
                "chunks_used": 0,
                "error": str(e)
            }
    
    def preguntar_stream(
        self,
        pregunta: str,
        usar_reranking: bool = True,
        max_chunks: int = 5
    ) -> Iterator[str]:
        """
        Hace una pregunta y obtiene respuesta en streaming (palabra por palabra).
        
        Útil para mostrar la respuesta mientras se genera.
        
        Yields:
            Fragmentos de la respuesta mientras se genera
        """
        try:
            response = self.session.post(
                f"{self.api_url}/api/chatbot/{self.chatbot_id}/query/stream",
                json={
                    "question": pregunta,
                    "use_reranking": usar_reranking,
                    "max_chunks": max_chunks
                },
                stream=True,
                timeout=30
            )
            response.raise_for_status()
            
            for line in response.iter_lines():
                if line:
                    try:
                        data = json.loads(line.decode('utf-8'))
                        if 'chunk' in data:
                            yield data['chunk']
                    except json.JSONDecodeError:
                        continue
        except requests.exceptions.RequestException:
            yield "Error al consultar."
    
    def necesita_rag(self, pregunta: str) -> bool:
        """
        Determina si la pregunta necesita consultar documentos privados.
        
        Útil para decidir si usar RAG o responder directamente.
        
        Returns:
            True si necesita RAG, False si puede responder directamente
        """
        try:
            response = self.session.post(
                f"{self.api_url}/api/chatbot/{self.chatbot_id}/needs-rag",
                json={"question": pregunta},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            return data.get("needs_rag", True)
        except requests.exceptions.RequestException:
            return True  # Por defecto, usar RAG si hay error
    
    def responder_inteligente(
        self,
        pregunta: str,
        respuesta_directa: Optional[str] = None
    ) -> str:
        """
        Responde inteligentemente: usa RAG solo si es necesario.
        
        Si tienes una respuesta directa del chatbot, la usa primero.
        Si no, o si la pregunta necesita documentos, usa RAG.
        
        Args:
            pregunta: La pregunta del cliente
            respuesta_directa: Respuesta directa del chatbot (opcional)
        
        Returns:
            La mejor respuesta
        """
        # Si hay respuesta directa y no necesita RAG, usar respuesta directa
        if respuesta_directa and not self.necesita_rag(pregunta):
            return respuesta_directa
        
        # Si no hay respuesta directa o necesita RAG, usar RAG
        return self.preguntar(pregunta)
    
    def obtener_info(self) -> Dict[str, Any]:
        """Obtiene información de tu chatbot."""
        try:
            response = self.session.get(
                f"{self.api_url}/api/chatbot/{self.chatbot_id}/info",
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}


# Función helper super simple para uso rápido
def conectar_chatbot(chatbot_id: str, api_key: str, api_url: str = "http://localhost:8000") -> DocChatClient:
    """
    Función helper para conectar tu chatbot en una sola línea.
    
    Ejemplo:
    ```python
    client = conectar_chatbot("tu-id", "tu-key")
    respuesta = client.preguntar("¿Cuál es la política?")
    ```
    """
    return DocChatClient(chatbot_id=chatbot_id, api_key=api_key, api_url=api_url)


