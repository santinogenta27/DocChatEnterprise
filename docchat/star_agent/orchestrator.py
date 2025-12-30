"""
Orchestrator - Decision Layer para STAR AGENT.

Implementa la capa de decisión que determina qué acción tomar
basándose en la consulta del usuario y el contexto disponible.
"""

from __future__ import annotations

from typing import Dict, Any, Optional


class Orchestrator:
    """
    Orquestador que decide acciones según consulta y contexto.
    
    Implementa según especificaciones:
    - decide_action(query, context) -> acción
    - handle_action(action, query, context) -> resultado
    """
    
    def decide_action(self, query: str, context: str) -> str:
        """
        Decide qué acción tomar basándose en la consulta y contexto.
        
        Args:
            query: Consulta del usuario
            context: Contexto recuperado del RAG
            
        Returns:
            Acción a tomar: "answer", "start_checkout", "handoff_human", "ask_clarification"
        """
        q = query.lower()
        
        # Si menciona comprar, iniciar checkout
        if "comprar" in q or "pagar" in q or "checkout" in q:
            return "start_checkout"
        
        # Si solicita hablar con humano
        if any(x in q for x in ["hablar con alguien", "asesor humano", "persona", "operador", "agente humano"]):
            return "handoff_human"
        
        # Si el contexto es insuficiente (< 200 caracteres), pedir clarificación
        if len(context) < 200:
            return "ask_clarification"
        
        # Por defecto, responder
        return "answer"
    
    def handle_action(
        self,
        action: str,
        query: str,
        context: str,
        session_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Maneja la acción decidida y retorna el resultado.
        
        Args:
            action: Acción a ejecutar
            query: Consulta del usuario
            context: Contexto disponible
            session_data: Datos de sesión opcionales
            
        Returns:
            Diccionario con resultado de la acción:
            - needs_handoff: bool
            - needs_clarification: bool
            - needs_checkout: bool
            - message: str (mensaje opcional)
        """
        session_data = session_data or {}
        
        if action == "answer":
            return {
                "needs_handoff": False,
                "needs_clarification": False,
                "needs_checkout": False,
                "message": None,  # Se generará respuesta con LLM
            }
        
        elif action == "handoff_human":
            return {
                "needs_handoff": True,
                "needs_clarification": False,
                "needs_checkout": False,
                "message": "Te comunico con un asesor humano.",
            }
        
        elif action == "start_checkout":
            return {
                "needs_handoff": False,
                "needs_clarification": False,
                "needs_checkout": True,
                "message": "Perfecto, te ayudo a comprar. ¿Qué cantidad necesitás?",
            }
        
        elif action == "ask_clarification":
            return {
                "needs_handoff": False,
                "needs_clarification": True,
                "needs_checkout": False,
                "message": "No estoy seguro de haber entendido completamente. ¿Podrías darme más detalles?",
            }
        
        # Fallback a answer
        return {
            "needs_handoff": False,
            "needs_clarification": False,
            "needs_checkout": False,
            "message": None,
        }

