"""
ReactSalesAgent - Agente ReAct optimizado para widget web.

Implementa patrón ReAct completo con LangGraph:
- Think (razonamiento paso a paso)
- Act (uso de herramientas)
- Observe (procesamiento de resultados)
- Verify (verificación de respuestas)
- Close (cierre de ventas)

Optimizado específicamente para widget web con:
- Sales Closer Elite integrado
- RAG avanzado con índices separados
- Orquestador con decision layer
- Guardrails completos (Rule of Two, anti-injection)
- Flujo Siente→Piensa→Actúa→Aprende
"""

from __future__ import annotations

import json
import re
from typing import Dict, Any, Optional, List, TypedDict, Annotated, Sequence
from enum import Enum

from langchain_core.language_models import BaseLanguageModel
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool
from langchain_core.documents import Document
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages

from ...config import AppConfig
from ..state.customer_session import CustomerSessionManager, CustomerSessionState
from ..sentiment.sentiment_analyzer import SentimentAnalyzer
from ..tools.catalog_tool import CatalogTool
from ..tools.cart_tool import CartTool
from ..tools.payment_tool import PaymentTool
from ..tools.order_tool import OrderTool
from ..tools.support_tool import SupportTool
from ..rag.advanced_rag_manager import AdvancedRAGManager, IntentType
from ..rag.scope_checker import ScopeChecker
from ..rag.research_agent import ResearchAgent
from ..sales_closer_elite import SalesCloserElite
from ..orchestrator import Orchestrator
from ..guardrails import Guardrails

# Verification Agent eliminado: Ventas necesita velocidad, no verificación pesada tipo compliance


class SalesStage(str, Enum):
    """Etapas de venta según especificaciones."""
    INTEREST = "interest"
    CONSIDERATION = "consideration"
    READY = "ready"
    CLOSING = "closing"
    COMPLETED = "completed"


class SalesStrategy(str, Enum):
    """Estrategias de venta según especificaciones."""
    ANCHORING = "anchoring"
    ROI = "roi"
    SOCIAL_PROOF = "social_proof"
    URGENCY = "urgency"
    STANDARD = "standard"


class AgentState(TypedDict):
    """Estado del agente ReAct con Multi-Agent RAG completo."""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    session_id: str
    user_id: str
    sales_stage: str
    intent: str
    cart: Optional[Dict[str, Any]]
    payment_link: Optional[str]
    needs_handoff: bool
    context_retrieved: str
    tool_results: Dict[str, Any]
    verification_passed: bool
    closing_activated: bool
    # Campos para Multi-Agent RAG (sin verificación pesada - velocidad > compliance)
    relevance_label: str  # "CAN_ANSWER", "PARTIAL", "NO_MATCH"
    context_docs: List  # Documentos recuperados para Research Agent
    draft_answer: str  # Respuesta generada por Research Agent


class ReactSalesAgentConfig:
    """Configuración del ReactSalesAgent."""
    def __init__(
        self,
        brand_name: str = "Your Brand",
        language: str = "es",
        enable_sales_closer: bool = True,
        enable_rag_advanced: bool = True,
        enable_verification: bool = True,
    ):
        self.brand_name = brand_name
        self.language = language
        self.enable_sales_closer = enable_sales_closer
        self.enable_rag_advanced = enable_rag_advanced
        self.enable_verification = enable_verification


