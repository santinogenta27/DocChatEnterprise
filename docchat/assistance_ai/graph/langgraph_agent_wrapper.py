"""Wrapper para integrar LangGraph Agent con AssistanceAIAgent existente."""

from typing import Dict, Any, Optional
from langchain_core.language_models import BaseLanguageModel

from .agent_graph import CustomerServiceAgentGraph
from .rag_retriever import RAGRetriever


class LangGraphAgentWrapper:
    """Wrapper que integra el agente LangGraph con el sistema existente."""
    
    def __init__(
        self,
        llm: BaseLanguageModel,
        tools: Optional[Dict[str, Any]] = None,
        rag_enabled: bool = True
    ):
        self.llm = llm
        self.tools = tools or {}
        
        # Inicializar RAG retriever si está habilitado
        self.rag_retriever = None
        if rag_enabled:
            try:
                self.rag_retriever = RAGRetriever()
            except Exception as e:
                print(f"⚠️ Error inicializando RAG Retriever: {e}")
        
        # Crear el grafo
        self.agent_graph = CustomerServiceAgentGraph(
            llm=llm,
            tools=self.tools,
            rag_retriever=self.rag_retriever
        )
    
    def process(
        self,
        user_message: str,
        user_id: str,
        channel: str = "web",
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Procesa un mensaje usando el grafo LangGraph.
        
        Returns:
            {
                "text": str,
                "intent": str,
                "confidence": float,
                "needs_handoff": bool,
                "escalation_reason": Optional[str],
                "metadata": Dict
            }
        """
        # Estado inicial
        initial_state = {
            "user_id": user_id,
            "channel": channel,
            "user_message": user_message,
            "metadata": metadata or {},
            "messages": []  # Se creará HumanMessage en invoke
        }
        
        # Invocar el grafo
        try:
            final_state = self.agent_graph.invoke(initial_state)
            
            # Extraer resultado
            response_text = final_state.get("response_text", "")
            intent = final_state.get("intent", "pregunta_general")
            confidence = final_state.get("confidence", 0.0)
            escalation_flag = final_state.get("escalation_flag", False)
            escalation_reason = final_state.get("escalation_reason")
            
            return {
                "text": response_text,
                "intent": intent,
                "confidence": confidence,
                "needs_handoff": escalation_flag,
                "escalation_reason": escalation_reason,
                "metadata": {
                    **final_state.get("metadata", {}),
                    "decision_history": final_state.get("decision_history", []),
                    "retrieval_context_count": len(final_state.get("retrieval_context", [])),
                    "conversation_state": final_state.get("conversation_state", "completed")
                }
            }
        except Exception as e:
            print(f"❌ Error procesando mensaje con LangGraph: {e}")
            import traceback
            traceback.print_exc()
            
            # Fallback
            return {
                "text": "Lo siento, estoy teniendo problemas para procesar tu mensaje. Por favor, inténtalo de nuevo.",
                "intent": "pregunta_general",
                "confidence": 0.0,
                "needs_handoff": True,
                "escalation_reason": f"Error técnico: {str(e)}",
                "metadata": {}
            }

