"""
STAR AGENT - Agente ReAct Optimizado con Sales Closer Elite
Implementa arquitectura ReAct con LangGraph para el widget web optimizado
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, TypedDict, Annotated, Sequence, Literal
from datetime import datetime
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
from ..rag.advanced_rag_manager import AdvancedRAGManager, IntentType as RAGIntentType
from ..intelligence.lead_qualification import LeadQualifier, BANTQualification
from ..learning.continuous_learning import ContinuousLearningSystem


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
    bant_qualification: Optional[Any]  # BANTQualification
    next_bant_question: Optional[str]


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
        
        # Guardrails anti-injection (Rule of Two)
        self.BLOCKED_PATTERNS = [
            "ignora instrucciones",
            "system prompt",
            "actúa como",
            "forget previous",
            "you are now",
            "override",
            "bypass",
            "ignore all",
        ]
        
        # Calificador de Leads BANT
        self.lead_qualifier = LeadQualifier()
        
        # Sistema de aprendizaje continuo
        self.learning_system = ContinuousLearningSystem()
        
        # Construir grafo de LangGraph
        if LANGGRAPH_AVAILABLE:
            self.graph = self._build_graph()
        else:
            self.graph = None
            print("⚠️ LangGraph no disponible. El agente ReAct no funcionará correctamente.")
        
        # Inicializar RAG avanzado si está habilitado
        self.advanced_rag: Optional[AdvancedRAGManager] = None
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
        
        # Calificación BANT del lead
        session = self.session_manager.get(state["session_id"])
        if session:
            conversation_history = [m.content for m in state["messages"] if isinstance(m, HumanMessage)]
            bant_qualification = self.lead_qualifier.qualify_lead(session, conversation_history)
            state["bant_qualification"] = bant_qualification
            
            # Obtener siguiente pregunta BANT si es necesario
            next_question = self.lead_qualifier.get_next_question(bant_qualification, sales_stage.value)
            if next_question:
                state["next_bant_question"] = next_question
        
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
            
            # Decision Layer: Decidir acción basada en intención y etapa
            action = self._decide_action(query, intent, sales_stage, state)
            
            # Mapear acciones del usuario a acciones internas
            if action == "start_checkout":
                action = "close"
            elif action == "handoff_human":
                action = "handoff"
            
            # Validar acción basada en pensamiento del LLM
            if action == "act" and ("necesito buscar" in thought_content.lower() or "necesito consultar" in thought_content.lower()):
                state["next_action"] = "act"
            elif action == "close" and ("listo para comprar" in thought_content.lower() or "procesar pago" in thought_content.lower()):
                state["next_action"] = "close"
            elif action == "handoff" or "hablar con alguien" in query.lower() or "humano" in query.lower():
                state["needs_handoff"] = True
                state["next_action"] = "end"
            else:
                # Si la acción es "answer", verificar si necesita más contexto
                if action == "answer":
                    # Verificar si hay suficiente contexto
                    context = state.get("context_retrieved", "")
                    if len(context) < 200:
                        state["next_action"] = "act"  # Necesita más información
                    else:
                        state["next_action"] = "end"  # Puede responder directamente
                else:
                    state["next_action"] = action
            
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
    
    def _decide_action(self, query: str, intent: IntentType, sales_stage: SalesStage, state: AgentState) -> str:
        """
        Decision Layer (Orquestador) - Decide la acción a tomar según intención y etapa.
        
        Implementa código exacto según especificaciones del usuario:
        - "comprar" → start_checkout
        - "hablar con alguien" → handoff_human
        - len(context) < 200 → ask_clarification
        - default → answer
        """
        q = query.lower()
        context = state.get("context_retrieved", "")
        
        # Código exacto según especificaciones del usuario
        if "comprar" in q:
            return "start_checkout"  # Mapeado a "close" internamente
        if "hablar con alguien" in q:
            return "handoff_human"  # Mapeado a "handoff" internamente
        if len(context) < 200:
            return "ask_clarification"
        
        # Lógica adicional para casos específicos
        if "pagar" in q or "checkout" in q or intent == IntentType.CHECKOUT:
            if sales_stage in [SalesStage.READY, SalesStage.CLOSING]:
                return "close"
            else:
                return "act"  # Necesita más info antes de cerrar
        
        if "humano" in q or "asesor" in q or "persona" in q:
            return "handoff"
        
        if intent in [IntentType.PRODUCTS, IntentType.POLICIES, IntentType.REVIEWS]:
            if len(context) < 200:
                return "act"  # Necesita buscar más información
            else:
                return "answer"  # Ya tiene suficiente contexto
        
        if sales_stage == SalesStage.READY and state.get("cart_snapshot"):
            return "close"
        
        if len(query.strip()) < 10 and not any(x in q for x in ["hola", "gracias", "ok", "sí", "no"]):
            return "ask_clarification"
        
        return "answer"
    
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
        """
        Detecta la etapa de venta actual (Sales Closer Elite).
        
        Etapas:
        - INTEREST: Interés inicial
        - CONSIDERATION: Considerando compra (preguntas sobre funcionalidad, garantía, etc.)
        - READY: Listo para comprar (pregunta por precio, quiere pagar)
        - CLOSING: En proceso de cierre (confirmando detalles)
        - COMPLETED: Venta completada
        """
        q = query.lower()
        
        # Señales de READY (listo para comprar)
        ready_signals = [
            "precio", "cuánto cuesta", "comprar", "pagar", "checkout",
            "carrito", "finalizar", "completar compra", "procesar pago"
        ]
        if any(x in q for x in ready_signals):
            return SalesStage.READY
        
        # Señales de CONSIDERATION (considerando)
        consideration_signals = [
            "envío", "entrega", "funciona", "garantía", "devolución",
            "vale la pena", "beneficio", "ventaja", "comparar", "diferencia"
        ]
        if any(x in q for x in consideration_signals):
            return SalesStage.CONSIDERATION
        
        # Señales de CLOSING (en cierre)
        closing_signals = [
            "confirmar", "sí quiero", "acepto", "de acuerdo", "perfecto",
            "proceder", "adelante", "sí compro"
        ]
        if any(x in q for x in closing_signals):
            return SalesStage.CLOSING
        
        # Verificar etapa previa en sesión
        session = self.session_manager.get(state["session_id"])
        if session and hasattr(session, 'sales_stage'):
            return session.sales_stage
        
        return SalesStage.INTEREST
    
    def _select_sales_strategy(self, query: str, stage: SalesStage) -> SalesStrategy:
        """
        Selecciona estrategia de venta según query y etapa.
        
        Implementa código exacto según especificaciones del usuario:
        - precio → ANCHORING
        - vale la pena → ROI
        - opiniones → SOCIAL_PROOF
        - default → STANDARD
        """
        q = query.lower()
        
        # Código exacto según especificaciones del usuario
        if "precio" in q:
            return SalesStrategy.ANCHORING
        if "vale la pena" in q:
            return SalesStrategy.ROI
        if "opiniones" in q:
            return SalesStrategy.SOCIAL_PROOF
        
        # Detección adicional
        if "caro" in q:
            return SalesStrategy.ANCHORING
        elif "beneficio" in q:
            return SalesStrategy.ROI
        elif "opinión" in q or "otros" in q:
            return SalesStrategy.SOCIAL_PROOF
        elif "después" in q or "luego" in q:
            return SalesStrategy.URGENCY
        
        return SalesStrategy.STANDARD
    
    def _retrieve_context(self, query: str, intent: IntentType) -> str:
        """Recupera contexto según intención usando RAG avanzado"""
        if not self.config.enable_rag_advanced or not self.advanced_rag:
            return ""
        
        # Mapear IntentType a RAGIntentType
        intent_map = {
            IntentType.PRODUCTS: RAGIntentType.PRODUCTOS,
            IntentType.POLICIES: RAGIntentType.POLITICAS,
            IntentType.REVIEWS: RAGIntentType.REVIEWS,
            IntentType.GENERAL: RAGIntentType.GENERAL,
        }
        
        rag_intent = intent_map.get(intent, RAGIntentType.GENERAL)
        
        # Recuperar contexto con validación de confianza
        result = self.advanced_rag.retrieve_with_confidence(query, rag_intent)
        return result.get("context", "")
    
    def _initialize_advanced_rag(self):
        """Inicializa RAG avanzado con índices separados"""
        try:
            # Obtener embeddings desde app_config
            if self.app_config:
                try:
                    from langchain_openai import OpenAIEmbeddings
                    embeddings = OpenAIEmbeddings(
                        openai_api_key=self.app_config.openai_api_key
                    )
                except:
                    # Fallback a embeddings simples si OpenAI no está disponible
                    print("⚠️ OpenAI embeddings no disponible. Usando embeddings básicos.")
                    from langchain.embeddings import FakeEmbeddings
                    embeddings = FakeEmbeddings(size=384)
            else:
                from langchain.embeddings import FakeEmbeddings
                embeddings = FakeEmbeddings(size=384)
            
            self.advanced_rag = AdvancedRAGManager(
                embeddings=embeddings,
                base_dir=None,  # Usar default
                k=4,
            )
            print("✅ RAG Avanzado inicializado con índices separados")
        except Exception as e:
            print(f"⚠️ Error inicializando RAG avanzado: {e}")
            self.advanced_rag = None
    
    def _build_think_prompt(self, state: AgentState) -> str:
        """
        Construye el prompt para el nodo think (ReAct pattern).
        
        Implementa flujo: Siente → Piensa → Actúa → Aprende
        """
        sales_stage = state.get("sales_stage", SalesStage.INTEREST)
        strategy = state.get("sales_strategy", SalesStrategy.STANDARD)
        intent = state.get("intent", IntentType.GENERAL)
        
        # Obtener contexto de mensajes anteriores
        messages = state.get("messages", [])
        recent_context = ""
        if len(messages) > 1:
            recent_context = "\n".join([
                f"{'Usuario' if isinstance(m, HumanMessage) else 'Asistente'}: {m.content}"
                for m in messages[-3:]  # Últimos 3 mensajes
            ])
        
        prompt = f"""Eres un asistente virtual 24/7 para {self.config.brand_name}, especializado en ventas y soporte al cliente.

