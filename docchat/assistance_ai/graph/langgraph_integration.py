"""LangGraph Integration - Integración con AssistanceAIAgent existente."""

from typing import Dict, Any, Optional, List
from langchain_core.language_models import BaseLanguageModel
from langchain_core.messages import HumanMessage, AIMessage

from .langgraph_agent_wrapper import LangGraphAgentWrapper


class LangGraphIntegration:
    """Integración de LangGraph Agent con el sistema de Assistance AI."""
    
    def __init__(
        self,
        llm: BaseLanguageModel,
        tools: Dict[str, Any],
        rag_enabled: bool = True,
        rag_manager = None,
        chatbot_config_manager = None,
        session_manager = None,
        sentiment_analyzer = None,
    ):
        """Inicializa la integración de LangGraph.
        
        Args:
            llm: Modelo de lenguaje a usar
            tools: Diccionario de herramientas disponibles
            rag_enabled: Si RAG está habilitado
            rag_manager: Manager de RAG (opcional, se usará si está disponible)
            chatbot_config_manager: Manager de configuración (opcional)
            session_manager: Manager de sesiones (opcional)
            sentiment_analyzer: Analizador de sentimientos (opcional)
        """
        self.llm = llm
        self.tools = tools
        self.rag_enabled = rag_enabled
        self.rag_manager = rag_manager
        self.chatbot_config_manager = chatbot_config_manager
        self.session_manager = session_manager
        self.sentiment_analyzer = sentiment_analyzer
        
        # Crear wrapper de LangGraph
        self.langgraph_wrapper = LangGraphAgentWrapper(
            llm=llm,
            tools=tools,
            rag_enabled=rag_enabled
        )
    
    def process_message(
        self,
        session,
        user_message: str
    ) -> Dict[str, Any]:
        """Procesa un mensaje usando LangGraph Agent.
        
        Args:
            session: Sesión del cliente (CustomerSessionState)
            user_message: Mensaje del usuario
        
        Returns:
            Dict con la respuesta y metadata
        """
        # Extraer información de la sesión
        user_id = getattr(session, 'user_id', 'unknown')
        channel = getattr(session, 'channel', 'web')
        session_id = getattr(session, 'session_id', user_id)
        
        # Preparar metadata
        metadata = {}
        
        # Agregar información de sentimiento si está disponible
        if self.sentiment_analyzer and hasattr(session, 'last_messages'):
            try:
                sentiment = self.sentiment_analyzer.analyze(user_message)
                metadata['sentiment_score'] = getattr(sentiment, 'score', 0.5)
                metadata['sentiment_label'] = getattr(sentiment, 'label', 'neutral')
            except Exception as e:
                print(f"⚠️ Error analizando sentimiento: {e}")
        
        # Procesar mensaje con LangGraph
        result = self.langgraph_wrapper.process(
            user_message=user_message,
            user_id=user_id,
            channel=channel,
            session_id=session_id,
            metadata=metadata
        )
        
        # Actualizar sesión si está disponible
        if self.session_manager and session:
            try:
                # Actualizar estado de sesión
                session.intent = result.get('intent', getattr(session, 'intent', 'unknown'))
                session.confidence = result.get('confidence', getattr(session, 'confidence', 0.0))
                session.needs_handoff = result.get('needs_handoff', False)
                session.conversation_state = result.get('metadata', {}).get('conversation_state', 'completed')
                
                # Guardar mensajes en sesión
                if hasattr(session, 'add_message'):
                    session.add_message('user', user_message)
                    session.add_message('assistant', result.get('text', ''))
            except Exception as e:
                print(f"⚠️ Error actualizando sesión: {e}")
        
        return {
            "text": result.get("text", ""),
            "intent": result.get("intent", "pregunta_general"),
            "confidence": result.get("confidence", 0.0),
            "conversation_state": result.get("metadata", {}).get("conversation_state", "completed"),
            "needs_handoff": result.get("needs_handoff", False),
            "clarification_needed": False,  # Se maneja dentro del grafo
            "clarification_question": None,
            "decision_history": result.get("metadata", {}).get("decision_history", []),
            "tools_output": result.get("metadata", {}).get("tools_output", {}),
        }

