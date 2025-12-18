"""
Support Agent - LangGraph-based autonomous resolution agent
"""
from typing import Dict, Any, List, Optional, TypedDict
import logging
import os

try:
    from langchain_openai import ChatOpenAI
    from langchain_community.chat_models import ChatGrok
    from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
    from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
    from langgraph.graph import StateGraph, END
    from langgraph.prebuilt import ToolNode
    from langgraph.checkpoint.memory import MemorySaver
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

try:
    import gradio as gr
    GRADIO_AVAILABLE = True
except ImportError:
    GRADIO_AVAILABLE = False

from ..rag.knowledge_base import KnowledgeBase
from ..tools.refund_tool import RefundTool
from ..tools.ticket_tool import TicketTool
from ..tools.tracking_tool import TrackingTool
from ..tools.kb_search_tool import KBSearchTool
from ..utils.logging import setup_logger

logger = setup_logger("customer_support.agent")


class AgentState(TypedDict):
    """State for LangGraph agent"""
    messages: List
    query: str
    context: str
    tools_used: List[str]
    resolution_status: str
    needs_escalation: bool


class SupportAgent:
    """Autonomous Resolution Agent for Customer Service"""
    
    def __init__(
        self,
        grok_api_key: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        provider: str = "grok",
        kb_path: str = "./knowledge_base",
        storage_path: str = "./data"
    ):
        """
        Initialize Support Agent
        
        Args:
            grok_api_key: Grok API key (xAI)
            openai_api_key: OpenAI API key (fallback)
            provider: LLM provider (grok, openai)
            kb_path: Path to knowledge base
            storage_path: Storage path
        """
        if not LANGCHAIN_AVAILABLE:
            raise ImportError("LangChain is required. Install with: pip install langchain langgraph")
        
        self.provider = provider
        self.storage_path = storage_path
        
        # Initialize LLM
        self.llm = self._initialize_llm(grok_api_key, openai_api_key, provider)
        
        # Initialize Knowledge Base
        logger.info("📚 Inicializando base de conocimiento...")
        self.kb = KnowledgeBase(kb_path=kb_path)
        
        # Initialize Tools
        logger.info("🔧 Inicializando herramientas...")
        self.refund_tool = RefundTool()
        self.ticket_tool = TicketTool()
        self.tracking_tool = TrackingTool()
        self.kb_search_tool = KBSearchTool(self.kb)
        
        # Get LangChain tools
        self.tools = [
            self.refund_tool.get_langchain_tool(),
            self.ticket_tool.get_langchain_tool(),
            self.tracking_tool.get_langchain_tool(),
            self.kb_search_tool.get_langchain_tool()
        ]
        
        # Bind tools to LLM
        self.llm_with_tools = self.llm.bind_tools(self.tools)
        
        # Create agent graph
        self.agent = self._create_agent_graph()
        
        logger.info("✅ Support Agent inicializado")
    
    def _initialize_llm(self, grok_api_key: Optional[str], openai_api_key: Optional[str], provider: str):
        """Initialize LLM based on provider"""
        try:
            if provider == "grok" and grok_api_key:
                logger.info("🤖 Inicializando Grok (xAI)...")
                # Note: Grok integration may vary, using OpenAI as fallback structure
                # In production, use: ChatGrok(api_key=grok_api_key)
                if openai_api_key:
                    logger.info("   Usando OpenAI como fallback para Grok")
                    return ChatOpenAI(model="gpt-4o-mini", api_key=openai_api_key, temperature=0.7)
                else:
                    raise ValueError("Grok API key or OpenAI fallback required")
            elif provider == "openai" and openai_api_key:
                logger.info("🤖 Inicializando OpenAI...")
                return ChatOpenAI(model="gpt-4o-mini", api_key=openai_api_key, temperature=0.7)
            else:
                # Fallback to open models
                logger.warning("⚠️ No API keys provided, using fallback")
                raise ValueError("API key required for LLM")
        except Exception as e:
            logger.error(f"Error inicializando LLM: {e}")
            raise
    
    def _create_agent_graph(self):
        """Create LangGraph agent workflow"""
        logger.info("🔄 Creando grafo de agente LangGraph...")
        
        # Define system prompt
        system_prompt = """You are a helpful and empathetic customer service agent. Your goal is to resolve customer issues autonomously using the available tools.

Guidelines:
1. Always be empathetic and professional
2. Use Chain-of-Thought reasoning: Think step-by-step before acting
3. Search the knowledge base FIRST to understand policies and procedures
4. Use tools autonomously to resolve issues (refunds, tracking, tickets)
5. Only escalate to humans if the issue is complex or requires policy exceptions
6. Provide clear, actionable responses
7. Confirm actions taken with the customer

Available tools:
- search_knowledge_base_tool: Search policies, FAQs, and procedures
- track_order_tool: Track order status
- process_refund_tool: Process refunds
- create_ticket_tool: Create support tickets for escalation

Workflow:
1. Understand the customer query
2. Search knowledge base for relevant information
3. Plan actions needed
4. Execute tools as needed
5. Respond naturally and confirm actions
6. Escalate only if necessary"""
        
        # Define nodes
        def should_continue(state: AgentState) -> str:
            """Determine if agent should continue or end"""
            messages = state["messages"]
            last_message = messages[-1]
            
            # If there are tool calls, continue to tools
            if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
                return "tools"
            
            # Otherwise, end
            return "end"
        
        def agent_node(state: AgentState) -> AgentState:
            """Agent reasoning node"""
            messages = state["messages"]
            
            # Add system message if first message
            if len(messages) == 1:
                messages = [SystemMessage(content=system_prompt)] + messages
            
            # Get response from LLM
            response = self.llm_with_tools.invoke(messages)
            
            return {"messages": [response]}
        
        def tools_node(state: AgentState) -> AgentState:
            """Tools execution node"""
            messages = state["messages"]
            last_message = messages[-1]
            
            # Execute tools
            tool_node = ToolNode(self.tools)
            tool_responses = tool_node.invoke({"messages": [last_message]})
            
            return {"messages": tool_responses["messages"]}
        
        # Create graph
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("agent", agent_node)
        workflow.add_node("tools", tools_node)
        
        # Set entry point
        workflow.set_entry_point("agent")
        
        # Add conditional edges
        workflow.add_conditional_edges(
            "agent",
            should_continue,
            {
                "tools": "tools",
                "end": END
            }
        )
        
        workflow.add_edge("tools", "agent")
        
        # Compile with memory
        memory = MemorySaver()
        app = workflow.compile(checkpointer=memory)
        
        logger.info("✅ Grafo de agente creado")
        
        return app
    
    def process_query(
        self,
        query: str,
        session_id: Optional[str] = None,
        customer_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a customer query
        
        Args:
            query: Customer query
            session_id: Session ID for conversation history
            customer_info: Optional customer information
            
        Returns:
            Agent response with actions taken
        """
        logger.info(f"💬 Procesando consulta: '{query[:50]}...'")
        
        # Prepare initial state
        config = {"configurable": {"thread_id": session_id or "default"}}
        
        # Add customer context if provided
        system_context = ""
        if customer_info:
            system_context = f"\nCustomer Info: {customer_info}\n"
        
        initial_message = HumanMessage(content=system_context + query)
        
        # Invoke agent
        try:
            result = self.agent.invoke(
                {"messages": [initial_message]},
                config=config
            )
            
            # Get final response
            final_message = result["messages"][-1]
            response_text = final_message.content if hasattr(final_message, 'content') else str(final_message)
            
            # Extract tools used
            tools_used = []
            for msg in result["messages"]:
                if hasattr(msg, 'tool_calls') and msg.tool_calls:
                    tools_used.extend([tc.get('name', 'unknown') for tc in msg.tool_calls])
            
            logger.info(f"✅ Consulta procesada. Tools usados: {tools_used}")
            
            return {
                "response": response_text,
                "tools_used": tools_used,
                "needs_escalation": "escalate" in response_text.lower() or len(tools_used) == 0,
                "session_id": session_id or "default"
            }
            
        except Exception as e:
            logger.error(f"Error procesando consulta: {e}")
            return {
                "response": "I apologize, but I encountered an error. Please contact human support.",
                "error": str(e),
                "needs_escalation": True
            }
    
    def get_gradio_interface(self):
        """Get Gradio interface for embedding"""
        if not GRADIO_AVAILABLE:
            raise ImportError("Gradio is required. Install with: pip install gradio")
        
        logger.info("🎨 Creando interfaz Gradio...")
        
        def chat_fn(message, history):
            """Chat function for Gradio"""
            response = self.process_query(message)
            return response["response"]
        
        # Create Gradio interface
        interface = gr.ChatInterface(
            fn=chat_fn,
            title="Customer Support Assistant",
            description="I'm here to help! Ask me about orders, refunds, shipping, or any questions.",
            examples=[
                "Where is my order #12345?",
                "I want a refund for order #12345",
                "My package is late, what can you do?",
                "What is your refund policy?"
            ],
            theme=gr.themes.Soft(),
            share=False  # Set to True for public link
        )
        
        logger.info("✅ Interfaz Gradio creada")
        
        return interface


