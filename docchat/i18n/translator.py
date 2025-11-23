"""
Sistema de multi-idioma automático.
"""

from __future__ import annotations

from typing import Dict, Optional
from langchain_openai import ChatOpenAI

from ..config import AppConfig


class MultiLanguageTranslator:
    """
    Traductor multi-idioma para respuestas automáticas.
    """
    
    SUPPORTED_LANGUAGES = {
        "es": "Español",
        "en": "English",
        "pt": "Português",
        "fr": "Français",
        "de": "Deutsch",
        "it": "Italiano",
        "zh": "中文",
        "ja": "日本語"
    }
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.llm = ChatOpenAI(
            model=config.research_model or "gpt-4o",
            api_key=config.openai_api_key,
            temperature=0.3
        )
    
    def detect_language(self, text: str) -> str:
        """Detecta idioma del texto."""
        # Detección básica (se puede mejorar con modelo dedicado)
        if any(word in text.lower() for word in ["the", "is", "are", "and", "or"]):
            return "en"
        elif any(word in text.lower() for word in ["o", "a", "é", "de", "da"]):
            return "pt"
        elif any(word in text.lower() for word in ["le", "la", "les", "de", "et"]):
            return "fr"
        elif any(word in text.lower() for word in ["der", "die", "das", "und", "oder"]):
            return "de"
        elif any(word in text.lower() for word in ["el", "la", "los", "las", "y", "o"]):
            return "es"
        
        return "es"  # Default
    
    def translate(self, text: str, target_language: str, source_language: Optional[str] = None) -> str:
        """Traduce texto a idioma objetivo."""
        if not source_language:
            source_language = self.detect_language(text)
        
        if source_language == target_language:
            return text
        
        prompt = f"""Traduce el siguiente texto del {self.SUPPORTED_LANGUAGES.get(source_language, source_language)} 
al {self.SUPPORTED_LANGUAGES.get(target_language, target_language)}.
Mantén el formato, estructura y significado exacto.

Texto a traducir:
{text}

Traducción:"""
        
        try:
            response = self.llm.invoke(prompt)
            return response.content.strip()
        except Exception as e:
            print(f"Error traduciendo: {e}")
            return text
    
    def translate_response(self, response: str, user_language: str) -> str:
        """Traduce respuesta al idioma del usuario."""
        detected = self.detect_language(response)
        if detected != user_language:
            return self.translate(response, user_language, detected)
        return response

