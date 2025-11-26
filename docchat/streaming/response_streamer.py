"""
Streaming de respuestas para mostrar resultados mientras se generan.
"""

from __future__ import annotations

from typing import AsyncIterator, Iterator, Optional
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult


class StreamingCallbackHandler(BaseCallbackHandler):
    """Callback handler para streaming de respuestas."""
    
    def __init__(self):
        self.tokens = []
        self.finished = False
    
    def on_llm_new_token(self, token: str, **kwargs) -> None:
        """Se llama cuando se genera un nuevo token."""
        self.tokens.append(token)
    
    def on_llm_end(self, response: LLMResult, **kwargs) -> None:
        """Se llama cuando termina la generación."""
        self.finished = True
    
    def get_tokens(self) -> str:
        """Obtiene todos los tokens generados."""
        return "".join(self.tokens)


class ResponseStreamer:
    """
    Streamer de respuestas para mostrar resultados en tiempo real.
    """
    
    def __init__(self):
        self.callback_handler = StreamingCallbackHandler()
    
    def stream_response(self, llm, prompt: str) -> Iterator[str]:
        """
        Genera respuesta en streaming.
        
        Yields:
            token: Token generado
        """
        # Configurar callback para streaming
        from langchain_core.messages import HumanMessage
        
        messages = [HumanMessage(content=prompt)]
        
        # Stream de tokens
        for token in llm.stream(messages):
            if hasattr(token, 'content'):
                yield token.content
            elif isinstance(token, str):
                yield token
    
    async def astream_response(self, llm, prompt: str) -> AsyncIterator[str]:
        """
        Genera respuesta en streaming asíncrono.
        
        Yields:
            token: Token generado
        """
        from langchain_core.messages import HumanMessage
        
        messages = [HumanMessage(content=prompt)]
        
        async for token in llm.astream(messages):
            if hasattr(token, 'content'):
                yield token.content
            elif isinstance(token, str):
                yield token