class ReactSalesAgent:
    """
    Agente ReAct optimizado para widget web con Sales Closer Elite.
    
    Implementa:
    - Patrón ReAct completo (Think → Act → Observe → Verify → Close)
    - Sales Closer Elite (detección de etapas, BANT, estrategias, objeciones)
    - RAG avanzado con índices separados
    - Orquestador con decision layer
    - Guardrails (Rule of Two, anti-injection)
    - Flujo Siente→Piensa→Actúa→Aprende
    """
    
    def __init__(
        self,
        llm: BaseLanguageModel,
        session_manager: CustomerSessionManager,
        sentiment_analyzer: SentimentAnalyzer,
        catalog_tool: CatalogTool,
        cart_tool: CartTool,
        payment_tool: PaymentTool,
        order_tool: OrderTool,
        support_tool: SupportTool,
        config: ReactSalesAgentConfig,
        app_config: Optional[AppConfig] = None,
    ):
        self.llm = llm
        self.session_manager = session_manager
        self.sentiment_analyzer = sentiment_analyzer
        self.catalog_tool = catalog_tool
        self.cart_tool = cart_tool
        self.payment_tool = payment_tool
        self.order_tool = order_tool
        self.support_tool = support_tool
        self.config = config
        self.app_config = app_config
        
        # Inicializar RAG avanzado si está habilitado
        self.advanced_rag: Optional[AdvancedRAGManager] = None
        if config.enable_rag_advanced:
            try:
                from langchain_openai import OpenAIEmbeddings
                import os
                api_key = os.getenv("OPENAI_API_KEY") or (app_config.openai_api_key if app_config else None)
                if api_key:
                    embeddings = OpenAIEmbeddings(
                        model="text-embedding-3-small",
                        openai_api_key=api_key
                    )
                    self.advanced_rag = AdvancedRAGManager(embeddings=embeddings)
                    print("✅ AdvancedRAGManager inicializado para ReactSalesAgent")
            except Exception as e:
                print(f"⚠️ Error inicializando AdvancedRAGManager: {e}")
        
        # Sales Closer Elite
        import os
        stripe_key = getattr(app_config, 'stripe_api_key', None) if app_config else None
        if not stripe_key:
            stripe_key = os.getenv('STRIPE_API_KEY')
        self.sales_closer = SalesCloserElite(stripe_api_key=stripe_key)
        
        # Orquestador
        self.orchestrator = Orchestrator()
        
        # Guardrails completos
        self.guardrails = Guardrails()
        
        # Links Manager - Para acceder a links configurados desde UI
        from ..config.links_manager import LinksManager
        self.links_manager = LinksManager()
        
        # Handoff Manager - Para transferir conversaciones a humanos
        from ..integrations.handoff_manager import HandoffManager
        self.handoff_manager = HandoffManager(enabled=False)  # Se configurará desde UI
        
        # Multi-Agent RAG: Scope Checker (Relevance Checker)
        self.scope_checker: Optional[ScopeChecker] = None
        if config.enable_rag_advanced and self.advanced_rag:
            try:
                # Crear retriever para Scope Checker usando AdvancedRAGManager
                from langchain_core.retrievers import BaseRetriever
                
                class AdvancedRAGRetriever(BaseRetriever):
                    """Wrapper de AdvancedRAGManager como BaseRetriever para ScopeChecker."""
                    def __init__(self, rag_manager: AdvancedRAGManager):
                        super().__init__()
                        self.rag_manager = rag_manager
                    
                    def _get_relevant_documents(self, query: str) -> List:
                        """Retorna documentos relevantes usando AdvancedRAGManager."""
                        result = self.rag_manager.retrieve_with_confidence(query)
                        return result.get("documents", [])
                    
                    def get_relevant_documents(self, query: str, k: int = 5) -> List:
                        """Interface compatible con ScopeChecker."""
                        docs = self._get_relevant_documents(query)
                        return docs[:k]
                
                rag_retriever = AdvancedRAGRetriever(self.advanced_rag) if self.advanced_rag else None
                self.scope_checker = ScopeChecker(llm=llm, retriever=rag_retriever)
                print("✅ ScopeChecker inicializado para Multi-Agent RAG")
            except Exception as e:
                print(f"⚠️ Error inicializando ScopeChecker: {e}")
        
        # Multi-Agent RAG: Research Agent
        self.research_agent: Optional[ResearchAgent] = None
        if config.enable_rag_advanced:
            try:
                self.research_agent = ResearchAgent(llm=llm)
                print("✅ ResearchAgent inicializado para Multi-Agent RAG")
            except Exception as e:
                print(f"⚠️ Error inicializando ResearchAgent: {e}")
        
        # Verification Agent eliminado: Ventas necesita velocidad, no verificación pesada
        
        # Construir grafo de LangGraph
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Construye el grafo de LangGraph con patrón ReAct + Multi-Agent RAG completo."""
        workflow = StateGraph(AgentState)
        
        # Nodos del flujo Multi-Agent RAG + ReAct
        # Si RAG avanzado está habilitado, agregar nodos de Multi-Agent RAG
        if self.config.enable_rag_advanced and self.scope_checker:
            workflow.add_node("check_relevance", self._check_relevance_node)
            workflow.add_node("research", self._research_node)
            # Punto de entrada: check_relevance
            workflow.set_entry_point("check_relevance")
            # Flujo RAG simplificado: check_relevance → research → think (velocidad > verificación)
            workflow.add_conditional_edges(
                "check_relevance",
                self._after_relevance_check,
                {
                    "relevant": "research",
                    "irrelevant": END,  # Si no es relevante (NO_MATCH), terminar
                }
            )
            workflow.add_edge("research", "think")  # Directo a think para velocidad
        else:
            # Si RAG avanzado no está habilitado, usar flujo normal
            workflow.set_entry_point("think")
        
        # Nodos del flujo ReAct (siempre presentes)
        workflow.add_node("think", self._think_node)
        workflow.add_node("act", self._act_node)
        workflow.add_node("observe", self._observe_node)
        workflow.add_node("verify", self._verify_node)
        workflow.add_node("close", self._close_node)
        workflow.add_node("handoff", self._handoff_node)  # Nodo para handoff a humanos
        
        # Flujo principal: think → act → observe
        workflow.add_edge("think", "act")
        workflow.add_edge("act", "observe")
        
        # Después de observar, decidir siguiente paso
        workflow.add_conditional_edges(
            "observe",
            self._should_continue,
            {
                "verify": "verify",
                "close": "close",
                "think": "think",  # Loop si necesita más razonamiento
                "handoff": "handoff",  # Handoff a humanos
                "end": END,
            }
        )
        
        # Después de handoff, terminar
        workflow.add_edge("handoff", END)
        
        # Después de verificar, decidir
        workflow.add_conditional_edges(
            "verify",
            self._after_verify,
            {
                "close": "close",
                "end": END,
            }
        )
        
        # Después de cerrar, terminar
        workflow.add_edge("close", END)
        
        return workflow.compile()
    
    def _check_relevance_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Nodo de Relevance Check (Scope Checker).
        
        Verifica si la pregunta está en scope antes de procesar.
        Retorna: "CAN_ANSWER", "PARTIAL", o "NO_MATCH"
        """
        if not self.scope_checker:
            return {"relevance_label": "CAN_ANSWER"}
        
        messages = state["messages"]
        last_message = messages[-1] if messages else None
        
        if not last_message or not isinstance(last_message, HumanMessage):
            return {"relevance_label": "CAN_ANSWER"}
        
        question = last_message.content
        
        try:
            relevance_label = self.scope_checker.check(question, k=5)
            print(f"🔍 Relevance Check: {relevance_label}")
            
            # Si es NO_MATCH, preparar mensaje de respuesta
            if relevance_label == "NO_MATCH":
                return {
                    "relevance_label": relevance_label,
                    "messages": [AIMessage(content="Lo siento, no tengo información suficiente en los documentos para responder esa pregunta. ¿Hay algo más en lo que pueda ayudarte?")],
                }
            
            # Si es PARTIAL o CAN_ANSWER, continuar
            return {"relevance_label": relevance_label}
            
        except Exception as e:
            print(f"⚠️ Error en Relevance Check: {e}")
            return {"relevance_label": "CAN_ANSWER"}  # Default: permitir continuar
    
    def _research_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Nodo de Research Agent.
        
        Genera respuesta inicial basada en documentos recuperados.
        """
        if not self.research_agent or not self.advanced_rag:
            return {}
        
        messages = state["messages"]
        last_message = messages[-1] if messages else None
        
        if not last_message or not isinstance(last_message, HumanMessage):
            return {}
        
        question = last_message.content
        
        try:
            # Recuperar documentos usando AdvancedRAGManager
            rag_result = self.advanced_rag.retrieve_with_confidence(question)
            documents = rag_result.get("documents", [])
            context = rag_result.get("context", "")
            
            if not documents:
                return {
                    "draft_answer": "No tengo información suficiente en los documentos para responder esta pregunta.",
                    "context_docs": [],
                    "context_retrieved": context,
                }
            
            # Generar respuesta usando Research Agent
            research_result = self.research_agent.generate_answer(
                question=question,
                documents=documents,
                max_context_length=3000
            )
            
            draft_answer = research_result.get("answer", "")
            context_used = research_result.get("context_used", context)
            
            print(f"📚 Research Agent: Respuesta generada (velocidad optimizada)")
            
            return {
                "draft_answer": draft_answer,
                "context_docs": documents,
                "context_retrieved": context_used,
            }
            
        except Exception as e:
            print(f"⚠️ Error en Research Agent: {e}")
            return {"draft_answer": "", "context_docs": []}
    
    def _after_relevance_check(self, state: AgentState) -> str:
        """Decide qué hacer después de Relevance Check."""
        relevance_label = state.get("relevance_label", "CAN_ANSWER")
        
        # Si hay mensaje de respuesta (NO_MATCH ya respondió), terminar
        messages = state.get("messages", [])
        if messages and any(isinstance(msg, AIMessage) for msg in messages):
            # Ya hay respuesta de NO_MATCH, terminar workflow
            return "irrelevant"
        
        if relevance_label == "NO_MATCH":
            return "irrelevant"
        
        # Si es CAN_ANSWER o PARTIAL, continuar con Research
        return "relevant"
    
    # Verification Agent y Self-Correction eliminados: Ventas necesita velocidad, no verificación pesada
    def _think_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Nodo de razonamiento (Think).
        
        Implementa:
        - Detección de intención
        - Detección de etapa de venta
        - Recuperación de contexto (RAG)
        - Análisis de sentimiento
        """
        messages = state["messages"]
        last_message = messages[-1] if messages else None
        
        if not last_message or not isinstance(last_message, HumanMessage):
            return {}
        
        user_query = last_message.content
        
        # Guardrails: Verificar si el query es seguro
        validation = self.guardrails.validate_input(
            query=user_query,
            action=None,
            session_id=state["session_id"],
        )
        if not validation["is_safe"]:
            return {
                "messages": [AIMessage(content=validation["message"] or "Lo siento, no puedo procesar esa solicitud.")],
                "needs_handoff": validation["blocked_reason"] == "rule_of_two",
            }
        
        # Obtener sesión
        session = self.session_manager.get_or_create(
            session_id=state["session_id"],
            profile=None
        )
        
        # Detección de intención (usando RAG avanzado si está disponible)
        intent = "general"
        if self.advanced_rag:
            detected_intent = self.advanced_rag.detect_intent(user_query)
            intent = detected_intent.value
        
        # Detección de etapa de venta
        sales_stage = self._detect_sales_stage(user_query)
        
        # Recuperar contexto (RAG avanzado)
        # Si ya hay contexto de Research Agent, usarlo (viene de research_node)
        context = state.get("context_retrieved", "")
        draft_answer = state.get("draft_answer", "")
        
        # Si hay draft_answer del Research Agent, usarlo como contexto adicional
        if draft_answer and draft_answer not in context:
            context = f"{context}\n\n{draft_answer}".strip() if context else draft_answer
        
        # Si no hay contexto y RAG avanzado está disponible, recuperar normalmente
        if not context and self.advanced_rag:
            context_result = self.advanced_rag.retrieve_with_confidence(user_query)
            context = context_result.get("context", "")
        
        # Usar orquestador para decidir acción
        action = self.orchestrator.decide_action(user_query, context)
        action_result = self.orchestrator.handle_action(
            action=action,
            query=user_query,
            context=context,
            session_data={"session_id": state["session_id"], "user_id": state["user_id"]}
        )
        
        # Si necesita handoff humano, retornar inmediatamente
        if action_result.get("needs_handoff"):
            return {
                "messages": [AIMessage(content=action_result["message"])],
                "needs_handoff": True,
            }
        
        # Si necesita clarificación, retornar con mensaje
        if action_result.get("needs_clarification"):
            return {
                "messages": [AIMessage(content=action_result["message"])],
                "context_retrieved": context,
            }
        
        # Si es checkout, preparar para iniciar proceso
        if action_result.get("needs_checkout"):
            # Log inicio de checkout
            self._log_event("checkout_started", state["session_id"])
            # Se manejará en el nodo act
        
        # Análisis de sentimiento
        sentiment_result = self.sentiment_analyzer.analyze(user_query, session)
        
        # Construir prompt de razonamiento
        think_prompt = self._build_think_prompt(
            user_query=user_query,
            intent=intent,
            sales_stage=sales_stage,
            context=context,
            sentiment=sentiment_result,
            session=session,
        )
        
        # Invocar LLM para razonamiento
        response = self.llm.invoke([
            SystemMessage(content=think_prompt),
            HumanMessage(content=user_query),
        ])
        
        # Extraer decisión del LLM
        content = response.content if hasattr(response, 'content') else str(response)
        decision = self._parse_think_decision(content)
        
        return {
            "messages": [response],
            "intent": intent,
            "sales_stage": sales_stage,
            "context_retrieved": context,
            "tool_results": decision,
        }
    
    def _act_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Nodo de acción (Act).
        
        Ejecuta herramientas según la decisión del nodo think.
        """
        tool_results = state.get("tool_results", {})
        session_id = state["session_id"]
        messages = state["messages"]
        
        # Extraer última decisión del LLM
        last_ai_message = None
        for msg in reversed(messages):
            if isinstance(msg, AIMessage):
                last_ai_message = msg
                break
        
        if not last_ai_message:
            return {}
        
        # Parsear tool calls del mensaje
        tool_calls = getattr(last_ai_message, 'tool_calls', [])
        if not tool_calls:
            # Intentar extraer de contenido si no hay tool_calls
            tool_calls = self._extract_tool_calls_from_content(last_ai_message.content)
        
        executed_tools = {}
        
        # Ejecutar herramientas
        for tool_call in tool_calls:
            tool_name = tool_call.get("name")
            tool_args = tool_call.get("args", {})
            
            try:
                if tool_name == "search_products":
                    query = tool_args.get("query", "")
                    result = self.catalog_tool.search_products(query=query, limit=5)
                    executed_tools["products"] = result
                
                elif tool_name == "add_to_cart":
                    product_id = tool_args.get("product_id")
                    quantity = tool_args.get("quantity", 1)
                    cart = self.cart_tool.add_item(session_id, product_id, quantity)
                    # Log evento de carrito
                    self._log_event("cart_add", session_id, {
                        "product_id": product_id,
                        "quantity": quantity
                    })
                    executed_tools["cart"] = cart.to_dict() if hasattr(cart, "to_dict") else cart.__dict__
                
                elif tool_name == "create_payment":
                    cart = self.cart_tool.get_cart(session_id)
                    # Usar Sales Closer Elite para crear payment link con Stripe
                    cart_dict = cart.to_dict() if hasattr(cart, "to_dict") else cart.__dict__
                    payment_result = self._request_payment(session_id, cart_dict)
                    if payment_result.get("payment_link"):
                        # Sales Closer Elite creó payment link exitosamente
                        executed_tools["payment"] = payment_result
                        executed_tools["payment_link"] = payment_result["payment_link"]
                        # Log evento
                        self._log_event("payment_initiated", session_id, {"total": payment_result.get("total", 0)})
                    else:
                        # Fallback al payment_tool original si Sales Closer Elite falla
                        try:
                            payment_result = self.payment_tool.create_payment_for_cart(
                                session_id=session_id,
                                cart=cart,
                            )
                            executed_tools["payment"] = payment_result.__dict__ if hasattr(payment_result, '__dict__') else payment_result
                            if hasattr(payment_result, "payment_link"):
                                executed_tools["payment_link"] = payment_result.payment_link
                            elif isinstance(payment_result, dict) and "payment_link" in payment_result:
                                executed_tools["payment_link"] = payment_result["payment_link"]
                        except Exception as e:
                            print(f"⚠️ Error creando payment con payment_tool: {e}")
                            executed_tools["payment_error"] = str(e)
                
                elif tool_name == "create_order":
                    cart = self.cart_tool.get_cart(session_id)
                    cart_dict = cart.to_dict() if hasattr(cart, "to_dict") else cart.__dict__
                    payment_info = executed_tools.get("payment", {})
                    order = self.order_tool.create_order(
                        session_id=session_id,
                        cart_snapshot=cart_dict,
                        payment_info=payment_info,
                    )
                    executed_tools["order"] = order
                
                elif tool_name == "create_ticket":
                    ticket = self.support_tool.create_ticket(
                        session_id=session_id,
                        subject=tool_args.get("subject", "Soporte"),
                        description=tool_args.get("description", ""),
                        priority=tool_args.get("priority", "normal"),
                    )
                    executed_tools["ticket"] = ticket
                
            except Exception as e:
                print(f"⚠️ Error ejecutando herramienta {tool_name}: {e}")
                executed_tools[f"{tool_name}_error"] = str(e)
        
        # Crear mensajes de herramientas
        tool_messages = []
        for tool_name, result in executed_tools.items():
            tool_messages.append(
                ToolMessage(
                    content=json.dumps(result, default=str),
                    name=tool_name,
                )
            )
        
        return {
            "messages": tool_messages,
            "tool_results": executed_tools,
        }
    
    def _observe_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Nodo de observación (Observe).
        
        Procesa resultados de herramientas y decide siguiente paso.
        """
        messages = state["messages"]
        tool_results = state.get("tool_results", {})
        
        # Construir contexto de observación
        observation_context = self._build_observation_context(tool_results)
        
        # Invocar LLM para procesar observaciones
        observation_prompt = f"""
Analiza los resultados de las herramientas ejecutadas y decide el siguiente paso.

**Resultados de herramientas:**
{observation_context}

**Instrucciones:**
1. Si hay productos encontrados, prepara una respuesta que los presente de forma persuasiva.
2. Si hay un carrito actualizado, menciona los productos agregados.
3. Si hay un payment_link, inclúyelo en la respuesta.
4. Si hay errores, explica qué salió mal.
5. Decide si necesitas más información o si puedes generar la respuesta final.

Responde en JSON:
{{
    "ready_to_respond": true/false,
    "needs_more_info": true/false,
    "response_draft": "borrador de respuesta si está listo",
    "next_action": "respond" | "verify" | "close" | "think_more"
}}
"""
        
        response = self.llm.invoke([
            SystemMessage(content=observation_prompt),
            HumanMessage(content="Procesa las observaciones y decide el siguiente paso."),
        ])
        
        content = response.content if hasattr(response, 'content') else str(response)
        decision = self._parse_json_decision(content)
        
        return {
            "messages": [response],
            "verification_passed": decision.get("ready_to_respond", False),
        }
    
    def _verify_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Nodo de verificación (Verify).
        
        Verifica que la respuesta sea correcta y esté soportada por el contexto.
        """
        if not self.config.enable_verification:
            return {"verification_passed": True}
        
        messages = state["messages"]
        context = state.get("context_retrieved", "")
        
        # Extraer respuesta del último mensaje
        last_message = messages[-1] if messages else None
        if not last_message:
            return {"verification_passed": False}
        
        response_text = last_message.content if hasattr(last_message, 'content') else str(last_message)
        
        # Verificar contra contexto
        verify_prompt = f"""
