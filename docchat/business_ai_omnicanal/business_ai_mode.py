"""Business AI Omnicanal - Modo principal.

Agente unificado de ventas + soporte 24/7 para todos los canales.
"""

from __future__ import annotations

from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends

from langchain_core.language_models import BaseLanguageModel
from langchain_openai import ChatOpenAI

from ..config import AppConfig, load_config
from ..commerce.product_catalog import ProductCatalog
from ..commerce.cart_manager import CartManager
from ..commerce.payment_processor import PaymentProcessor
from .state.customer_session import CustomerSessionManager
from .sentiment.sentiment_analyzer import SentimentAnalyzer
from .tools.catalog_tool import CatalogTool
from .tools.cart_tool import CartTool
from .tools.payment_tool import PaymentTool
from .tools.order_tool import OrderTool
from .tools.support_tool import SupportTool
from .agents.business_ai_agent import BusinessAIAgent, BusinessAIConfig
from .channels.base import ChannelMessage, BaseChannelAdapter


class WebChannelAdapter(BaseChannelAdapter):
    channel_name = "web"

    def to_internal(self, raw_payload: Dict[str, Any]) -> ChannelMessage:
        return ChannelMessage(
            session_id=str(raw_payload.get("session_id") or raw_payload.get("user_id") or "anon_web"),
            channel=self.channel_name,
            user_id=str(raw_payload.get("user_id") or "anon"),
            content=str(raw_payload.get("message") or ""),
            metadata={
                "display_name": raw_payload.get("display_name"),
                "language": raw_payload.get("language", "es"),
            },
        )


