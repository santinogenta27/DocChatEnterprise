"""Response Validator - Valida respuestas antes de enviarlas al usuario."""

from typing import Dict, Any, Optional, List
from langchain_core.language_models import BaseLanguageModel
from langchain_core.messages import SystemMessage, HumanMessage


class ResponseValidator:
    """Validador automático de respuestas - verifica factual correctness, policy compliance, hallucination risk."""
    
    def __init__(self, llm: BaseLanguageModel):
        self.llm = llm
        
        self.validation_prompt = """Eres un validador de respuestas para un agente de customer service.

Tu tarea es validar si una respuesta es:
1. Factualmente correcta (basada en el contexto proporcionado)
2. Cumple con políticas (no promete cosas no autorizadas)
3. No contiene alucinaciones (no inventa información)

Responde SOLO con:
- PASS: Si la respuesta es válida
- FAIL: Si la respuesta tiene problemas

Si es FAIL, indica brevemente el problema (máximo 20 palabras)."""
    
    def validate(
        self,
        response_text: str,
        context: List[Dict[str, Any]] = None,
        user_query: str = None
    ) -> Dict[str, Any]:
        """Valida una respuesta.
        
        Returns:
            {
                "valid": bool,
                "reason": str,
                "confidence": float
            }
        """
        try:
            # Construir prompt de validación
            context_text = ""
            if context:
                context_text = "\n\n".join([
                    f"[{i+1}] {doc.get('content', '')[:200]}"
                    for i, doc in enumerate(context[:3])
                ])
            
            validation_query = f"""Respuesta a validar: "{response_text}"

Contexto disponible:
{context_text if context_text else "No hay contexto disponible"}

Pregunta del usuario: {user_query or "N/A"}

¿Esta respuesta es válida?"""
            
            messages = [
                SystemMessage(content=self.validation_prompt),
                HumanMessage(content=validation_query)
            ]
            
            response = self.llm.invoke(messages)
            response_text_validator = response.content if hasattr(response, 'content') else str(response)
            
            # Parsear respuesta
            response_upper = response_text_validator.upper()
            
            if "PASS" in response_upper:
                return {
                    "valid": True,
                    "reason": "Validación exitosa",
                    "confidence": 0.9
                }
            elif "FAIL" in response_upper:
                # Extraer razón del fallo
                reason = response_text_validator.replace("FAIL", "").replace("fail", "").strip()
                if not reason:
                    reason = "Respuesta no válida"
                
                return {
                    "valid": False,
                    "reason": reason[:100],  # Limitar longitud
                    "confidence": 0.3
                }
            else:
                # Si no está claro, asumir válido pero con menor confianza
                return {
                    "valid": True,
                    "reason": "Validación ambigua",
                    "confidence": 0.6
                }
                
        except Exception as e:
            print(f"⚠️ Error en validación: {e}")
            # En caso de error, permitir la respuesta pero con baja confianza
            return {
                "valid": True,
                "reason": f"Error en validación: {str(e)}",
                "confidence": 0.5
            }

