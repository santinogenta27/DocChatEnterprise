"""Factory para crear LLMs de diferentes proveedores (OpenAI, Anthropic)."""
from __future__ import annotations

from typing import Optional
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic


def create_llm(
    provider: str = "openai",
    model: str = "gpt-4o",
    temperature: float = 0.15,
    max_tokens: Optional[int] = None,  # None = sin límite, la API decide
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
        max_tokens: Tokens máximos (None = sin límite, la API decide la longitud)
        api_key: API key (opcional, se toma de config si no se proporciona)
        request_timeout: Timeout en segundos
        max_retries: Número máximo de reintentos
    
    Returns:
        LLM instance (ChatOpenAI o ChatAnthropic)
    """
    if provider.lower() == "claude":
        # Mapear modelos de OpenAI a Claude equivalentes
        # ACTUALIZADO: Usar modelos Claude 4.5 (familia actual)
        # Claude Sonnet 4.5: Mejor balance inteligencia/velocidad/costo
        # Claude Opus 4.5: Mejor modelo para codificación y agentes
        # Claude Haiku 4.5: Más rápido y económico
        model_mapping = {
            "gpt-4o": "claude-sonnet-4-5-20250929",  # Claude Sonnet 4.5 (recomendado) - Mejor balance
            "gpt-4o-mini": "claude-haiku-4-5-20251001",  # Claude Haiku 4.5 - Más rápido y económico
            "gpt-4": "claude-opus-4-5-20251101",  # Claude Opus 4.5 - Mejor para codificación y agentes
        }
        claude_model = model_mapping.get(model, "claude-sonnet-4-5-20250929")  # Default: Sonnet 4.5
        
        # Construir kwargs dinámicamente para no pasar max_tokens si es None
        kwargs = {
            "model": claude_model,
            "temperature": temperature,
            "api_key": api_key,
            "timeout": request_timeout,
            "max_retries": max_retries
        }
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens
        else:
            # Para Anthropic, si no queremos límite, ponemos un valor muy alto
            # porque Anthropic REQUIERE max_tokens
            kwargs["max_tokens"] = 16384  # Máximo permitido por Claude
        
        return ChatAnthropic(**kwargs)
    else:
        # Default: OpenAI
        # OpenAI no requiere max_tokens, si es None simplemente no lo pasamos
        kwargs = {
            "model": model,
            "temperature": temperature,
            "api_key": api_key,
            "request_timeout": request_timeout,
            "max_retries": max_retries
        }
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens
        # Si max_tokens es None, no lo pasamos y OpenAI usará su límite por defecto del modelo
        
        return ChatOpenAI(**kwargs)