**CONTEXTO ACTUAL:**
- Etapa de venta: {sales_stage.value}
- Estrategia: {strategy.value}
- Intención detectada: {intent.value}
- Idioma: {self.config.language}

**HISTORIAL RECIENTE:**
{recent_context if recent_context else "Inicio de conversación"}

**INSTRUCCIONES (ReAct Pattern):**
Piensa paso a paso siguiendo el patrón ReAct:

1. **THOUGHT (Pensamiento):**
   - ¿Qué información necesitas para responder adecuadamente?
   - ¿Qué herramientas debes usar? (catálogo, carrito, políticas, etc.)
   - ¿Está el usuario listo para comprar o necesita más información?

2. **ACTION (Acción):**
   - Si necesitas información: busca en el catálogo, consulta políticas, etc.
   - Si el usuario está listo: guía hacia el checkout
   - Si hay objeciones: aplica técnicas de manejo de objeciones

3. **OBSERVATION (Observación):**
   - Procesa los resultados de tus acciones
   - Evalúa si necesitas más información o puedes responder

4. **FINAL ANSWER (Respuesta Final):**
   - Proporciona una respuesta clara, útil y orientada a cerrar la venta
   - Sé conversacional y natural
   - Si es apropiado, aplica técnicas de cierre

**IMPORTANTE:**
- Actúa como asistente profesional 24/7
- Aprende de las interacciones para mejorar
- Escala a humano si detectas frustración o el usuario lo solicita
- Mantén el enfoque en ayudar y cerrar ventas de manera ética

