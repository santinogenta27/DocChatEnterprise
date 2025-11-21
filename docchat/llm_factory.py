"""Factory for creating different LLM models - OpenAI only."""

from __future__ import annotations

from typing import Optional
from langchain_openai import ChatOpenAI

from .config import AppConfig


class LLMFactory:
    """Factory for creating LLM instances - OpenAI only."""
    
    @staticmethod
    def create_llm(
        model_name: str,
        config: AppConfig,
        temperature: Optional[float] = None,
        **kwargs
    ):
        """Create an LLM instance - OpenAI only."""
        temperature = temperature if temperature is not None else config.temperature
        
        if not config.openai_api_key:
            raise ValueError("OPENAI_API_KEY required")
        
        return ChatOpenAI(
            model=model_name,
            temperature=temperature,
            api_key=config.openai_api_key,
            **kwargs
        )
    
    @staticmethod
    def get_model_provider(model_name: str) -> str:
        """Get the provider name for a model."""
        return "openai"  # Only OpenAI supported

