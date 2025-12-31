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
import os
from datetime import datetime
from pathlib import Path
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


class ObjectionDetector:
    """
    Detecta objeciones comunes en el mensaje del usuario.
    Reglas heurísticas simples.
    """
    
    def __init__(self):
        self.objection_keywords = {
            "caro": ["caro", "costoso", "precio alto", "muy caro", "carísimo", "demasiado caro"],
            "después": ["después", "más tarde", "luego", "después lo compro", "ya veré"],
            "precio": ["precio", "cuánto cuesta", "vale mucho", "es caro"],
            "calidad": ["calidad", "es bueno", "confianza", "duradero"],
            "tiempo": ["tarda", "demora", "envío", "cuándo llega"],
        }
    
    def detect_objection(self, query: str) -> Optional[str]:
        """
        Detecta si hay una objeción en el query.
        
        Returns:
            Tipo de objeción o None si no hay objeción
        """
        query_lower = query.lower()
        
        for objection_type, keywords in self.objection_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                return objection_type
        
        return None
    
    def is_objection(self, query: str) -> bool:
        """Retorna True si el query contiene una objeción."""
        return self.detect_objection(query) is not None


class ProductRecommender:
    """
    Sistema básico de recomendaciones (upsell/cross-sell).
    Reglas heurísticas simples basadas en productos mencionados.
    """
    
    def __init__(self, catalog_tool: CatalogTool):
        self.catalog_tool = catalog_tool
    
    def get_upsell_recommendations(self, current_product_name: str, limit: int = 2) -> List[Dict[str, Any]]:
        """
        Recomienda productos superiores (upsell) basado en el producto actual.
        
        Heurística simple: busca productos con palabras clave "premium", "pro", "deluxe"
        o productos similares pero con precio mayor.
        """
        recommendations = []
        try:
            # Buscar productos relacionados
            related = self.catalog_tool.suggest_alternatives(current_product_name, limit=limit * 2)
            
            # Filtrar productos que podrían ser upsell (precio mayor o keywords premium)
            for product in related[:limit]:
                if hasattr(product, 'name') and product.name:
                    name_lower = product.name.lower()
                    # Detectar keywords de upsell
                    upsell_keywords = ["premium", "pro", "deluxe", "superior", "advanced"]
                    is_upsell = any(keyword in name_lower for keyword in upsell_keywords)
                    
                    if is_upsell:
                        recommendations.append({
                            "product_id": getattr(product, 'id', ''),
                            "name": getattr(product, 'name', ''),
                            "price": getattr(product, 'price', 0),
                            "type": "upsell",
                        })
        except Exception as e:
            print(f"⚠️ Error en upsell recommendations: {e}")
        
        return recommendations
    
    def get_cross_sell_recommendations(self, current_product_name: str, limit: int = 2) -> List[Dict[str, Any]]:
        """
        Recomienda productos complementarios (cross-sell).
        
        Heurística simple: productos relacionados del catálogo.
        """
        recommendations = []
        try:
            # Buscar productos relacionados
            related = self.catalog_tool.suggest_alternatives(current_product_name, limit=limit * 2)
            
            # Excluir el producto actual y tomar los primeros
            for product in related[:limit]:
                if hasattr(product, 'name') and product.name and product.name.lower() != current_product_name.lower():
                    recommendations.append({
                        "product_id": getattr(product, 'id', ''),
                        "name": getattr(product, 'name', ''),
                        "price": getattr(product, 'price', 0),
                        "type": "cross_sell",
                    })
        except Exception as e:
            print(f"⚠️ Error en cross-sell recommendations: {e}")
        
        return recommendations
    
    def get_recommendations(
        self,
        products_mentioned: List[str],
        personalization: Dict[str, Any],
        lead_temperature: str,
        limit: int = 2
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Genera recomendaciones combinadas (upsell + cross-sell).
        
        Args:
            products_mentioned: Lista de productos mencionados
            personalization: Datos de personalización
            lead_temperature: Temperatura del lead (cold/warm/hot)
            limit: Número máximo de recomendaciones por tipo
            
        Returns:
            Dict con "upsell" y "cross_sell" lists
        """
        all_recommendations = {"upsell": [], "cross_sell": []}
        
        # Solo recomendar si el lead es warm o hot
        if lead_temperature == "cold":
            return all_recommendations
        
        # Si no hay productos mencionados, no hacer recomendaciones
        if not products_mentioned:
            return all_recommendations
        
        # Usar el primer producto mencionado como base
        base_product = products_mentioned[0]
        
        # Obtener recomendaciones
        try:
            upsell = self.get_upsell_recommendations(base_product, limit=limit)
            cross_sell = self.get_cross_sell_recommendations(base_product, limit=limit)
            
            all_recommendations["upsell"] = upsell
            all_recommendations["cross_sell"] = cross_sell
        except Exception as e:
            print(f"⚠️ Error generando recomendaciones: {e}")
        
        return all_recommendations


class LeadScorer:
    """
    Sistema de scoring de leads con reglas heurísticas (0-100).
    FASE 1: Sin ML, solo reglas basadas en comportamiento.
    """
    
    def __init__(self):
        self.base_score = 0
        self.max_score = 100
    
    def calculate_score(
        self,
        intent: str,
        sales_stage: str,
        clear_intent: str,
        messages_count: int,
        has_cart_items: bool,
        has_payment_link: bool,
        products_mentioned: List[str],
        personalization: Dict[str, Any]
    ) -> int:
        """
        Calcula score de lead (0-100) basado en reglas heurísticas.
        
        Args:
            intent: Intención detectada
            sales_stage: Etapa de venta
            clear_intent: Intención clara (precio, compra, checkout, info)
            messages_count: Número de mensajes en la conversación
            has_cart_items: Si tiene items en carrito
            has_payment_link: Si tiene link de pago
            products_mentioned: Productos mencionados
            personalization: Datos de personalización
            
        Returns:
            Score de 0 a 100
        """
        score = 0
        
        # 1. Intención clara (0-30 puntos)
        if clear_intent == "checkout":
            score += 30
        elif clear_intent == "compra":
            score += 25
        elif clear_intent == "precio":
            score += 15
        elif clear_intent == "info":
            score += 10
        else:  # explorando
            score += 5
        
        # 2. Etapa de venta (0-25 puntos)
        if sales_stage == "closing":
            score += 25
        elif sales_stage == "ready":
            score += 20
        elif sales_stage == "consideration":
            score += 15
        elif sales_stage == "interest":
            score += 10
        else:
            score += 5
        
        # 3. Comportamiento de compra (0-20 puntos)
        if has_payment_link:
            score += 20
        elif has_cart_items:
            score += 15
        elif len(products_mentioned) > 0:
            score += 10
        
        # 4. Engagement (0-15 puntos)
        if messages_count >= 5:
            score += 15
        elif messages_count >= 3:
            score += 10
        elif messages_count >= 2:
            score += 5
        
        # 5. Personalización (0-10 puntos)
        if personalization.get("talla") or personalization.get("color"):
            score += 10
        elif personalization.get("products_mentioned"):
            score += 5
        
        # Asegurar que el score esté entre 0 y 100
        return min(max(score, 0), 100)
    
    def get_temperature(self, score: int) -> str:
        """
        Determina temperatura del lead basado en score.
        
        Args:
            score: Score del lead (0-100)
            
        Returns:
            "cold", "warm", o "hot"
        """
        if score >= 70:
            return "hot"
        elif score >= 40:
            return "warm"
        else:
            return "cold"
    
    def detect_clear_intent(self, query: str, sales_stage: str) -> str:
        """
        Detecta intención clara del usuario.
        
        Args:
            query: Mensaje del usuario
            sales_stage: Etapa de venta actual
            
        Returns:
            "precio", "compra", "checkout", "info", o "explorando"
        """
        query_lower = query.lower()
        
        # Checkout (más alta prioridad)
        checkout_keywords = [
            "pagar", "checkout", "comprar ahora", "finalizar compra",
            "proceder al pago", "ir a pagar", "completar compra"
        ]
        if any(keyword in query_lower for keyword in checkout_keywords):
            return "checkout"
        
        # Compra
        compra_keywords = [
            "quiero comprar", "me interesa comprar", "dame", "necesito",
            "agregar al carrito", "añadir al carrito", "comprar"
        ]
        if any(keyword in query_lower for keyword in compra_keywords):
            return "compra"
        
        # Precio
        precio_keywords = [
            "precio", "cuánto cuesta", "cuánto vale", "costo",
            "precio de", "vale", "cuesta"
        ]
        if any(keyword in query_lower for keyword in precio_keywords):
            return "precio"
        
        # Info (preguntas específicas)
        info_keywords = [
            "qué", "cómo", "cuál", "dónde", "cuándo", "talles",
            "colores", "material", "talla", "color", "disponible"
        ]
        if any(keyword in query_lower for keyword in info_keywords):
            return "info"
        
        # Por defecto: explorando
        return "explorando"


class AgentState(TypedDict):
    """Estado del agente ReAct con Multi-Agent RAG completo + FASE 1 (Lead Scoring y Métricas)."""
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
    # FASE 1: Lead Scoring y Métricas
    lead_score: int  # Score 0-100
    lead_temperature: str  # "cold", "warm", "hot"
    clear_intent: str  # "precio", "compra", "checkout", "info", "explorando"
    metrics: Dict[str, Any]  # Métricas básicas
    personalization: Dict[str, Any]  # Personalización mínima
    events: List[Dict[str, Any]]  # Registro de eventos
    # Detección de objeciones
    objection_detected: bool
    objection_type: Optional[str]


class ReactSalesAgentConfig:
    """Configuración del ReactSalesAgent."""
    def __init__(
        self,
        brand_name: str = "Your Brand",
        language: str = "es",
        enable_sales_closer: bool = True,
        enable_rag_advanced: bool = True,
        enable_verification: bool = True,
        base_url: Optional[str] = None,
    ):
        self.brand_name = brand_name
        self.language = language
        self.base_url = base_url or os.getenv("BASE_URL") or os.getenv("SHOPIFY_SHOP_URL")  # URL base para generar links
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
                # Usar sentence-transformers (gratis, local) en lugar de OpenAI embeddings
                # Claude/Anthropic no tiene modelo de embeddings dedicado
                from langchain_community.embeddings import HuggingFaceEmbeddings
                import os
                
                # Usar modelo multilingüe que funciona bien en español
                # Este modelo es gratuito, local y no requiere API calls
                embeddings = HuggingFaceEmbeddings(
                    model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
                    model_kwargs={'device': 'cpu'},  # Usar CPU (cambiar a 'cuda' si tienes GPU)
                    encode_kwargs={'normalize_embeddings': True}
                )
                
                # Directorio para persistir el RAG (los documentos se guardan aquí)
                base_dir = Path("docchat/star_agent/rag_storage")
                base_dir.mkdir(parents=True, exist_ok=True)
                
                self.advanced_rag = AdvancedRAGManager(embeddings=embeddings, base_dir=base_dir)
                print("✅ AdvancedRAGManager inicializado para ReactSalesAgent (usando sentence-transformers - gratis y local)")
            except ImportError as e:
                print(f"⚠️ Error: sentence-transformers no instalado. Instala con: pip install sentence-transformers")
                print(f"   Detalles: {e}")
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
        
        # FASE 1: Lead Scoring y Métricas
        self.lead_scorer = LeadScorer()
        
        # Sistema de detección de objeciones
        self.objection_detector = ObjectionDetector()
        
        # Sistema de recomendaciones (upsell/cross-sell)
        self.product_recommender = ProductRecommender(catalog_tool)
        
        # Links Manager - Para acceder a links configurados desde UI (con sistema de 3 capas)
        from ..config.links_manager import LinksManager
        from ..config.intent_link_mapper import UserIntent, LinkType
        self.links_manager = LinksManager()
        self.user_intent_type = UserIntent  # Para acceso a UserIntent
        self.link_type = LinkType  # Para acceso a LinkType
        
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
                        self._rag_manager = rag_manager
                    
                    def _get_relevant_documents(self, query: str) -> List:
                        """Retorna documentos relevantes usando AdvancedRAGManager."""
                        result = self._rag_manager.retrieve_with_confidence(query)
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
        
        # Flujo principal simplificado: think → act → close (directo, sin observe)
        workflow.add_edge("think", "act")
        workflow.add_edge("act", "close")  # Directo a close después de ejecutar herramientas
        
        # Después de handoff, terminar
        workflow.add_edge("handoff", END)
        
        # Después de verificar, decidir
        workflow.add_conditional_edges(
            "verify",
            self._after_verify,
            {
                "close": "close",
                "think": "think",  # Volver a pensar si no pasó verificación
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
        
        # FASE 1: Detección de intención clara
        clear_intent = self.lead_scorer.detect_clear_intent(user_query, sales_stage)
        
        # FASE 1: Obtener personalización y memoria conversacional
        personalization = state.get("personalization", {})
        previous_score = state.get("lead_score", 0)
        previous_temperature = state.get("lead_temperature", "cold")
        
        # Actualizar personalización: extraer productos, talla, color mencionados
        personalization = self._update_personalization(user_query, personalization, messages)
        
        # FASE 1: Calcular score de lead
        products_mentioned = personalization.get("products_mentioned", [])
        has_cart_items = bool(state.get("cart") and state.get("cart").get("items"))
        has_payment_link = bool(state.get("payment_link"))
        messages_count = len([m for m in messages if isinstance(m, HumanMessage)])
        
        lead_score = self.lead_scorer.calculate_score(
            intent=intent,
            sales_stage=sales_stage,
            clear_intent=clear_intent,
            messages_count=messages_count,
            has_cart_items=has_cart_items,
            has_payment_link=has_payment_link,
            products_mentioned=products_mentioned,
            personalization=personalization
        )
        
        lead_temperature = self.lead_scorer.get_temperature(lead_score)
        
        # FASE 1: Registrar evento de cambio de score
        events = state.get("events", [])
        if lead_score != previous_score:
            events.append({
                "type": "score_change",
                "previous_score": previous_score,
                "new_score": lead_score,
                "temperature": lead_temperature,
                "timestamp": str(datetime.now()) if 'datetime' in dir() else ""
            })
        
        # Registrar evento de intención detectada
        events.append({
            "type": "intent_detected",
            "clear_intent": clear_intent,
            "intent": intent,
            "sales_stage": sales_stage,
            "timestamp": str(datetime.now()) if 'datetime' in dir() else ""
        })
        
        # FASE 1: Inicializar métricas si no existen
        metrics = state.get("metrics", {})
        metrics["intent_detected"] = clear_intent
        metrics["score_current"] = lead_score
        metrics["temperature"] = lead_temperature
        metrics["link_shown"] = False  # Se actualizará en close_node
        metrics["link_clicked"] = False  # Se actualizará cuando se detecte click
        
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
        
        # Detección de objeciones
        objection_type = self.objection_detector.detect_objection(user_query)
        objection_detected = objection_type is not None
        
        # Si hay objeción, manejarla automáticamente
        objection_response = None
        if objection_detected and objection_type:
            objection_response = self._handle_objection(user_query)
            # Registrar evento
            events.append({
                "type": "objection_detected",
                "objection_type": objection_type,
                "timestamp": str(datetime.now())
            })
        
        # Generar recomendaciones (upsell/cross-sell) si aplica
        recommendations = {}
        if lead_temperature in ["warm", "hot"] and products_mentioned:
            recommendations = self.product_recommender.get_recommendations(
                products_mentioned=products_mentioned,
                personalization=personalization,
                lead_temperature=lead_temperature,
                limit=2
            )
        
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
        
        # Si hay objeción detectada, incluir respuesta de objeción en tool_results
        tool_results_with_extras = decision.copy() if decision else {}
        if objection_detected and objection_response:
            tool_results_with_extras["objection"] = {
                "type": objection_type,
                "response": objection_response,
            }
        
        # Incluir recomendaciones en tool_results
        if recommendations:
            tool_results_with_extras["recommendations"] = recommendations
        
        return {
            "messages": [response],
            "intent": intent,
            "sales_stage": sales_stage,
            "context_retrieved": context,
            "tool_results": tool_results_with_extras,
            # FASE 1: Lead Scoring y Métricas
            "lead_score": lead_score,
            "lead_temperature": lead_temperature,
            "clear_intent": clear_intent,
            "metrics": metrics,
            "personalization": personalization,
            "events": events,
            # Detección de objeciones
            "objection_detected": objection_detected,
            "objection_type": objection_type,
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
        tool_call_map = {}  # Mapear tool_name a tool_call_id para crear ToolMessage
        
        # Ejecutar herramientas
        for idx, tool_call in enumerate(tool_calls):
            # Los tool_calls son diccionarios en LangChain
            tool_name = tool_call.get("name") if isinstance(tool_call, dict) else getattr(tool_call, "name", None)
            tool_args = tool_call.get("args", {}) if isinstance(tool_call, dict) else getattr(tool_call, "args", {})
            
            # Si no hay tool_name, saltar esta tool_call
            if not tool_name:
                continue
            
            # Obtener tool_call_id (generar uno si no existe)
            if isinstance(tool_call, dict):
                tool_call_id = tool_call.get("id", f"call_{tool_name}_{idx}")
            else:
                tool_call_id = getattr(tool_call, "id", f"call_{tool_name}_{idx}")
            
            # Guardar tool_call_id para usar en ToolMessage
            tool_call_map[tool_name] = tool_call_id
            
            try:
                if tool_name == "search_products":
                    query = tool_args.get("query", "")
                    # Usar get_products_with_links para generar links automáticamente
                    base_url = getattr(self.config, 'base_url', None) or os.getenv("BASE_URL")
                    result = self.catalog_tool.get_products_with_links(query=query, base_url=base_url, limit=5)
                    executed_tools["products"] = result
                    # También guardar resultado compatible con formato anterior
                    if isinstance(result, dict) and "products" in result:
                        executed_tools["products_list"] = result["products"]
                
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
            # Obtener tool_call_id correspondiente, o generar uno si no existe
            tool_call_id = tool_call_map.get(tool_name, f"call_{tool_name}_{len(tool_messages)}")
            
            tool_messages.append(
                ToolMessage(
                    content=json.dumps(result, default=str),
                    name=tool_name,
                    tool_call_id=tool_call_id,
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
        
        # Obtener etapa de venta e intención del estado
        sales_stage = state.get("sales_stage", "interest")
        intent = state.get("intent", "general")
        
        # Determinar si debe enviar links de productos basado en etapa de venta e intención
        should_include_product_links = self._should_include_product_links(sales_stage, intent, state)
        
        # Obtener último mensaje del usuario para detectar intención (CAPA 1+2+3)
        messages = state.get("messages", [])
        last_user_message = ""
        for msg in reversed(messages):
            if hasattr(msg, 'content') and isinstance(msg.content, str):
                last_user_message = msg.content
                break
        
        # CAPA 1+2+3: Detectar intención y obtener link correcto
        user_intent = self.links_manager.intent_mapper.detect_intent(last_user_message, sales_stage)
        link_for_intent = self.links_manager.format_link_for_intent(user_intent, sales_stage)
        
        # Obtener contexto del RAG del estado
        context_retrieved = state.get("context_retrieved", "")
        draft_answer = state.get("draft_answer", "")
        
        # Construir contexto de observación
        observation_context = self._build_observation_context(tool_results, include_links=should_include_product_links)
        
        # Agregar contexto del RAG si está disponible
        rag_context = ""
        if context_retrieved:
            rag_context = f"\n\n**Contexto recuperado de documentos (RAG - ÚSALO COMPLETAMENTE):**\n{context_retrieved[:2000]}"
        if draft_answer and draft_answer not in context_retrieved:
            rag_context += f"\n\n**Información adicional del Research Agent:**\n{draft_answer[:1000]}"
        
        # Agregar link configurado según intención
        if link_for_intent:
            observation_context += f"\n\n**🔗 LINK OBLIGATORIO para incluir:** {link_for_intent}"
        
        # Invocar LLM para procesar observaciones
        observation_prompt = f"""
Analiza los resultados de las herramientas ejecutadas y decide el siguiente paso.

**Resultados de herramientas:**
{observation_context}
{rag_context}

**INFORMACIÓN INTERNA (NO MENCIONAR AL USUARIO):**
- Etapa de venta actual: {sales_stage}
- Intención detectada: {intent}

**Instrucciones CRÍTICAS sobre LINKS (OBLIGATORIO):**
- Si hay "🔗 LINK OBLIGATORIO" en el contexto, DEBES incluirlo en tu respuesta.
- Los links son el 90% del producto - SIEMPRE inclúyelos cuando están disponibles.
- Formato: [Texto](url) en Markdown.
- NO elijas links al azar - usa SOLO los links proporcionados.
{"✅ INCLUYE LINKS DE PRODUCTOS:" if should_include_product_links else "❌ NO INCLUYAS LINKS DE PRODUCTOS todavía:"}
{self._get_link_instructions(sales_stage, intent, should_include_product_links)}

**Otras instrucciones:**
1. Si hay un carrito actualizado, menciona los productos agregados.
2. Si hay un payment_link, inclúyelo claramente con un CTA: [Pagar ahora](payment_link).
3. Si hay errores, explica qué salió mal.
4. Decide si necesitas más información o si puedes generar la respuesta final.
5. IMPORTANTE: Si generas un "response_draft", NO incluyas información técnica como "etapa de venta", "intención detectada", etc. Responde de forma natural y conversacional.

Responde en JSON:
{{
    "ready_to_respond": true/false,
    "needs_more_info": true/false,
    "response_draft": "borrador de respuesta si está listo (sin información técnica)",
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
        
        # FASE 1: Obtener datos de scoring y personalización
        lead_score = state.get("lead_score", 0)
        lead_temperature = state.get("lead_temperature", "cold")
        clear_intent = state.get("clear_intent", "explorando")
        personalization = state.get("personalization", {})
        metrics = state.get("metrics", {})
        events = state.get("events", [])
        
        # FASE 1: Determinar si debe incluir links basado en intención + etapa + score
        should_include_links = self._should_send_link(clear_intent, sales_stage, lead_score, lead_temperature)
        
        # FASE 1: Registrar si se va a mostrar un link
        if should_include_links:
            metrics["link_shown"] = True
            events.append({
                "type": "link_shown",
                "clear_intent": clear_intent,
                "sales_stage": sales_stage,
                "lead_score": lead_score,
                "timestamp": str(datetime.now())
            })
        
        # Construir prompt de cierre con contexto unificado
        close_prompt = self._build_close_prompt(
            sales_stage=sales_stage,
            intent=intent,
            tool_results=tool_results,
            context=context,
            closing_strategy=closing_strategy,
            state=state,
            # FASE 1: Contexto unificado
            lead_score=lead_score,
            lead_temperature=lead_temperature,
            clear_intent=clear_intent,
            personalization=personalization,
        )
        
        # Generar respuesta final
        response = self.llm.invoke([
            SystemMessage(content=close_prompt),
            HumanMessage(content="Genera la respuesta final optimizada para el widget. Responde en texto natural, NO en JSON."),
        ])
        
        final_text = response.content if hasattr(response, 'content') else str(response)
        
        # Limpiar respuesta: eliminar JSON si aparece accidentalmente
        # Si la respuesta contiene JSON estructurado, extraer solo el texto útil
        import re
        # Buscar si hay bloques JSON en la respuesta
        json_pattern = r'\{[^{}]*"response_draft"[^{}]*\}'
        if re.search(json_pattern, final_text):
            # Intentar extraer solo el contenido útil
            match = re.search(r'"response_draft"\s*:\s*"([^"]+)"', final_text)
            if match:
                final_text = match.group(1)
            else:
                # Si no se puede extraer, eliminar el JSON completo
                final_text = re.sub(json_pattern, '', final_text).strip()
        
        # Eliminar cualquier otro JSON visible
        final_text = re.sub(r'\{[^{}]*\}', '', final_text).strip()
        
        # Limpiar espacios múltiples
        final_text = re.sub(r'\s+', ' ', final_text).strip()
        
        # Validar respuesta antes de enviar
        final_text = self._validate_and_improve_response(final_text, context, tool_results)
        
        # Extraer payment_link si existe
        payment_link = tool_results.get("payment_link") or tool_results.get("payment", {}).get("payment_link")
        
        return {
            "messages": [AIMessage(content=final_text)],
            "closing_activated": closing_strategy is not None,
        }
    
    def _handoff_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Nodo de Handoff.
        
        Inicia el proceso de transferencia a un agente humano.
        """
        user_query = state["messages"][-1].content if state["messages"] else "No message"
        session_id = state["session_id"]
        user_id = state["user_id"]
        conversation_history = self._format_conversation_history(state["messages"])
        
        print(f"🚨 Iniciando handoff para sesión {session_id} a {self.handoff_manager.provider}")
        
        handoff_result = self.handoff_manager.create_ticket(
            session_id=session_id,
            user_id=user_id,
            user_message=user_query,
            conversation_history=conversation_history,
            priority="high"  # Handoff suele ser alta prioridad
        )
        
        handoff_message = handoff_result.get("message", "Se ha solicitado la transferencia a un agente humano.")
        if handoff_result.get("success"):
            handoff_message = f"✅ {handoff_message} Un agente se pondrá en contacto contigo pronto."
        else:
            handoff_message = f"⚠️ {handoff_message} Por favor, intenta contactarnos por otro medio."
        
        return {
            "messages": [AIMessage(content=handoff_message)],
            "needs_handoff": True,  # Mantener en true para señalizar que el handoff ocurrió
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
        
        # Obtener links relevantes usando sistema de 3 capas (CAPA 1+2+3)
        relevant_links_list = self.links_manager.get_relevant_links_for_query(user_query, sales_stage)
        
        # Detectar intención para incluir en prompt
        user_intent = self.links_manager.intent_mapper.detect_intent(user_query, sales_stage)
        link_for_intent = self.links_manager.format_link_for_intent(user_intent, sales_stage)
        
        links_context = ""
        if relevant_links_list or link_for_intent:
            links_to_show = relevant_links_list if relevant_links_list else ([link_for_intent] if link_for_intent else [])
            if links_to_show:
                links_context = f"\n\n**🔗 LINK OBLIGATORIO para incluir en la respuesta:**\n" + "\n".join(links_to_show)
                links_context += f"\n\n**Intención detectada:** {user_intent.value}\n**Acción:** INCLUYE este link en tu respuesta."
        
        prompt = f"""
Eres un asistente virtual 24/7 para {self.config.brand_name}.

**REGLAS CRÍTICAS - LÉELAS CUIDADOSAMENTE:**
1. SOLO responde usando la información del contexto proporcionado.
2. NUNCA inventes información, precios, políticas, fechas o garantías.
3. Si no tienes la información en el contexto, di: "No tengo esa información en mis documentos. ¿Puedes ser más específico?"
4. Si el contexto está vacío, di: "No tengo información sobre eso en mis documentos."
5. SIEMPRE cita o referencia información del contexto cuando sea posible.

**Contexto recuperado (RAG):**
{context[:6000] if context else "⚠️ NO HAY CONTEXTO DISPONIBLE - Solo responde con información que SABES que es correcta o di que no tienes la información."}
{links_context}

**Etapa de venta detectada:** {sales_stage}
**Intención detectada:** {intent}

**Instrucciones CRÍTICAS sobre LINKS de productos:**
- NO incluyas links cuando el usuario solo está explorando ("qué tienen", "muéstrame", "qué venden").
- SÍ incluye links cuando el usuario muestra intención de compra ("quiero", "comprar", "me interesa", "precio").
- SÍ incluye links cuando está en etapa READY o CLOSING.
- En etapa CONSIDERATION, solo incluye links si pregunta específicamente por un producto.

**Otras instrucciones:**
1. Analiza el mensaje del usuario paso a paso.
2. Decide qué herramientas necesitas usar.
3. Si es sobre productos, usa search_products o get_products_with_links (este último incluye links automáticamente).
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
    
    def _should_include_product_links(self, sales_stage: str, intent: str, state: Dict[str, Any]) -> bool:
        """
        Determina si debe incluir links de productos en la respuesta.
        
        Reglas:
        - READY/CLOSING: SIEMPRE incluir links (usuario quiere comprar)
        - CONSIDERATION: Solo si pregunta específicamente por un producto
        - INTEREST: NO incluir links (solo explorando)
        - Si dice "quiero", "comprar", "me interesa": SIEMPRE incluir
        - Si pregunta "qué tienen", "muéstrame": NO incluir links (solo exploración)
        
        Args:
            sales_stage: Etapa de venta (interest, consideration, ready, closing)
            intent: Intención detectada
            state: Estado completo del agente
            
        Returns:
            True si debe incluir links, False si no
        """
        # Etapas donde SIEMPRE incluir links
        if sales_stage in ["ready", "closing"]:
            return True
        
        # Verificar mensaje del usuario para palabras clave de compra
        messages = state.get("messages", [])
        last_user_message = None
        for msg in reversed(messages):
            if hasattr(msg, 'content') and isinstance(msg.content, str):
                last_user_message = msg.content.lower()
                break
        
        if last_user_message:
            # Palabras que indican intención de compra -> INCLUIR LINKS
            purchase_keywords = [
                "quiero", "comprar", "me interesa", "dame", "necesito comprar",
                "precio de", "cuánto cuesta", "agregar al carrito", "añadir"
            ]
            if any(keyword in last_user_message for keyword in purchase_keywords):
                return True
            
            # Palabras que indican solo exploración -> NO INCLUIR LINKS
            exploration_keywords = [
                "qué tienen", "qué venden", "muéstrame", "muéstrenme",
                "qué productos", "catálogo", "listado", "opciones"
            ]
            if any(keyword in last_user_message for keyword in exploration_keywords):
                return False
        
        # CONSIDERATION: Solo si pregunta específicamente por un producto
        if sales_stage == "consideration":
            # Si pregunta por características específicas de un producto, incluir link
            if last_user_message and any(word in last_user_message for word in ["este", "ese", "ese producto", "este producto"]):
                return True
            return False
        
        # INTEREST: NO incluir links por defecto
        return False
    
    def _get_link_instructions(self, sales_stage: str, intent: str, should_include: bool) -> str:
        """
        Genera instrucciones específicas sobre cuándo incluir links.
        
        Args:
            sales_stage: Etapa de venta
            intent: Intención detectada
            should_include: Si debe incluir links
            
        Returns:
            Instrucciones en texto
        """
        if should_include:
            return f"""
- El usuario está en etapa {sales_stage.upper()} y muestra intención de compra.
- SIEMPRE incluye links a productos en formato Markdown: [Ver producto](url) o [Comprar ahora](url).
- Haz los links clickeables y atractivos.
- Si hay múltiples productos, incluye link a cada uno."""
        else:
            return f"""
- El usuario está en etapa {sales_stage.upper()} y solo está explorando.
- NO incluyas links de productos todavía.
- Solo menciona los productos sin links.
- Si el usuario muestra interés real, entonces sí incluye links."""
    
    def _build_observation_context(self, tool_results: Dict[str, Any], include_links: bool = True) -> str:
        """
        Construye contexto de observación desde resultados de herramientas.
        
        Args:
            tool_results: Resultados de herramientas ejecutadas
            include_links: Si debe incluir links en el contexto (default: True)
        """
        context_parts = []
        
        if "products" in tool_results:
            products = tool_results["products"]
            products_list = []
            if hasattr(products, 'products'):
                products_list = products.products
            elif isinstance(products, dict) and "products" in products:
                products_list = products["products"]
            elif isinstance(products, list):
                products_list = products
            
            # Formatear productos con o sin links según include_links
            product_info = []
            for p in products_list[:5]:
                if isinstance(p, dict):
                    title = p.get('title', p.get('name', 'Product'))
                    price = p.get('price', 0)
                    link = p.get('url', None)
                    if include_links and link:
                        product_info.append(f"- {title}: ${price:.2f} [Ver producto]({link})")
                    else:
                        product_info.append(f"- {title}: ${price:.2f}")
                elif hasattr(p, 'title'):
                    title = p.title
                    price = p.price if hasattr(p, 'price') else 0
                    link = p.url if hasattr(p, 'url') and p.url else None
                    if include_links and link:
                        product_info.append(f"- {title}: ${price:.2f} [Ver producto]({link})")
                    else:
                        product_info.append(f"- {title}: ${price:.2f}")
            
            if product_info:
                context_parts.append(f"Productos encontrados ({len(products_list)}):\n" + "\n".join(product_info))
            else:
                context_parts.append(f"Productos encontrados: {len(products_list)}")
        
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
        state: Optional[Dict[str, Any]] = None,
        lead_score: int = 0,
        lead_temperature: str = "cold",
        clear_intent: str = "explorando",
        personalization: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Construye prompt de cierre optimizado para widget.
        
        Args:
            sales_stage: Etapa de venta
            intent: Intención detectada
            tool_results: Resultados de herramientas
            context: Contexto recuperado
            closing_strategy: Estrategia de cierre
            state: Estado completo del agente (para determinar si incluir links)
            lead_score: Score del lead (0-100)
            lead_temperature: Temperatura del lead (cold, warm, hot)
            clear_intent: Intención clara detectada
            personalization: Datos de personalización
        """
        # FASE 1: Usar personalización del estado si está disponible
        if personalization is None:
            personalization = state.get("personalization", {}) if state else {}
        
        # FASE 1: Construir contexto unificado (sin fragmentación)
        unified_context_parts = []
        
        # 1. Contexto RAG (prioritario)
        if context:
            unified_context_parts.append(f"**CONTEXTO DE DOCUMENTOS (RAG):**\n{context[:8000]}")
        
        # 2. Personalización y memoria conversacional
        personalization_context = ""
        products_mentioned = personalization.get("products_mentioned", [])
        talla = personalization.get("talla")
        color = personalization.get("color")
        
        if products_mentioned or talla or color:
            personalization_context = "\n\n**PERSONALIZACIÓN DEL CLIENTE:**\n"
            if products_mentioned:
                personalization_context += f"- Productos mencionados anteriormente: {', '.join(set(products_mentioned))}\n"
            if talla:
                personalization_context += f"- Talla preferida: {talla}\n"
            if color:
                personalization_context += f"- Color preferido: {color}\n"
            personalization_context += "- Usa esta información para personalizar tu respuesta."
        
        # 3. Lead Score y Temperatura (para estrategia, NO mencionar al usuario)
        score_context = f"\n\n**INFORMACIÓN INTERNA (NO MENCIONAR):**\n"
        score_context += f"- Lead Score: {lead_score}/100\n"
        score_context += f"- Temperatura: {lead_temperature}\n"
        score_context += f"- Intención clara: {clear_intent}\n"
        score_context += f"- Etapa de venta: {sales_stage}\n"
        if lead_temperature == "hot":
            score_context += "- ⚠️ LEAD CALIENTE: Prioriza cierre de venta y envío de links.\n"
        elif lead_temperature == "warm":
            score_context += "- ⚠️ LEAD TIBIO: Nutre la relación, proporciona información detallada.\n"
        else:
            score_context += "- ⚠️ LEAD FRÍO: Solo información, sin presión de venta.\n"
        
        # 4. Links (solo si debe enviarse)
        links_context = ""
        if state:
            should_include_product_links = self._should_send_link(clear_intent, sales_stage, lead_score, lead_temperature)
            if should_include_product_links:
                # Obtener link según intención
                messages = state.get("messages", [])
                last_user_message = ""
                for msg in reversed(messages):
                    if isinstance(msg, HumanMessage) and hasattr(msg, 'content'):
                        last_user_message = msg.content
                        break
                
                user_intent = self.links_manager.intent_mapper.detect_intent(last_user_message, sales_stage)
                link_for_intent = self.links_manager.format_link_for_intent(user_intent, sales_stage)
                
                if link_for_intent:
                    links_context = f"\n\n**🔗 LINK OBLIGATORIO (DEBES INCLUIRLO):**\n{link_for_intent}\n"
        
        # 5. Recomendaciones (upsell/cross-sell)
        recommendations_context = ""
        if tool_results and "recommendations" in tool_results:
            recommendations = tool_results["recommendations"]
            upsell_list = recommendations.get("upsell", [])
            cross_sell_list = recommendations.get("cross_sell", [])
            
            if upsell_list or cross_sell_list:
                recommendations_context = "\n\n**RECOMENDACIONES DE PRODUCTOS (UPSELL/CROSS-SELL):**\n"
                if upsell_list:
                    recommendations_context += "- **Productos superiores (upsell):**\n"
                    for rec in upsell_list:
                        recommendations_context += f"  • {rec.get('name', 'Producto')} - ${rec.get('price', 0)}\n"
                if cross_sell_list:
                    recommendations_context += "- **Productos complementarios (cross-sell):**\n"
                    for rec in cross_sell_list:
                        recommendations_context += f"  • {rec.get('name', 'Producto')} - ${rec.get('price', 0)}\n"
                recommendations_context += "- Si el lead es warm o hot, PRESENTA estas recomendaciones de forma natural en tu respuesta.\n"
                recommendations_context += "- Ejemplo: 'También tenemos [producto] que va perfecto con [producto actual]' o '¿Te interesa conocer nuestra versión premium?'\n"
        
        # 6. Objeción detectada (si hay)
        objection_context = ""
        objection_detected_state = state.get("objection_detected", False) if state else False
        objection_type_state = state.get("objection_type") if state else None
        if objection_detected_state and objection_type_state and tool_results and "objection" in tool_results:
            objection_data = tool_results["objection"]
            objection_response = objection_data.get("response", "")
            objection_context = f"\n\n**⚠️ OBJECIÓN DETECTADA ({objection_type_state}):**\n"
            objection_context += f"- El cliente expresó una objeción sobre: {objection_type_state}\n"
            objection_context += f"- Respuesta sugerida: {objection_response}\n"
            objection_context += "- DEBES incluir esta respuesta en tu mensaje de forma natural.\n"
            objection_context += "- NO ignores la objeción - abórdala directamente pero con tacto.\n"
        
        # Combinar todo en contexto unificado
        unified_context = "\n".join(unified_context_parts) + personalization_context + score_context + links_context + recommendations_context + objection_context
        
        prompt = f"""
Eres un asistente virtual de ventas para {self.config.brand_name}.

**REGLAS CRÍTICAS - LÉELAS CUIDADOSAMENTE:**
1. SOLO responde usando la información del contexto proporcionado y resultados de herramientas.
2. NUNCA inventes información, precios, políticas, fechas o garantías.
3. Si no tienes la información en el contexto, di: "No tengo esa información en mis documentos. ¿Puedes ser más específico?"
4. SIEMPRE usa información real del contexto recuperado (RAG) y resultados de herramientas.
5. NUNCA menciones información técnica como "etapa de venta", "intención detectada", "relevancia", "score", etc. al usuario.
6. NUNCA digas cosas como "Basándome en la información proporcionada" - habla DIRECTAMENTE.
7. Responde de forma natural y conversacional, como si fueras un vendedor humano experto.
8. Si el contexto contiene información relevante sobre productos, servicios, políticas, etc., ÚSALO en tu respuesta.

**CONTEXTO UNIFICADO (TODO LO QUE NECESITAS):**
{unified_context}

**INFORMACIÓN INTERNA (NO MENCIONAR AL USUARIO):**
- Etapa de venta: {sales_stage}
- Intención: {intent}
- Estrategia de cierre: {closing_strategy.value if closing_strategy else "standard"}

**Resultados de herramientas:**
{json.dumps(tool_results, default=str)[:2000]}

**INSTRUCCIONES CRÍTICAS PARA GENERAR LA RESPUESTA:**

1. **CONTEXTO RAG ES PRIORITARIO**: Si el contexto RAG contiene información sobre productos, servicios, precios, tallas, materiales, colores, MOQ, etc., DEBES INCLUIR TODA ESA INFORMACIÓN en tu respuesta. NO omitas detalles importantes.

2. **INFORMACIÓN COMPLETA DE PRODUCTOS**: Cuando menciones un producto del contexto RAG, incluye:
   - Nombre completo del producto
   - Precio (si está disponible)
   - MOQ (Minimum Order Quantity) si está disponible
   - Tallas/Sizes disponibles
   - Colores disponibles
   - Materiales
   - Personalización disponible
   - País de origen/Fabricación
   - Cualquier otro detalle relevante que esté en el contexto

3. **FORMATO DE RESPUESTA**: 
   - Responde de forma natural y conversacional, como un vendedor humano experto
   - Usa lenguaje claro y directo
   - NO uses frases genéricas como "Parece que estás explorando" o "Basándome en la información"
   - Habla DIRECTAMENTE al cliente: "Tenemos la Agerola T-shirt en color negro..."
   - NO incluyas JSON en tu respuesta - solo texto natural

4. **LINKS (OBLIGATORIO si están disponibles):**
   - Si hay "🔗 LINK OBLIGATORIO" en el contexto unificado, DEBES incluirlo en tu respuesta.
   - Formato: [Texto del link](url) en Markdown.
   - NO elijas links al azar - usa SOLO los links proporcionados.
   - Si el lead es "hot" o la intención es "checkout"/"compra", SIEMPRE incluye links.
   - Si el lead es "cold" y solo está "explorando", NO incluyas links todavía.

5. **MANEJO DE OBJECIONES (CRÍTICO):**
   - Si hay "⚠️ OBJECIÓN DETECTADA" en el contexto, DEBES abordarla DIRECTAMENTE.
   - Usa la respuesta sugerida como guía, pero adaptala de forma natural.
   - NO ignores objeciones - son oportunidades para aclarar dudas y cerrar ventas.
   - Sé empático: "Entiendo tu preocupación sobre [objeción]..."
   - Luego presenta tu respuesta de forma convincente pero honesta.

6. **RECOMENDACIONES (UPSELL/CROSS-SELL):**
   - Si hay "RECOMENDACIONES DE PRODUCTOS" en el contexto, PRESÉNTALAS de forma natural.
   - Solo recomienda si el lead es warm o hot (no a leads fríos).
   - Cross-sell: "Este producto va perfecto con [producto recomendado]"
   - Upsell: "¿Te interesa conocer nuestra versión premium [producto]?"
   - NO seas agresivo - presenta las recomendaciones como sugerencias útiles.

7. **EMPUJAR A DECISIÓN (PROACTIVO):**
   - Si el lead es "hot" (score >= 70), EMPUJA activamente hacia la decisión.
   - Usa CTAs claros: "¿Quieres que lo agreguemos a tu carrito?", "¿Procedemos con el pago?"
   - Si está en etapa READY o CLOSING, incluye un CTA claro con link de checkout.
   - Si el lead es "warm" (score 40-69), nutre la relación pero también invita a acción.
   - Si el lead es "cold" (score < 40), solo proporciona información, sin presión.

8. **OTRAS INSTRUCCIONES:**
   - Si hay payment_link, inclúyelo claramente con CTA: [Pagar ahora](payment_link)
   - Usa la estrategia de cierre {closing_strategy.value if closing_strategy else "standard"}
   - Sé persuasivo pero ético
   - Responde como un vendedor humano experto que CONOCE sus productos
   - Si el contexto tiene información detallada, ÚSALA TODA - no resumas innecesariamente

**EJEMPLOS DE BUENAS RESPUESTAS:**

Ejemplo 1 (producto específico):
"¡Perfecto! Tenemos la Agerola T-shirt en color negro. Está disponible en tallas S, M, L, XL, XXL. El precio es desde 27,90 € (con pedidos de 100 unidades, MOQ: 15/49/100 pcs, precios: 30€/28,50€/27,90€). Está hecha 100% algodón, hecha en Italia por Giulio M. en Milano. Puedes personalizarla con etiquetas y colores. ¿Qué talle necesitas?"

Ejemplo 2 (catálogo general):
"Tenemos una excelente colección de ropa para hombre. Entre nuestros productos destacados están: Agerola T-shirt (desde 27,90€, 100% algodón, tallas S-XXL), Tagliamento Corset (hecho en Italia, personalizable), y más. ¿Hay algún producto específico que te interese?"

Ejemplo 3 (pregunta sobre detalles):
"Sí, la Agerola T-shirt está disponible en las siguientes tallas: S, M, L, XL, XXL. El material es 100% algodón y puedes elegir entre 3+ colores. El precio depende de la cantidad: 30€ para 15 unidades, 28,50€ para 49 unidades, y 27,90€ para 100 unidades o más. ¿Cuántas unidades necesitas?"

**REGLAS ABSOLUTAS:**
- NUNCA digas "Parece que", "Basándome en", "Según la información" - habla DIRECTAMENTE
- SIEMPRE incluye TODOS los detalles del producto que estén en el contexto
- NO resumas innecesariamente - da información completa
- Responde como si fueras un vendedor experto que CONOCE sus productos de memoria

Genera la respuesta final. Habla DIRECTAMENTE al cliente usando TODA la información relevante del contexto RAG. Responde en texto natural, NO en JSON.
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
            # FASE 1: Lead Scoring y Métricas (inicializados)
            "lead_score": 0,
            "lead_temperature": "cold",
            "clear_intent": "explorando",
            "metrics": {
                "intent_detected": "explorando",
                "score_current": 0,
                "temperature": "cold",
                "link_shown": False,
                "link_clicked": False,
            },
            "personalization": {
                "products_mentioned": [],
                "talla": None,
                "color": None,
                "last_strong_intent": None,
            },
            "events": [],
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
        
        # Limpiar respuesta final: eliminar JSON si aparece
        import re
        # Buscar y eliminar bloques JSON que puedan aparecer en la respuesta
        if response_text.strip().startswith('{') or '"response_draft"' in response_text or '"ready_to_respond"' in response_text:
            # Intentar extraer texto útil de JSON
            match = re.search(r'"response_draft"\s*:\s*"([^"]+(?:\\.[^"]*)*)"', response_text, re.DOTALL)
            if match:
                response_text = match.group(1).replace('\\"', '"').replace('\\n', '\n')
            else:
                # Si la respuesta completa parece JSON, intentar extraer cualquier texto útil
                match = re.search(r'"[^"]+"\s*:\s*"([^"]+)"', response_text)
                if match:
                    response_text = match.group(1)
                else:
                    # Eliminar bloques JSON completos pero mantener el texto fuera de ellos
                    response_text = re.sub(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', '', response_text)
        
        # Limpiar espacios múltiples y saltos de línea innecesarios
        response_text = re.sub(r'\s+', ' ', response_text).strip()
        
        # Si la respuesta está vacía o es muy corta después de limpiar, usar draft_answer
        if len(response_text) < 20:
            draft_answer = final_state.get("draft_answer", "")
            if draft_answer:
                response_text = draft_answer
        
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
