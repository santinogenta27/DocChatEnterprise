"""
STAR AGENT - Agente ReAct Optimizado con Sales Closer Elite
Implementa arquitectura ReAct con LangGraph para el widget web optimizado
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, TypedDict, Annotated, Sequence, Literal
from enum import Enum
from pathlib import Path

from langchain_core.language_models import BaseLanguageModel
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage, SystemMessage
from langchain_core.tools import tool
try:
    from langgraph.graph import StateGraph, END
    from langgraph.graph.message import add_messages
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    print("⚠️ LangGraph no disponible. Instala con: pip install langgraph")

from ...config import AppConfig
from ..state.customer_session import CustomerSessionManager, CustomerSessionState, SentimentLabel
from ..sentiment.sentiment_analyzer import SentimentAnalyzer
from ..tools.catalog_tool import CatalogTool
from ..tools.cart_tool import CartTool
from ..tools.payment_tool import PaymentTool
from ..tools.order_tool import OrderTool
from ..tools.support_tool import SupportTool


class SalesStage(str, Enum):
    """Etapas del proceso de venta"""
    INTEREST = "interest"  # Interés inicial
    CONSIDERATION = "consideration"  # Considerando compra
    READY = "ready"  # Listo para comprar
    CLOSING = "closing"  # En proceso de cierre
    COMPLETED = "completed"  # Venta completada


class SalesStrategy(str, Enum):
    """Estrategias de venta"""
    ANCHORING = "anchoring"  # Anclar precio/valor
    ROI = "roi"  # Retorno de inversión
    SOCIAL_PROOF = "social_proof"  # Prueba social
    URGENCY = "urgency"  # Urgencia/escasez
    STANDARD = "standard"  # Estrategia estándar


class IntentType(str, Enum):
    """Tipos de intención detectada"""
    PRODUCTS = "productos"
    POLICIES = "políticas"
    REVIEWS = "reviews"
    SUPPORT = "soporte"
    CHECKOUT = "checkout"
    GENERAL = "general"


class AgentState(TypedDict):
    """Estado compartido del agente ReAct"""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    session_id: str
    user_id: str
    channel: str
    sales_stage: SalesStage
    sales_strategy: SalesStrategy
    intent: IntentType
    context_retrieved: str
    draft_answer: str
    verification_result: Dict[str, Any]
    needs_handoff: bool
    cart_snapshot: Dict[str, Any]
    conversion_tracked: bool
    next_action: str


@dataclass
class ReactSalesAgentConfig:
    """Configuración del agente ReAct optimizado"""
    brand_name: str = "Your Brand"
    language: str = "es"
    enable_sales_closer: bool = True
    enable_rag_advanced: bool = True
    enable_verification: bool = True
    max_iterations: int = 5
    temperature: float = 0.3


class ReactSalesAgent:
    """
    Agente ReAct optimizado con Sales Closer Elite para widget web.
    
    Implementa:
    - Arquitectura ReAct con LangGraph (Think → Act → Observe → Think)
    - Sales Closer Elite con detección de etapas
    - RAG avanzado con índices separados
    - Orquestador con decision layer
    - Guardrails anti-injection
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
        
        # Guardrails anti-injection
        self.BLOCKED_PATTERNS = [
            "ignora instrucciones",
            "system prompt",
            "actúa como",
            "forget previous",
            "you are now",
        ]
        
        # Construir grafo de LangGraph
        if LANGGRAPH_AVAILABLE:
            self.graph = self._build_graph()
        else:
            self.graph = None
            print("⚠️ LangGraph no disponible. El agente ReAct no funcionará correctamente.")
        
        # Inicializar RAG avanzado si está habilitado
        self.rag_stores = {}
        if config.enable_rag_advanced:
            self._initialize_advanced_rag()
    
    def _build_graph(self):
        """Construye el grafo de LangGraph para ReAct"""
        if not LANGGRAPH_AVAILABLE:
            return None
        
        workflow = StateGraph(AgentState)
        
        # Nodos del workflow
        workflow.add_node("think", self._think_node)
        workflow.add_node("act", self._act_node)
        workflow.add_node("observe", self._observe_node)
        workflow.add_node("verify", self._verify_node)
        workflow.add_node("close_sale", self._close_sale_node)
        
        # Punto de entrada
        workflow.set_entry_point("think")
        
        # Edges condicionales
        workflow.add_conditional_edges(
            "think",
            self._decide_after_think,
            {
                "act": "act",
                "close": "close_sale",
                "end": END,
            }
        )
        
        workflow.add_edge("act", "observe")
        
        workflow.add_conditional_edges(
            "observe",
            self._decide_after_observe,
            {
                "think": "think",
                "verify": "verify",
                "end": END,
            }
        )
        
        workflow.add_conditional_edges(
            "verify",
            self._decide_after_verify,
            {
                "think": "think",  # Re-research si falla verificación
                "close": "close_sale",
                "end": END,
            }
        )
        
        workflow.add_edge("close_sale", END)
        
        return workflow.compile()
    
    def _think_node(self, state: AgentState) -> AgentState:
        """Nodo de razonamiento - analiza la situación y decide qué hacer"""
        messages = state["messages"]
        last_message = messages[-1] if messages else None
        
        if not last_message or not isinstance(last_message, HumanMessage):
            return state
        
        query = last_message.content
        
        # Guardrails: verificar si el query es seguro
        if not self._is_safe_query(query):
            state["messages"] = add_messages(
                state["messages"],
                [AIMessage(content="Lo siento, no puedo procesar esa solicitud.")]
            )
            state["next_action"] = "end"
            return state
        
        # Detectar intención
        intent = self._detect_intent(query)
        state["intent"] = intent
        
        # Detectar etapa de venta
        sales_stage = self._detect_sales_stage(query, state)
        state["sales_stage"] = sales_stage
        
        # Seleccionar estrategia de venta
        strategy = self._select_sales_strategy(query, sales_stage)
        state["sales_strategy"] = strategy
        
        # Generar pensamiento del agente
        system_prompt = self._build_think_prompt(state)
        
        thought_messages = [
            SystemMessage(content=system_prompt),
            *messages[-3:]  # Últimos 3 mensajes para contexto
        ]
        
        try:
            thought_response = self.llm.invoke(thought_messages)
            thought_content = thought_response.content if hasattr(thought_response, 'content') else str(thought_response)
            
            # Extraer acción del pensamiento
            if "necesito buscar" in thought_content.lower() or "necesito consultar" in thought_content.lower():
                state["next_action"] = "act"
            elif "listo para comprar" in thought_content.lower() or "procesar pago" in thought_content.lower():
                state["next_action"] = "close"
            else:
                state["next_action"] = "end"
            
            # Agregar pensamiento al estado (para debugging)
            state["draft_answer"] = thought_content
            
        except Exception as e:
            print(f"⚠️ Error en think node: {e}")
            state["next_action"] = "end"
        
        return state
    
    def _act_node(self, state: AgentState) -> AgentState:
        """Nodo de acción - ejecuta herramientas según la intención"""
        intent = state.get("intent", IntentType.GENERAL)
        query = state["messages"][-1].content if state["messages"] else ""
        
        # Recuperar contexto según intención
        context = self._retrieve_context(query, intent)
        state["context_retrieved"] = context
        
        # Ejecutar herramientas según intención
        tool_results = []
        
        if intent == IntentType.PRODUCTS:
            # Buscar productos
            try:
                search_result = self.catalog_tool.search_products(query, limit=5)
                tool_results.append(f"Productos encontrados: {len(search_result.products)}")
                state["context_retrieved"] += f"\n\nProductos disponibles:\n{json.dumps([p.model_dump() for p in search_result.products[:3]], indent=2)}"
            except Exception as e:
                tool_results.append(f"Error buscando productos: {e}")
        
        elif intent == IntentType.CHECKOUT:
            # Obtener carrito actual
            try:
                cart = self.cart_tool.get_cart(state["session_id"])
                state["cart_snapshot"] = {
                    "items": [{"id": item.product_id, "quantity": item.quantity} for item in cart.items],
                    "total": cart.total
                }
                tool_results.append(f"Carrito con {len(cart.items)} items, total: ${cart.total:.2f}")
            except Exception as e:
                tool_results.append(f"Error obteniendo carrito: {e}")
        
        elif intent == IntentType.SUPPORT:
            # Crear ticket si es necesario
            if "problema" in query.lower() or "error" in query.lower():
                try:
                    ticket = self.support_tool.create_ticket(
                        state["session_id"],
                        subject="Consulta desde widget",
                        description=query
                    )
                    tool_results.append(f"Ticket creado: {ticket['ticket_id']}")
                except Exception as e:
                    tool_results.append(f"Error creando ticket: {e}")
        
        # Agregar resultados de herramientas como ToolMessage
        tool_message = ToolMessage(
            content="\n".join(tool_results) if tool_results else "No se ejecutaron herramientas",
            name="action_tools"
        )
        state["messages"] = add_messages(state["messages"], [tool_message])
        
        return state
    
    def _observe_node(self, state: AgentState) -> AgentState:
        """Nodo de observación - procesa resultados de herramientas"""
        # El contexto ya está en state["context_retrieved"]
        # Generar respuesta inicial basada en contexto
        context = state.get("context_retrieved", "")
        query = state["messages"][-1].content if state["messages"] else ""
        
        if not context:
            state["next_action"] = "end"
            return state
        
        # Generar respuesta usando LLM
        prompt = f"""Basado en el siguiente contexto, responde la pregunta del usuario de manera clara y útil.

Contexto:
{context}

Pregunta: {query}

Responde de manera natural y conversacional."""
        
        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            draft_answer = response.content if hasattr(response, 'content') else str(response)
            state["draft_answer"] = draft_answer
            
            # Decidir siguiente paso
            if self.config.enable_verification:
                state["next_action"] = "verify"
            else:
                state["next_action"] = "end"
                
        except Exception as e:
            print(f"⚠️ Error generando respuesta: {e}")
            state["draft_answer"] = "Lo siento, no pude generar una respuesta adecuada."
            state["next_action"] = "end"
        
        return state
    
    def _verify_node(self, state: AgentState) -> AgentState:
        """Nodo de verificación - valida la respuesta contra el contexto"""
        draft_answer = state.get("draft_answer", "")
        context = state.get("context_retrieved", "")
        
        if not draft_answer or not context:
            state["next_action"] = "end"
            return state
        
        # Verificar si la respuesta está soportada por el contexto
        verification_prompt = f"""Verifica si la siguiente respuesta está soportada por el contexto proporcionado.

Contexto:
{context}

Respuesta a verificar:
{draft_answer}

Responde SOLO con "YES" si la respuesta está completamente soportada, o "NO" si hay información no soportada."""
        
        try:
            verification_response = self.llm.invoke([HumanMessage(content=verification_prompt)])
            verification_text = verification_response.content if hasattr(verification_response, 'content') else str(verification_response)
            
            is_supported = "YES" in verification_text.upper()
            
            state["verification_result"] = {
                "supported": is_supported,
                "verification_text": verification_text
            }
            
            if is_supported:
                # Si está soportada y estamos en etapa de cierre, ir a close_sale
                if state.get("sales_stage") == SalesStage.READY:
                    state["next_action"] = "close"
                else:
                    state["next_action"] = "end"
            else:
                # Re-research si no está soportada
                state["next_action"] = "think"
                
        except Exception as e:
            print(f"⚠️ Error en verificación: {e}")
            state["verification_result"] = {"supported": True, "error": str(e)}
            state["next_action"] = "end"
        
        return state
    
    def _close_sale_node(self, state: AgentState) -> AgentState:
        """Nodo de cierre de venta - aplica técnicas de cierre y procesa pago"""
        sales_stage = state.get("sales_stage", SalesStage.INTEREST)
        strategy = state.get("sales_strategy", SalesStrategy.STANDARD)
        cart_snapshot = state.get("cart_snapshot", {})
        
        # Aplicar técnicas de cierre según estrategia
        closing_message = self._apply_closing_techniques(state, strategy)
        
        # Si hay carrito y está listo, procesar pago
        if cart_snapshot and sales_stage == SalesStage.READY:
            try:
                # Obtener carrito completo
                cart = self.cart_tool.get_cart(state["session_id"])
                
                if cart.items:
                    # Crear link de pago
                    payment_result = self.payment_tool.create_payment_for_cart(
                        state["session_id"],
                        cart,
                        payment_method="stripe"
                    )
                    
                    closing_message += f"\n\n💳 **Listo para procesar tu compra:**\n"
                    closing_message += f"Total: ${cart.total:.2f}\n"
                    if hasattr(payment_result, 'payment_link'):
                        closing_message += f"[Pagar ahora]({payment_result.payment_link})"
                    
                    # Trackear conversión
                    if not state.get("conversion_tracked"):
                        self._track_conversion(state, "payment_initiated")
                        state["conversion_tracked"] = True
            except Exception as e:
                print(f"⚠️ Error procesando pago: {e}")
                closing_message += "\n\n⚠️ Hubo un error procesando el pago. Por favor, intenta de nuevo."
        
        # Agregar mensaje de cierre
        state["messages"] = add_messages(
            state["messages"],
            [AIMessage(content=closing_message)]
        )
        
        state["next_action"] = "end"
        return state
    
    def _decide_after_think(self, state: AgentState) -> str:
        """Decide qué hacer después del nodo think"""
        return state.get("next_action", "end")
    
    def _decide_after_observe(self, state: AgentState) -> str:
        """Decide qué hacer después del nodo observe"""
        return state.get("next_action", "end")
    
    def _decide_after_verify(self, state: AgentState) -> str:
        """Decide qué hacer después del nodo verify"""
        return state.get("next_action", "end")
    
    # === Métodos auxiliares ===
    
    def _is_safe_query(self, query: str) -> bool:
        """Verifica si el query es seguro (guardrails anti-injection)"""
        query_lower = query.lower()
        return not any(pattern in query_lower for pattern in self.BLOCKED_PATTERNS)
    
    def _detect_intent(self, query: str) -> IntentType:
        """Detecta la intención del usuario"""
        q = query.lower()
        
        if any(x in q for x in ["precio", "cuesta", "producto", "comprar", "tengo"]):
            return IntentType.PRODUCTS
        elif any(x in q for x in ["envío", "entrega", "devolución", "garantía"]):
            return IntentType.POLICIES
        elif any(x in q for x in ["opinión", "reseña", "review", "calificación"]):
            return IntentType.REVIEWS
        elif any(x in q for x in ["problema", "error", "soporte", "ayuda", "ticket"]):
            return IntentType.SUPPORT
        elif any(x in q for x in ["pagar", "checkout", "carrito", "comprar ahora"]):
            return IntentType.CHECKOUT
        else:
            return IntentType.GENERAL
    
    def _detect_sales_stage(self, query: str, state: AgentState) -> SalesStage:
        """Detecta la etapa de venta actual"""
        q = query.lower()
        
        if any(x in q for x in ["precio", "cuánto cuesta", "comprar", "pagar"]):
            return SalesStage.READY
        elif any(x in q for x in ["envío", "funciona", "garantía", "vale la pena"]):
            return SalesStage.CONSIDERATION
        else:
            # Verificar etapa previa en sesión
            session = self.session_manager.get(state["session_id"])
            if session and hasattr(session, 'sales_stage'):
                return session.sales_stage
            return SalesStage.INTEREST
    
    def _select_sales_strategy(self, query: str, stage: SalesStage) -> SalesStrategy:
        """Selecciona estrategia de venta según query y etapa"""
        q = query.lower()
        
        if "precio" in q or "caro" in q:
            return SalesStrategy.ANCHORING
        elif "vale la pena" in q or "beneficio" in q:
            return SalesStrategy.ROI
        elif "opinión" in q or "otros" in q:
            return SalesStrategy.SOCIAL_PROOF
        elif "después" in q or "luego" in q:
            return SalesStrategy.URGENCY
        else:
            return SalesStrategy.STANDARD
    
    def _retrieve_context(self, query: str, intent: IntentType) -> str:
        """Recupera contexto según intención usando RAG avanzado"""
        if not self.config.enable_rag_advanced:
            return ""
        
        # Usar índice específico según intención
        store_key = intent.value
        if store_key not in self.rag_stores:
            return ""
        
        # TODO: Implementar búsqueda en vector store específico
        # Por ahora retornar contexto vacío
        return ""
    
    def _initialize_advanced_rag(self):
        """Inicializa RAG avanzado con índices separados"""
        # TODO: Implementar inicialización de múltiples vector stores
        # Por ahora placeholder
        pass
    
    def _build_think_prompt(self, state: AgentState) -> str:
        """Construye el prompt para el nodo think"""
        sales_stage = state.get("sales_stage", SalesStage.INTEREST)
        strategy = state.get("sales_strategy", SalesStrategy.STANDARD)
        
        prompt = f"""Eres un asistente virtual 24/7 para {self.config.brand_name}.

Estás en la etapa de venta: {sales_stage.value}
Estrategia actual: {strategy.value}

Piensa paso a paso:
1. ¿Qué información necesitas para responder?
2. ¿Qué herramientas debes usar?
3. ¿Está el usuario listo para comprar?

Responde de manera natural y conversacional."""
        
        return prompt
    
    def _apply_closing_techniques(self, state: AgentState, strategy: SalesStrategy) -> str:
        """Aplica técnicas de cierre según estrategia"""
        sales_stage = state.get("sales_stage", SalesStage.INTEREST)
        
        if strategy == SalesStrategy.ANCHORING:
            return "Entiendo tu preocupación por el precio. Este producto incluye [beneficios] que lo hacen una excelente inversión."
        elif strategy == SalesStrategy.ROI:
            return "Este producto te ahorrará tiempo y dinero a largo plazo. ¿Qué tendría que pasar para que lo veas útil ahora?"
        elif strategy == SalesStrategy.SOCIAL_PROOF:
            return "Muchos clientes están satisfechos con este producto. ¿Querés que te muestre algunas opiniones?"
        elif strategy == SalesStrategy.URGENCY:
            return "Tenemos disponibilidad limitada. ¿Querés que lo procesemos ahora y te lo envío enseguida?"
        else:
            return "¿Querés que te ayude a completar tu compra?"
    
    def _track_conversion(self, state: AgentState, event_type: str):
        """Trackea eventos de conversión"""
        # TODO: Implementar tracking de conversiones
        pass
    
    def process(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Procesa un mensaje usando el workflow ReAct"""
        session_id = payload.get("session_id", "default")
        user_id = payload.get("user_id", "anonymous")
        channel = payload.get("channel", "web")
        message = payload.get("message", "")
        
        # Estado inicial
        initial_state: AgentState = {
            "messages": [HumanMessage(content=message)],
            "session_id": session_id,
            "user_id": user_id,
            "channel": channel,
            "sales_stage": SalesStage.INTEREST,
            "sales_strategy": SalesStrategy.STANDARD,
            "intent": IntentType.GENERAL,
            "context_retrieved": "",
            "draft_answer": "",
            "verification_result": {},
            "needs_handoff": False,
            "cart_snapshot": {},
            "conversion_tracked": False,
            "next_action": "think",
        }
        
        # Ejecutar workflow
        if not self.graph:
            return {
                "text": "Lo siento, el sistema de procesamiento avanzado no está disponible. Por favor, inténtalo más tarde.",
                "error": "LangGraph no disponible"
            }
        
        try:
            final_state = self.graph.invoke(initial_state)
            
            # Extraer respuesta final
            messages = final_state["messages"]
            last_ai_message = None
            for msg in reversed(messages):
                if isinstance(msg, AIMessage) and msg.content:
                    last_ai_message = msg.content
                    break
            
            response_text = last_ai_message or final_state.get("draft_answer", "Lo siento, no pude generar una respuesta.")
            
            return {
                "text": response_text,
                "intent": final_state.get("intent", IntentType.GENERAL).value,
                "sales_stage": final_state.get("sales_stage", SalesStage.INTEREST).value,
                "needs_handoff": final_state.get("needs_handoff", False),
                "cart": final_state.get("cart_snapshot", {}),
            }
            
        except Exception as e:
            print(f"❌ Error en workflow ReAct: {e}")
            import traceback
            traceback.print_exc()
            return {
                "text": "Lo siento, hubo un error procesando tu mensaje. Por favor, inténtalo de nuevo.",
                "error": str(e)
            }

