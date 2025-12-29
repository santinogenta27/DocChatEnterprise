"""State definition para LangGraph - Customer Service Agent Enterprise."""

from typing import TypedDict, Optional, List, Dict, Any, Annotated
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class CustomerServiceState(TypedDict):
    """State mínimo tipado para el agente de customer service."""
    
    # Identificación
    user_id: str
    channel: str  # web, whatsapp, instagram, messenger
    
    # Intención y confianza
    intent: Optional[str]  # pregunta_general, consulta_productos, soporte_tecnico, tracking_envio, devolucion_reclamo, compra_asistencia, conversacion_sentimiento_negativo, escalamiento_humano
    confidence: float  # 0.0 - 1.0
    
    # Estado de conversación
    conversation_state: str  # init, asking_clarification, processing, completed, escalated
    messages: Annotated[List[BaseMessage], add_messages]  # Historial de mensajes
    
    # Contexto RAG
    retrieval_context: List[Dict[str, Any]]  # Documentos recuperados
    retrieval_confidence: float  # Confianza en el retrieval
    
    # Escalamiento
    escalation_flag: bool
    escalation_reason: Optional[str]
    
    # Decision log (para debugging y auditoría)
    decision_history: List[Dict[str, Any]]  # Registro de decisiones tomadas
    
    # Respuesta final
    response_text: Optional[str]
    
    # Metadata adicional
    metadata: Dict[str, Any]  # Cualquier dato adicional necesario
    
    # Flags adicionales
    clarification_needed: Optional[bool]
    clarification_question: Optional[str]