class BusinessAIMode:
    """Modo principal Business AI Omnicanal."""

    def __init__(self, config: Optional[AppConfig] = None, llm: Optional[BaseLanguageModel] = None) -> None:
        self.config = config or load_config()

        # LLM - Soporte para Groq (Enterprise - Velocidad Extrema)
        if llm is not None:
            self.llm = llm
        else:
            # Prioridad: Groq si está habilitado y configurado
            if self.config.use_groq and self.config.groq_api_key:
                try:
                    from langchain_groq import ChatGroq
                    self.llm = ChatGroq(
                        model=self.config.groq_model or "llama-3.3-70b-versatile",
                        temperature=0.3,
                        groq_api_key=self.config.groq_api_key,
                        max_tokens=2000,
                    )
                    print("✅ Business AI usando Groq (Llama 3.3 70B) - Velocidad <0.5 seg")
                except ImportError:
                    print("⚠️ langchain-groq no instalado. Instala con: pip install langchain-groq")
                    print("⚠️ Usando OpenAI como fallback")
                    if not self.config.openai_api_key:
                        raise ValueError("OPENAI_API_KEY requerida para Business AI Omnicanal")
                    self.llm = ChatOpenAI(
                        model=self.config.agentic_model or "gpt-4o",
                        temperature=0.3,
                        api_key=self.config.openai_api_key,
                        max_tokens=2000,
                    )
                except Exception as e:
                    print(f"⚠️ Error inicializando Groq: {e}. Usando OpenAI como fallback")
                    if not self.config.openai_api_key:
                        raise ValueError("OPENAI_API_KEY requerida para Business AI Omnicanal")
                    self.llm = ChatOpenAI(
                        model=self.config.agentic_model or "gpt-4o",
                        temperature=0.3,
                        api_key=self.config.openai_api_key,
                        max_tokens=2000,
                    )
            else:
                # Fallback a OpenAI
                if not self.config.openai_api_key:
                    raise ValueError("OPENAI_API_KEY requerida para Business AI Omnicanal (o configura GROQ_API_KEY y DOCCHAT_USE_GROQ=true)")
                self.llm = ChatOpenAI(
                    model=self.config.agentic_model or "gpt-4o",
                    temperature=0.3,
                    api_key=self.config.openai_api_key,
                    max_tokens=2000,
                )

        # Estado de sesiones - Soporte para PostgreSQL (memoria de largo plazo)
        if self.config.postgresql_enabled and self.config.postgresql_url:
            try:
                from .state.postgresql_session_manager import PostgreSQLSessionManager
                self.session_manager = PostgreSQLSessionManager(
                    database_url=self.config.postgresql_url,
                    pool_size=self.config.postgresql_pool_size
                )
                print("✅ Business AI usando PostgreSQL - Memoria de largo plazo activa")
            except Exception as e:
                print(f"⚠️ Error inicializando PostgreSQL: {e}. Usando memoria en RAM")
                from .state.customer_session import CustomerSessionManager
                self.session_manager = CustomerSessionManager()
        else:
            from .state.customer_session import CustomerSessionManager
            self.session_manager = CustomerSessionManager()

        # Sentiment
        self.sentiment_analyzer = SentimentAnalyzer(llm=self.llm)

        # Módulos de comercio reutilizados
        self.product_catalog = ProductCatalog(config=self.config)
        self.cart_manager = CartManager(config=self.config)
        self.payment_processor = PaymentProcessor(config=self.config)

        # Wrappers de tools
        self.catalog_tool = CatalogTool(self.product_catalog)
        self.cart_tool = CartTool(self.cart_manager)
        self.payment_tool = PaymentTool(self.payment_processor)
        self.order_tool = OrderTool()
        self.support_tool = SupportTool()

        # Agente principal
        self.agent = BusinessAIAgent(
            llm=self.llm,
            session_manager=self.session_manager,
            sentiment_analyzer=self.sentiment_analyzer,
            catalog_tool=self.catalog_tool,
            cart_tool=self.cart_tool,
            payment_tool=self.payment_tool,
            order_tool=self.order_tool,
            support_tool=self.support_tool,
            config=BusinessAIConfig(brand_name=self.config.app_name if hasattr(self.config, "app_name") else "Your Brand"),
        )

        # Adaptador por defecto (web). Para WhatsApp/IG se pueden añadir otros.
        self.web_adapter = WebChannelAdapter()

    # --- Núcleo de procesamiento ---

    def process_message(self, payload: Dict[str, Any], channel: str = "web") -> Dict[str, Any]:
        """Procesa un mensaje entrante desde cualquier canal soportado.

        Args:
            payload: Dict con datos del mensaje bruto
            channel: Nombre del canal (web, whatsapp, instagram, messenger)
        """
        if channel == "web":
            adapter: BaseChannelAdapter = self.web_adapter
        else:
            # Por ahora usamos el mismo adaptador como fallback
            adapter = self.web_adapter

        internal_msg = adapter.to_internal(payload)
        profile = adapter.to_profile(internal_msg)

        # Obtener/crear sesión
        session = self.session_manager.get_or_create(session_id=internal_msg.session_id, profile=profile)

        # Extraer imagen si viene en el payload (para procesamiento con visión)
        image_data = payload.get("image_data") or payload.get("image")
        if not image_data and "[Image]" in internal_msg.content:
            # Intentar extraer de mensaje si viene en formato [Image] base64
            try:
                parts = internal_msg.content.split("[Image]")
                if len(parts) > 1:
                    image_data = parts[1].strip()
                    # Limpiar mensaje de la parte de imagen
                    internal_msg.content = parts[0].strip() + (parts[2] if len(parts) > 2 else "")
            except:
                pass

        # Pasar al agente principal (con imagen si existe)
        result = self.agent.handle_message(
            session=session, 
            user_message=internal_msg.content,
            image_data=image_data
        )

        # Actualizar sesión (en PostgreSQL si está habilitado)
        self.session_manager.update(session)
        
        # Si hay orden completada, guardar en historial de compras
        if result.get("tools", {}).get("order") and hasattr(self.session_manager, 'save_purchase'):
            try:
                order = result["tools"]["order"]
                cart_data = result.get("tools", {}).get("cart", {})
                products = cart_data.get("items", []) if isinstance(cart_data, dict) else []
                total = sum(
                    item.get("price", 0) * item.get("quantity", 1) 
                    for item in products 
                    if isinstance(item, dict)
                )
                
                self.session_manager.save_purchase(
                    session_id=session.session_id,
                    user_id=session.profile.user_id if session.profile else "unknown",
                    order_id=str(order.get("order_id", "")),
                    products=products,
                    total_amount=float(total)
                )
            except:
                pass  # Si falla, continuar sin guardar

        # Convertir respuesta a formato genérico de canal
        external = adapter.to_external_response(response_text=result["text"], extra={
            "intent": result.get("intent"),
            "sentiment": result.get("sentiment"),
            "frustration_score": result.get("frustration_score"),
            "needs_handoff": result.get("needs_handoff"),
            "cart": result.get("cart"),  # Para actualizar badge en widget
            "user_profile": result.get("user_profile"),  # Perfil inferido
            "tools": result.get("tools"),  # Productos, cross-selling, etc.
        })
        return external

    # --- Integración FastAPI ---

    def get_api_router(self) -> APIRouter:
        router = APIRouter(prefix="/business-ai", tags=["Business AI Omnicanal"])

        @router.post("/chat")
        async def chat(payload: Dict[str, Any]) -> Dict[str, Any]:
            return self.process_message(payload, channel=str(payload.get("channel", "web")))

        return router

    # --- Demo / Gradio (opcional) ---

    def get_gradio_interface(self):  # type: ignore[override]
        try:
            import gradio as gr
        except ImportError as e:
            raise ImportError("Gradio no está instalado. Añade gradio al entorno para usar esta función.") from e

        def _chat_fn(message: str, session_id: str = "demo_session") -> str:
            payload = {"session_id": session_id, "user_id": session_id, "message": message}
            resp = self.process_message(payload, channel="web")
            return str(resp.get("text") or "")

        return gr.Interface(fn=_chat_fn, inputs=["text", "text"], outputs="text", title="Business AI Omnicanal")