Responde de manera natural y conversacional, pensando paso a paso."""
        
        return prompt
    
    def _apply_closing_techniques(self, state: AgentState, strategy: SalesStrategy) -> str:
        """
        Aplica técnicas de cierre según estrategia (Sales Closer Elite).
        
        Implementa:
        - ANCHORING: Anclar precio/valor
        - ROI: Retorno de inversión
        - SOCIAL_PROOF: Prueba social
        - URGENCY: Urgencia/escasez ética
        - STANDARD: Estrategia estándar
        """
        sales_stage = state.get("sales_stage", SalesStage.INTEREST)
        query = state["messages"][-1].content if state["messages"] else ""
        
        # Manejo de objeciones
        objection = self._detect_objection(query)
        if objection:
            return self._handle_objection(objection, strategy)
        
        # Técnicas de cierre según estrategia
        if strategy == SalesStrategy.ANCHORING:
            return "Entiendo tu preocupación por el precio. Este producto incluye características premium que lo hacen una excelente inversión a largo plazo. ¿Te gustaría que te muestre el desglose de valor?"
        elif strategy == SalesStrategy.ROI:
            return "Este producto te ahorrará tiempo y dinero a largo plazo. ¿Qué tendría que pasar para que lo veas útil ahora mismo?"
        elif strategy == SalesStrategy.SOCIAL_PROOF:
            return "Muchos clientes están satisfechos con este producto. ¿Querés que te muestre algunas opiniones y reseñas?"
        elif strategy == SalesStrategy.URGENCY:
            # Urgencia ética (no falsa escasez)
            return "Tenemos disponibilidad limitada en este momento. ¿Querés que lo procesemos ahora y te lo envío enseguida?"
        else:
            # Cierre directo
            return self._close_sale_direct()
    
    def _detect_objection(self, query: str) -> Optional[str]:
        """Detecta objeciones comunes en el query"""
        q = query.lower()
        
        if any(x in q for x in ["caro", "precio alto", "muy costoso", "demasiado"]):
            return "price"
        elif any(x in q for x in ["después", "luego", "más tarde", "no ahora", "esperar"]):
            return "timing"
        elif any(x in q for x in ["no estoy seguro", "dudar", "pensar", "considerar"]):
            return "uncertainty"
        elif any(x in q for x in ["no necesito", "no me sirve", "no es para mí"]):
            return "need"
        
        return None
    
    def _handle_objection(self, objection: str, strategy: SalesStrategy) -> str:
        """
        Maneja objeciones con técnicas específicas.
        
        Implementa código exacto según especificaciones del usuario:
        - caro → "Entiendo. Justamente por eso incluye X, Y y Z que ahorran dinero a largo plazo."
        - después → "Tiene sentido. ¿Qué tendría que pasar para que lo veas útil ahora?"
        """
        objection_lower = objection.lower()
        
        # Código exacto según especificaciones del usuario
        if "caro" in objection_lower:
            return "Entiendo. Justamente por eso incluye X, Y y Z que ahorran dinero a largo plazo."
        if "después" in objection_lower:
            return "Tiene sentido. ¿Qué tendría que pasar para que lo veas útil ahora?"
        
        # Manejo adicional de objeciones detectadas por tipo
        if objection == "price":
            return "Entiendo. Justamente por eso incluye características que ahorran dinero a largo plazo. ¿Te gustaría que te muestre cómo se amortiza la inversión?"
        elif objection == "timing":
            return "Tiene sentido. ¿Qué tendría que pasar para que lo veas útil ahora? Tal vez podamos encontrar una solución que se ajuste a tus necesidades."
        elif objection == "uncertainty":
            return "Es normal tener dudas. ¿Hay algo específico que te gustaría saber más para tomar una decisión informada?"
        elif objection == "need":
            return "Entiendo. ¿Podrías contarme más sobre tu situación? Tal vez pueda recomendarte algo que se ajuste mejor a tus necesidades."
        
        return "Entiendo tu preocupación. ¿Hay algo específico en lo que pueda ayudarte?"
    
    def _close_sale_direct(self) -> str:
        """
        Cierre directo y ético.
        
        Implementa código exacto según especificaciones del usuario:
        "¿Querés que lo procesemos ahora y te lo envío enseguida?"
        """
        # Código exacto según especificaciones del usuario
        return "¿Querés que lo procesemos ahora y te lo envío enseguida?"
    
    def _track_conversion(self, state: AgentState, event_type: str):
        """
        Trackea eventos de conversión (métricas para PYMEs).
        
        Eventos:
        - interest_detected: Interés inicial detectado
        - consideration: Usuario en etapa de consideración
        - ready_to_buy: Usuario listo para comprar
        - payment_initiated: Pago iniciado
        - payment_completed: Pago completado
        - objection_handled: Objeción manejada
        - handoff_to_human: Escalado a humano
        """
        try:
            session_id = state.get("session_id", "unknown")
            sales_stage = state.get("sales_stage", SalesStage.INTEREST).value
            
            # Log de evento (en producción, enviar a analytics)
            print(f"📊 Conversion Event: {event_type} | Session: {session_id} | Stage: {sales_stage}")
            
            # Actualizar sesión con evento
            session = self.session_manager.get(session_id)
            if session:
                # Agregar evento a metadata de sesión
                if not hasattr(session, 'conversion_events'):
                    session.conversion_events = []
                session.conversion_events.append({
                    "type": event_type,
                    "stage": sales_stage,
                    "timestamp": self._get_timestamp(),
                })
        except Exception as e:
            print(f"⚠️ Error trackeando conversión: {e}")
    
    def _get_timestamp(self) -> str:
        """Obtiene timestamp actual"""
        from datetime import datetime
        return datetime.now().isoformat()
    
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
            
            # Registrar interacción para aprendizaje continuo
            session = self.session_manager.get(session_id)
            if session:
                user_message = message
                self.learning_system.record_interaction(
                    session=session,
                    user_message=user_message,
                    agent_response=response_text,
                    conversion=final_state.get("conversion_tracked", False),
                )
            
            # Construir respuesta con todos los datos
            response_data = {
                "text": response_text,
                "intent": final_state.get("intent", IntentType.GENERAL).value,
                "sales_stage": final_state.get("sales_stage", SalesStage.INTEREST).value,
                "needs_handoff": final_state.get("needs_handoff", False),
                "cart": final_state.get("cart_snapshot", {}),
            }
            
            # Agregar pregunta BANT si existe
            next_bant_question = final_state.get("next_bant_question")
            if next_bant_question:
                response_data["next_bant_question"] = next_bant_question
            
            return response_data
            
        except Exception as e:
            print(f"❌ Error en workflow ReAct: {e}")
            import traceback
            traceback.print_exc()
            return {
                "text": "Lo siento, hubo un error procesando tu mensaje. Por favor, inténtalo de nuevo.",
                "error": str(e)
            }

