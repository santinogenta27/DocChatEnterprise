"""Memory Manager - Gestión de memoria conversacional optimizada."""

from typing import List, Dict, Any, Optional
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from datetime import datetime, timedelta


class MemoryManager:
    """Gestiona memoria conversacional - solo lo necesario."""
    
    MAX_HISTORY_LENGTH = 20  # Máximo de mensajes en memoria
    SUMMARY_THRESHOLD = 15  # Si hay más mensajes, resumir
    
    def __init__(self):
        self.conversation_summaries = {}  # session_id -> summary
    
    def get_relevant_history(
        self,
        messages: List[BaseMessage],
        session_id: str,
        max_messages: int = 10
    ) -> List[BaseMessage]:
        """Obtiene historial relevante, resumiendo si es necesario."""
        if len(messages) <= max_messages:
            return messages[-max_messages:]
        
        # Si hay muchos mensajes, resumir los antiguos
        if len(messages) > self.SUMMARY_THRESHOLD:
            # Mantener últimos N mensajes + resumen de los anteriores
            recent_messages = messages[-max_messages:]
            old_messages = messages[:-max_messages]
            
            # Si ya hay un resumen, usarlo
            if session_id in self.conversation_summaries:
                summary_msg = HumanMessage(
                    content=f"[Resumen de conversación anterior]: {self.conversation_summaries[session_id]}"
                )
                return [summary_msg] + recent_messages
            else:
                # Crear resumen básico
                summary = self._create_basic_summary(old_messages)
                self.conversation_summaries[session_id] = summary
                summary_msg = HumanMessage(
                    content=f"[Resumen de conversación anterior]: {summary}"
                )
                return [summary_msg] + recent_messages
        
        return messages[-max_messages:]
    
    def _create_basic_summary(self, messages: List[BaseMessage]) -> str:
        """Crea un resumen básico de mensajes antiguos."""
        if not messages:
            return ""
        
        # Extraer temas principales
        topics = []
        for msg in messages[:10]:  # Primeros 10 para resumen
            if hasattr(msg, 'content'):
                content = msg.content[:100]  # Primeros 100 caracteres
                topics.append(content)
        
        return f"Conversación previa sobre: {', '.join(topics[:3])}..."
    
    def update_summary(
        self,
        session_id: str,
        new_messages: List[BaseMessage],
        llm = None
    ):
        """Actualiza el resumen de la conversación usando LLM si está disponible."""
        if not llm:
            return
        
        try:
            # Obtener mensajes recientes para resumir
            messages_to_summarize = new_messages[-10:] if len(new_messages) > 10 else new_messages
            
            # Construir prompt para resumen
            conversation_text = "\n".join([
                f"{'Usuario' if isinstance(msg, HumanMessage) else 'Asistente'}: {msg.content[:200]}"
                for msg in messages_to_summarize
                if hasattr(msg, 'content')
            ])
            
            summary_prompt = f"""Resume esta conversación en 2-3 oraciones, enfocándote en:
- El tema principal
- Información clave mencionada
- Estado actual de la conversación

Conversación:
{conversation_text}

Resumen:"""
            
            from langchain_core.messages import SystemMessage, HumanMessage
            response = llm.invoke([
                SystemMessage(content="Eres un asistente que resume conversaciones de forma concisa."),
                HumanMessage(content=summary_prompt)
            ])
            
            summary = response.content if hasattr(response, 'content') else str(response)
            self.conversation_summaries[session_id] = summary
            
        except Exception as e:
            print(f"⚠️ Error actualizando resumen: {e}")

