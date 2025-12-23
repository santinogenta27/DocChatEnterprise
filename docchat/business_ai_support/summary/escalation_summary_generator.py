"""Escalation Summary Generator - Generates structured summaries for human handoff."""

from __future__ import annotations

from typing import Dict, Any, Optional, List
from langchain_core.language_models import BaseLanguageModel
from langchain_core.messages import SystemMessage, HumanMessage


class EscalationSummaryGenerator:
    """Generates structured summaries for escalations."""
    
    def __init__(self, llm: BaseLanguageModel):
        """Initialize EscalationSummaryGenerator.
        
        Args:
            llm: Language model for generating summaries
        """
        self.llm = llm
    
    def generate_summary(
        self,
        conversation_history: List[Dict[str, str]],
        ticket_data: Dict[str, Any],
        sentiment: Optional[str] = None,
        frustration_score: Optional[float] = None,
        actions_taken: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Generate structured summary for escalation.
        
        Args:
            conversation_history: List of messages [{"role": "user/assistant", "content": "..."}]
            ticket_data: Ticket data (subject, description, status, etc.)
            sentiment: Detected sentiment (positive, neutral, negative)
            frustration_score: Frustration score (0-10)
            actions_taken: List of actions already taken by the AI
            
        Returns:
            Dict with structured summary:
            {
                "issue": str,
                "sentiment": str,
                "urgency": str,
                "actions_taken": List[str],
                "pending_actions": List[str],
                "additional_context": str
            }
        """
        # Format conversation history
        conversation_text = self._format_conversation(conversation_history)
        
        # Build prompt
        prompt = self._build_summary_prompt(
            conversation_text=conversation_text,
            ticket_data=ticket_data,
            sentiment=sentiment,
            frustration_score=frustration_score,
            actions_taken=actions_taken or []
        )
        
        try:
            # Generate summary using LLM
            messages = [
                SystemMessage(content="Eres un asistente experto en generar resúmenes estructurados de conversaciones de soporte al cliente para escalación a humanos. Genera respuestas en formato JSON válido."),
                HumanMessage(content=prompt)
            ]
            
            response = self.llm.invoke(messages)
            summary_text = response.content if hasattr(response, 'content') else str(response)
            
            # Parse JSON response
            import json
            import re
            
            # Extract JSON from response (in case LLM adds extra text)
            json_match = re.search(r'\{.*\}', summary_text, re.DOTALL)
            if json_match:
                summary_json = json.loads(json_match.group())
            else:
                # Fallback: try to parse entire response
                summary_json = json.loads(summary_text)
            
            # Validate and structure summary
            summary = {
                "issue": summary_json.get("issue", ticket_data.get("subject", "Consulta del cliente")),
                "sentiment": summary_json.get("sentiment", sentiment or "neutral"),
                "urgency": summary_json.get("urgency", self._calculate_urgency(frustration_score)),
                "actions_taken": summary_json.get("actions_taken", actions_taken or []),
                "pending_actions": summary_json.get("pending_actions", []),
                "additional_context": summary_json.get("additional_context", "")
            }
            
            return summary
            
        except Exception as e:
            print(f"⚠️ Error generando resumen estructurado: {e}")
            import traceback
            traceback.print_exc()
            
            # Fallback: generate simple summary
            return self._generate_fallback_summary(
                conversation_history,
                ticket_data,
                sentiment,
                frustration_score,
                actions_taken
            )
    
    def _build_summary_prompt(
        self,
        conversation_text: str,
        ticket_data: Dict[str, Any],
        sentiment: Optional[str],
        frustration_score: Optional[float],
        actions_taken: List[str]
    ) -> str:
        """Build prompt for summary generation."""
        prompt = f"""
Genera un resumen estructurado de esta conversación de soporte al cliente para escalación a un agente humano.

**HISTORIAL DE CONVERSACIÓN:**
{conversation_text}

**INFORMACIÓN DEL TICKET:**
- Asunto: {ticket_data.get('subject', 'N/A')}
- Descripción: {ticket_data.get('description', 'N/A')}
- Estado: {ticket_data.get('status', 'N/A')}
- Prioridad: {ticket_data.get('priority', 'normal')}

**INFORMACIÓN ADICIONAL:**
- Sentimiento detectado: {sentiment or 'No detectado'}
- Score de frustración: {frustration_score or 'N/A'} (0-10)
- Acciones ya tomadas por el AI: {', '.join(actions_taken) if actions_taken else 'Ninguna'}

**INSTRUCCIONES:**
Genera un resumen estructurado en formato JSON con los siguientes campos:

{{
    "issue": "Descripción clara y concisa del problema o consulta del cliente (1-2 párrafos)",
    "sentiment": "Sentimiento del cliente (positive, neutral, negative, frustrated)",
    "urgency": "Urgencia del caso (low, medium, high, critical)",
    "actions_taken": ["Lista de acciones que el AI ya realizó", "ej: Consultó base de conocimiento", "ej: Creó ticket interno"],
    "pending_actions": ["Lista de acciones pendientes que requiere el humano", "ej: Validar política de devolución", "ej: Contactar al cliente"],
    "additional_context": "Cualquier información adicional relevante para el agente humano"
}}

**IMPORTANTE:**
- Sé específico y accionable en "pending_actions"
- Evalúa la urgencia basándote en el score de frustración y el tipo de problema
- El resumen debe ayudar al agente humano a entender rápidamente el caso

Genera SOLO el JSON, sin texto adicional.
"""
        return prompt.strip()
    
    def _format_conversation(self, conversation_history: List[Dict[str, str]]) -> str:
        """Format conversation history for prompt."""
        if not conversation_history:
            return "No hay historial de conversación disponible."
        
        formatted = []
        for msg in conversation_history[-10:]:  # Last 10 messages
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            role_label = "Cliente" if role == "user" else "Asistente"
            formatted.append(f"{role_label}: {content}")
        
        return "\n".join(formatted)
    
    def _calculate_urgency(self, frustration_score: Optional[float]) -> str:
        """Calculate urgency based on frustration score."""
        if frustration_score is None:
            return "medium"
        
        if frustration_score >= 9.0:
            return "critical"
        elif frustration_score >= 7.0:
            return "high"
        elif frustration_score >= 4.0:
            return "medium"
        else:
            return "low"
    
    def _generate_fallback_summary(
        self,
        conversation_history: List[Dict[str, str]],
        ticket_data: Dict[str, Any],
        sentiment: Optional[str],
        frustration_score: Optional[float],
        actions_taken: Optional[List[str]]
    ) -> Dict[str, Any]:
        """Generate fallback summary if LLM fails."""
        # Extract last user message as issue
        issue = ticket_data.get("description", "Consulta del cliente")
        if conversation_history:
            for msg in reversed(conversation_history):
                if msg.get("role") == "user":
                    issue = msg.get("content", issue)
                    break
        
        return {
            "issue": issue[:500],  # Limit length
            "sentiment": sentiment or "neutral",
            "urgency": self._calculate_urgency(frustration_score),
            "actions_taken": actions_taken or ["Ticket creado"],
            "pending_actions": ["Revisar caso", "Contactar al cliente"],
            "additional_context": f"Ticket ID: {ticket_data.get('ticket_id', 'N/A')}"
        }

