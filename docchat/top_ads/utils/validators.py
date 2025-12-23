"""
Ads Policy Validator - Valida creativos contra políticas
de Meta y TikTok Ads
"""

from __future__ import annotations

from typing import Dict, Optional, Tuple
from langchain_core.language_models import BaseLanguageModel
from langchain_core.messages import SystemMessage, HumanMessage
import re

from ...config import AppConfig
from .logger import TopAdsLogger


class AdsPolicyValidator:
    """
    Validador de políticas de ads.
    
    Valida:
    - Contenido prohibido
    - Lenguaje inapropiado
    - Claims falsos
    - Políticas de Meta Ads
    - Políticas de TikTok Ads
    """
    
    def __init__(
        self,
        llm: BaseLanguageModel,
        logger: TopAdsLogger
    ):
        self.llm = llm
        self.logger = logger
        
        # Palabras prohibidas comunes
        self.prohibited_words = [
            "gratis", "free", "100%", "garantizado", "sin riesgo",
            # Agregar más según políticas
        ]
    
    def validate_creative(
        self,
        creative: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """
        Valida un creative contra políticas de ads.
        
        Args:
            creative: Creative a validar
        
        Returns:
            Tuple (is_valid, reason)
        """
        # Validación básica de palabras prohibidas
        text_content = f"{creative.get('headline', '')} {creative.get('primary_text', '')} {creative.get('description', '')}"
        text_lower = text_content.lower()
        
        for word in self.prohibited_words:
            if word in text_lower:
                return False, f"Contiene palabra prohibida: {word}"
        
        # Validación con LLM
        try:
            is_valid, reason = self._validate_with_llm(creative)
            return is_valid, reason
        except Exception as e:
            self.logger.warning(f"Error validando con LLM: {e}")
            # Si falla LLM, pasar validación básica
            return True, None
    
    def _validate_with_llm(
        self,
        creative: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """Valida creative usando LLM."""
        prompt = f"""Valida este creative publicitario contra las políticas de Meta Ads y TikTok Ads:

Headline: {creative.get('headline', '')}
Primary Text: {creative.get('primary_text', '')}
Description: {creative.get('description', '')}
CTA: {creative.get('cta', '')}

Verifica:
1. ¿Contiene contenido prohibido?
2. ¿Hace claims falsos o exagerados?
3. ¿Usa lenguaje inapropiado?
4. ¿Cumple con políticas de publicidad?

Responde en formato JSON:
{{
    "is_valid": true/false,
    "reason": "razón si no es válido"
}}"""
        
        try:
            response = self.llm.invoke([
                SystemMessage(content="Eres un experto en políticas de publicidad de Meta y TikTok."),
                HumanMessage(content=prompt)
            ])
            
            content = response.content if hasattr(response, 'content') else str(response)
            
            # Parsear JSON
            import json
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return result.get("is_valid", True), result.get("reason")
            else:
                return True, None
                
        except Exception as e:
            self.logger.error(f"Error en validación LLM: {e}")
            return True, None






































