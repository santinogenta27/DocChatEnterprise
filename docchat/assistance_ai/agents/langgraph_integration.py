"""Integración de LangGraph Agent con AssistanceAIAgent - IMPLEMENTACIÓN COMPLETA."""

from typing import Dict, Any, Optional, List
from langchain_core.language_models import BaseLanguageModel
from langchain_core.messages import HumanMessage, AIMessage

from ..graph.langgraph_integration import LangGraphIntegration as GraphLangGraphIntegration


class LangGraphIntegration:
    """Integración de LangGraph Agent con AssistanceAIAgent - Wrapper completo."""
    
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
        """Inicializa la integración LangGraph con todos los componentes."""
        # Usar la implementación completa del graph
        self.graph_integration = GraphLangGraphIntegration(
            llm=llm,
            tools=tools,
            rag_enabled=rag_enabled,
            rag_manager=rag_manager,
            chatbot_config_manager=chatbot_config_manager,
            session_manager=session_manager,
            sentiment_analyzer=sentiment_analyzer,
        )
    
    def process_message(
        self,
        session,
        user_message: str
    ) -> Dict[str, Any]:
        """Procesa un mensaje usando LangGraph Agent completo.
        
        Args:
            session: Sesión del cliente (CustomerSessionState)
            user_message: Mensaje del usuario
        
        Returns:
            Dict con la respuesta y metadata completa
        """
        # Delegar al graph_integration que tiene toda la lógica
        return self.graph_integration.process_message(session, user_message)

