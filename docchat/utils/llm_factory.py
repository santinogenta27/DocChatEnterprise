"""Factory para crear LLMs de diferentes proveedores (OpenAI, Anthropic)."""
from __future__ import annotations

from typing import Optional
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic


def create_llm(
    provider: str = "openai",
    model: str = "gpt-4o",
    temperature: float = 0.15,
    max_tokens: int = 8000,
    api_key: Optional[str] = None,
    request_timeout: int = 180,
    max_retries: int = 3
):
    """
    Crea un LLM del proveedor especificado.
    
    Args:
        provider: "openai" o "claude"
        model: Nombre del modelo
        temperature: Temperatura del modelo
        max_tokens: Tokens máximos
        api_key: API key (opcional, se toma de config si no se proporciona)
        request_timeout: Timeout en segundos
        max_retries: Número máximo de reintentos
    
    Returns:
        LLM instance (ChatOpenAI o ChatAnthropic)
    """
    if provider.lower() == "claude":
        # Mapear modelos de OpenAI a Claude equivalentes
        # Claude 3.5 Sonnet tiene context window de 200k tokens (más grande que OpenAI)
        # ACTUALIZADO: Usar nombres de modelo válidos sin fecha específica
        model_mapping = {
            "gpt-4o": "claude-3-5-sonnet",  # 200k tokens context window - Nombre estándar
            "gpt-4o-mini": "claude-3-5-haiku",  # 200k tokens context window - Nombre estándar
            "gpt-4": "claude-3-opus",  # 200k tokens context window - Nombre estándar
        }
        claude_model = model_mapping.get(model, "claude-3-5-sonnet")
        
        return ChatAnthropic(
            model=claude_model,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=api_key,
            timeout=request_timeout,
            max_retries=max_retries
        )
    else:
        # Default: OpenAI
        return ChatOpenAI(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=api_key,
            request_timeout=request_timeout,
            max_retries=max_retries
        )