Verifica que la siguiente respuesta esté soportada por el contexto proporcionado.

**Contexto:**
{context[:2000]}

**Respuesta a verificar:**
{response_text[:1000]}

Responde en JSON:
{{
    "supported": true/false,
    "unsupported_claims": ["lista de afirmaciones no soportadas"],
    "contradictions": ["lista de contradicciones"],
    "relevant": true/false
}}
"""
        
        response = self.llm.invoke([
            SystemMessage(content=verify_prompt),
            HumanMessage(content="Verifica la respuesta."),
        ])
        
        content = response.content if hasattr(response, 'content') else str(response)
        verification = self._parse_json_decision(content)
        
        is_supported = verification.get("supported", False) and verification.get("relevant", False)
        
        return {
            "messages": [response],
            "verification_passed": is_supported,
        }
    
    def _close_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Nodo de cierre (Close).
        
        Genera respuesta final optimizada para widget con Sales Closer Elite.
        """
        messages = state["messages"]
        sales_stage = state.get("sales_stage", SalesStage.INTEREST.value)
        intent = state.get("intent", "general")
        tool_results = state.get("tool_results", {})
        context = state.get("context_retrieved", "")
        
        # Aplicar Sales Closer Elite si está habilitado
        closing_strategy = None
        closing_message = None
        if self.config.enable_sales_closer:
            closing_strategy = self._select_sales_strategy(sales_stage, intent, tool_results)
            # Si está en etapa READY o CLOSING, usar mensaje de cierre directo
            if sales_stage in [SalesStage.READY.value, SalesStage.CLOSING.value]:
                closing_message = self._close_sale()
            closing_strategy = self._select_sales_strategy(sales_stage, intent, tool_results)
        
        # Construir prompt de cierre
        close_prompt = self._build_close_prompt(
            sales_stage=sales_stage,
            intent=intent,
            tool_results=tool_results,
            context=context,
            closing_strategy=closing_strategy,
        )
        
        # Generar respuesta final
        response = self.llm.invoke([
            SystemMessage(content=close_prompt),
            HumanMessage(content="Genera la respuesta final optimizada para el widget."),
        ])
        
        final_text = response.content if hasattr(response, 'content') else str(response)
        
        # Extraer payment_link si existe
        payment_link = tool_results.get("payment_link") or tool_results.get("payment", {}).get("payment_link")
        
        return {
            "messages": [AIMessage(content=final_text)],
            "closing_activated": closing_strategy is not None,
        }
    
    def _should_continue(self, state: AgentState) -> str:
        """
        Decide el siguiente paso después de observar.
        
        Returns:
            "verify", "close", "think", "handoff", o "end"
        """
        messages = state["messages"]
        verification_passed = state.get("verification_passed", False)
        sales_stage = state.get("sales_stage", SalesStage.INTEREST.value)
        
        # Verificar si necesita handoff automático
        if self.handoff_manager.enabled:
            from ..integrations.handoff_manager import HandoffTrigger
            
            # Obtener métricas del estado
            context_retrieved = state.get("context_retrieved", "")
            confidence = len(context_retrieved) / 2000.0 if context_retrieved else 0.0  # Proxy de confianza
            
            # Verificar triggers automáticos
            if self.handoff_manager.should_handoff(
                HandoffTrigger.AUTO_LOW_CONFIDENCE,
                confidence=confidence,
            ):
                return "handoff"
        
        # Si la verificación está habilitada y no pasó, verificar
        if self.config.enable_verification and not verification_passed:
            return "verify"
        
        # Si está en etapa de cierre, ir directo a close
        if sales_stage in [SalesStage.READY.value, SalesStage.CLOSING.value]:
            return "close"
        
        # Si está listo para responder, verificar o cerrar
        if verification_passed:
            if sales_stage in [SalesStage.READY.value, SalesStage.CLOSING.value]:
                return "close"
            return "end"
        
        # Si necesita más razonamiento, volver a think
        return "think"
    
    def _after_verify(self, state: AgentState) -> str:
        """Decide qué hacer después de verificar."""
        verification_passed = state.get("verification_passed", False)
        sales_stage = state.get("sales_stage", SalesStage.INTEREST.value)
        
        if verification_passed:
            if sales_stage in [SalesStage.READY.value, SalesStage.CLOSING.value]:
                return "close"
            return "end"
        else:
            # Si no pasó verificación, volver a pensar
            return "think"
    
    # === Métodos auxiliares ===
    
    def _detect_sales_stage(self, query: str) -> str:
        """Detecta etapa de venta usando Sales Closer Elite."""
        return self.sales_closer.detect_sales_stage(query)
        
        return SalesStage.INTEREST.value
    
    def _select_sales_strategy(
        self,
        sales_stage: str,
        intent: str,
        tool_results: Dict[str, Any],
    ) -> Optional[SalesStrategy]:
        """Selecciona estrategia de venta usando Sales Closer Elite."""
        query = f"{sales_stage} {intent}"
        strategy = self.sales_closer.sales_strategy(query)
        return SalesStrategy(strategy)
    
    def _handle_objection(self, objection: str) -> str:
        """Maneja objeciones usando Sales Closer Elite."""
        return self.sales_closer.handle_objection(objection)
    
    def _is_safe_query(self, query: str) -> bool:
        """Verifica si el query es seguro usando Guardrails."""
        validation = self.guardrails.validate_input(query)
        return validation["is_safe"]
    

    def _close_sale(self) -> str:
        """Cierre directo usando Sales Closer Elite."""
        return self.sales_closer.close_sale()
    
    def _request_payment(self, session_id: str, cart: Dict[str, Any]) -> Dict[str, Any]:
        """Solicita pago usando Sales Closer Elite."""
        return self.sales_closer.request_payment(session_id, cart)
    
    def _log_event(self, event_type: str, session_id: str, metadata: Optional[Dict[str, Any]] = None):
        """Registra evento para métricas."""
        self.sales_closer.log_event(event_type, session_id, metadata)
    
    def _format_conversation_history(self, messages: Sequence[BaseMessage]) -> str:
        """Formatea historial de conversación para handoff."""
        history_parts = []
        for msg in messages[-10:]:  # Últimos 10 mensajes
            if isinstance(msg, HumanMessage):
                history_parts.append(f"Usuario: {msg.content}")
            elif isinstance(msg, AIMessage):
                history_parts.append(f"Agente: {msg.content}")
        return "\n".join(history_parts)
    
    def update_handoff_config(self, config: Dict[str, Any]):
        """Actualiza configuración de handoff desde UI."""
        handoff_config = {
            "handoff_enabled": config.get("handoff_enabled", False),
            "handoff_provider": config.get("handoff_provider", "none"),
            "handoff_api_key": config.get("handoff_zendesk_subdomain") or config.get("handoff_whatsapp_token"),
            "handoff_api_token": config.get("handoff_zendesk_token"),
            "handoff_queue": config.get("handoff_zendesk_queue"),
            "handoff_department": config.get("handoff_zendesk_queue"),
            "handoff_email": config.get("handoff_email"),
            "handoff_triggers": config.get("handoff_triggers", {
                "manual": True,
                "auto_low_confidence": False,
                "auto_strong_objection": False,
                "auto_frustration": False,
            }),
        }
        self.handoff_manager.update_config(handoff_config)

    def _build_think_prompt(
        self,
        user_query: str,
        intent: str,
        sales_stage: str,
        context: str,
        sentiment: Any,
        session: CustomerSessionState,
    ) -> str:
        """Construye prompt de razonamiento."""
        
        # Obtener links relevantes para la consulta
        relevant_links_list = self.links_manager.get_relevant_links_for_query(user_query)
        links_context = ""
        if relevant_links_list:
            links_context = f"\n\n**Links relevantes disponibles (usa cuando sea apropiado):**\n" + "\n".join(relevant_links_list)
        
        prompt = f"""
Eres un asistente virtual 24/7 para {self.config.brand_name}.

**Contexto recuperado (RAG):**
{context[:1500] if context else "No hay contexto disponible"}
{links_context}

**Etapa de venta detectada:** {sales_stage}
**Intención detectada:** {intent}

**Instrucciones:**
1. Analiza el mensaje del usuario paso a paso.
2. Decide qué herramientas necesitas usar.
3. Si es sobre productos, usa search_products.
4. Si quiere comprar, usa add_to_cart y luego create_payment.
5. Si necesita soporte, usa create_ticket.

Responde en formato JSON con tu decisión:
{{
    "thought": "tu razonamiento paso a paso",
    "tools_needed": ["lista de herramientas"],
    "tool_calls": [
        {{
            "name": "nombre_herramienta",
            "args": {{"arg1": "valor1"}}
        }}
    ]
}}
"""
        return prompt
    
    def _build_observation_context(self, tool_results: Dict[str, Any]) -> str:
        """Construye contexto de observación desde resultados de herramientas."""
        context_parts = []
        
        if "products" in tool_results:
            products = tool_results["products"]
            if hasattr(products, 'products'):
                products = products.products
            context_parts.append(f"Productos encontrados: {len(products) if isinstance(products, list) else 'N/A'}")
        
        if "cart" in tool_results:
            cart = tool_results["cart"]
            items = cart.get("items", []) if isinstance(cart, dict) else []
            context_parts.append(f"Carrito actualizado: {len(items)} items")
        
        if "payment_link" in tool_results:
            context_parts.append(f"Payment link generado: {tool_results['payment_link']}")
        
        if "order" in tool_results:
            context_parts.append("Orden creada exitosamente")
        
        return "\n".join(context_parts) if context_parts else "No hay resultados de herramientas"
    
    def _build_close_prompt(
        self,
        sales_stage: str,
        intent: str,
        tool_results: Dict[str, Any],
        context: str,
        closing_strategy: Optional[SalesStrategy],
    ) -> str:
        """Construye prompt de cierre optimizado para widget."""
        prompt = f"""
Eres un asistente virtual de ventas para {self.config.brand_name}.

**Etapa de venta:** {sales_stage}
**Intención:** {intent}
**Estrategia de cierre:** {closing_strategy.value if closing_strategy else "standard"}

**Resultados de herramientas:**
{json.dumps(tool_results, default=str)[:2000]}

**Instrucciones para respuesta final:**
1. Sé directo y conciso (máximo 300 caracteres para widget).
2. Si hay productos, preséntalos con nombres y precios específicos.
3. Si hay payment_link, inclúyelo claramente.
4. Si estás en etapa READY o CLOSING, incluye un CTA claro.
5. Usa la estrategia de cierre {closing_strategy.value if closing_strategy else "standard"}.
6. Sé persuasivo pero ético.

Genera la respuesta final optimizada para widget web.
"""
        return prompt
    
    def _parse_think_decision(self, content: str) -> Dict[str, Any]:
        """Parsea decisión del nodo think."""
        try:
            match = re.search(r"\{[\s\S]*\}", content)
            if match:
                return json.loads(match.group().replace("'", '"'))
        except:
            pass
        return {"tools_needed": [], "tool_calls": []}
    
    def _parse_json_decision(self, content: str) -> Dict[str, Any]:
        """Parsea decisión en formato JSON."""
        try:
            match = re.search(r"\{[\s\S]*\}", content)
            if match:
                return json.loads(match.group().replace("'", '"'))
        except:
            pass
        return {}
    
    def _extract_tool_calls_from_content(self, content: str) -> List[Dict[str, Any]]:
        """Extrae tool calls del contenido si no están en formato estándar."""
        try:
            decision = self._parse_think_decision(content)
            return decision.get("tool_calls", [])
        except:
            return []
    
    # === Método principal de procesamiento ===
    
    def process(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Procesa un mensaje usando el flujo ReAct completo.
        
        Args:
            payload: Dict con session_id, user_id, message, channel
            
        Returns:
            Dict con text, intent, sales_stage, cart, payment_link, etc.
        """
        session_id = payload.get("session_id", "default_session")
        user_id = payload.get("user_id", "anonymous")
        message = payload.get("message", "")
        
        if not message:
            return {
                "text": "Por favor, envía un mensaje.",
                "error": True,
            }
        
        # Estado inicial
        initial_state: AgentState = {
            "messages": [HumanMessage(content=message)],
            "session_id": session_id,
            "user_id": user_id,
            "sales_stage": SalesStage.INTEREST.value,
            "intent": "general",
            "cart": None,
            "payment_link": None,
            "needs_handoff": False,
            "context_retrieved": "",
            "tool_results": {},
            "verification_passed": False,
            "closing_activated": False,
            # Campos para Multi-Agent RAG (sin verificación pesada)
            "relevance_label": "",
            "context_docs": [],
            "draft_answer": "",
        }
        
        # Ejecutar grafo
        try:
            final_state = self.graph.invoke(initial_state)
        except Exception as e:
            print(f"❌ Error ejecutando grafo ReAct: {e}")
            import traceback
            traceback.print_exc()
            return {
                "text": "Lo siento, hubo un error procesando tu mensaje. Por favor, intenta de nuevo.",
                "error": True,
            }
        
        # Extraer respuesta final
        messages = final_state.get("messages", [])
        final_message = None
        for msg in reversed(messages):
            if isinstance(msg, AIMessage):
                final_message = msg
                break
        
        # Obtener valores del estado final
        sales_stage = final_state.get("sales_stage", SalesStage.INTEREST.value)
        intent = final_state.get("intent", "general")
        tool_results = final_state.get("tool_results", {})
        
        # Extraer texto de respuesta
        if not final_message:
            # Si no hay mensaje final pero hay draft_answer del Research Agent, usarlo
            draft_answer = final_state.get("draft_answer", "")
            if draft_answer:
                response_text = draft_answer
            else:
                return {
                    "text": "No pude generar una respuesta. Por favor, intenta de nuevo.",
                    "error": True,
                }
        else:
            response_text = final_message.content if hasattr(final_message, 'content') else str(final_message)
        
        # Log conversión si está en etapa de cierre
        if sales_stage in [SalesStage.READY.value, SalesStage.CLOSING.value, SalesStage.COMPLETED.value]:
            cart = tool_results.get("cart")
            total = 0
            if cart and isinstance(cart, dict):
                total = sum(item.get("price", 0) * item.get("quantity", 1) for item in cart.get("items", []))
            self._log_event("conversion", session_id, {
                "sales_stage": sales_stage,
                "total": total,
                "intent": intent
            })
        
        # Construir respuesta final
        result = {
            "text": response_text,  # Incluir texto de respuesta
            "sales_stage": sales_stage,
            "intent": intent,
            "needs_handoff": final_state.get("needs_handoff", False),
            "cart": final_state.get("cart"),
            "payment_link": final_state.get("payment_link"),
            "closing_activated": final_state.get("closing_activated", False),
        }
        
        # Agregar tool_results si existen
        if tool_results:
            result["tools"] = tool_results
        
        return result
