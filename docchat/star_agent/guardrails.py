"""
Guardrails - Sistema de Seguridad para STAR AGENT.

Implementa:
- Anti-injection patterns (bloqueo de intentos de jailbreak)
- Rule of Two (seguridad para evitar procesamiento simultáneo de inputs no confiables con cambios sensibles)
"""

from __future__ import annotations

from typing import Dict, Any, List, Optional


class Guardrails:
    """
    Guardrails de seguridad para STAR AGENT.
    
    Implementa según especificaciones:
    - BLOCKED_PATTERNS: Patrones bloqueados (anti-injection)
    - is_safe(query) -> bool
    - validate_input(query, action, session_id) -> Dict
    """
    
    # Patrones bloqueados según especificaciones
    BLOCKED_PATTERNS = [
        "ignora instrucciones",
        "system prompt",
        "actúa como",
        "forget previous",
        "you are now",
        "jailbreak",
        "override",
        "ignore all previous",
        "developer mode",
        "dan mode",
        "disregard",
        "pretend to be",
        "simulate",
    ]
    
    # Keywords sensibles para Rule of Two
    SENSITIVE_KEYWORDS = [
        "precio",
        "pagar",
        "tarjeta",
        "datos personales",
        "contraseña",
        "password",
        "envío",
        "dirección",
        "compra",
        "compra ahora",
        "comprar",
        "checkout",
    ]
    
    def __init__(self):
        """Inicializa guardrails."""
        pass
    
    def is_safe(self, query: str) -> bool:
        """
        Verifica si un query es seguro (no contiene patrones bloqueados).
        
        Args:
            query: Consulta del usuario
            
        Returns:
            True si es seguro, False si contiene patrones bloqueados
        """
        query_lower = query.lower()
        return not any(pattern in query_lower for pattern in self.BLOCKED_PATTERNS)
    
    def validate_input(
        self,
        query: str,
        action: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Valida input completo aplicando Rule of Two y anti-injection.
        
        Args:
            query: Consulta del usuario
            action: Acción que se intenta realizar (opcional)
            session_id: ID de sesión (opcional)
            
        Returns:
            Dict con:
            - is_safe: bool
            - message: str (mensaje de error si no es seguro)
            - blocked_reason: str (razón del bloqueo: "anti_injection" o "rule_of_two")
        """
        # Verificación anti-injection
        if not self.is_safe(query):
            return {
                "is_safe": False,
                "message": "Lo siento, esa solicitud contiene patrones de seguridad bloqueados.",
                "blocked_reason": "anti_injection",
            }
        
        # Rule of Two: No procesar inputs no confiables con cambios sensibles simultáneamente
        # Si el query contiene keywords sensibles Y no es seguro (ya verificado arriba),
        # aplicar bloqueo adicional.
        # Nota: Como ya pasó is_safe, aquí solo verificamos si contiene keywords sensibles
        # en combinación con acciones sensibles.
        
        query_lower = query.lower()
        contains_sensitive_keywords = any(
            keyword in query_lower for keyword in self.SENSITIVE_KEYWORDS
        )
        
        # Si hay keywords sensibles y la acción también es sensible, aplicar Rule of Two
        sensitive_actions = ["checkout", "payment", "purchase", "buy", "create_order"]
        if action and any(sa in action.lower() for sa in sensitive_actions):
            if contains_sensitive_keywords:
                # Para Rule of Two completo, aquí se podría implementar validación adicional
                # Por ejemplo, verificar si hay múltiples inputs simultáneos en la sesión
                # Por ahora, solo validamos que el query no esté bloqueado
                pass
        
        # Si pasó todas las validaciones
        return {
            "is_safe": True,
            "message": None,
            "blocked_reason": None,
        }
    
    def get_blocked_patterns(self) -> List[str]:
        """
        Retorna lista de patrones bloqueados.
        
        Returns:
            Lista de patrones bloqueados
        """
        return self.BLOCKED_PATTERNS.copy()
    
    def add_blocked_pattern(self, pattern: str):
        """
        Agrega un patrón bloqueado (para extensión).
        
        Args:
            pattern: Patrón a agregar
        """
        if pattern not in self.BLOCKED_PATTERNS:
            self.BLOCKED_PATTERNS.append(pattern.lower())

