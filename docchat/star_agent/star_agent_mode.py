"""STAR AGENT - Modo principal.

Agente unificado de ventas + soporte 24/7 para todos los canales.
"""

from __future__ import annotations

import os
from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends

from langchain_core.language_models import BaseLanguageModel

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
from .agents.star_agent_agent import StarAgentAgent, StarAgentConfig
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


class StarAgentMode:
    """Modo principal STAR AGENT."""

    def __init__(self, config: Optional[AppConfig] = None, llm: Optional[BaseLanguageModel] = None) -> None:
        self.config = config or load_config()

        # LLM - Soporte para Groq (Enterprise - Velocidad Extrema)
        if llm is not None:
            self.llm = llm
        else:
            # SIEMPRE usar Groq para STAR AGENT (como solicitado)
            groq_api_key = self.config.groq_api_key or os.getenv("GROQ_API_KEY")
            if not groq_api_key:
                raise ValueError("GROQ_API_KEY requerida para STAR AGENT. Configura en .env: GROQ_API_KEY=tu-clave")
            
            try:
                from langchain_groq import ChatGroq
                # SIEMPRE usar Groq 3.3 70B para STAR AGENT
                groq_llm = ChatGroq(
                    model="llama-3.3-70b-versatile",  # SIEMPRE usar este modelo
                    temperature=0.3,
                    groq_api_key=groq_api_key,
                    max_tokens=2000,
                )
                self.llm = groq_llm
                print("✅ STAR AGENT usando Groq (Llama 3.3 70B Versatile) - Velocidad <0.5 seg")
            except ImportError:
                raise ImportError("langchain-groq no está instalado. Instala con: pip install langchain-groq")
            except Exception as e:
                raise ValueError(f"Error inicializando Groq: {e}. Verifica que GROQ_API_KEY sea válida.")

        # Estado de sesiones - Soporte para PostgreSQL (memoria de largo plazo)
        if self.config.postgresql_enabled and self.config.postgresql_url:
            try:
                from .state.postgresql_session_manager import PostgreSQLSessionManager
                self.session_manager = PostgreSQLSessionManager(
                    database_url=self.config.postgresql_url,
                    pool_size=self.config.postgresql_pool_size
                )
                print("✅ STAR AGENT usando PostgreSQL - Memoria de largo plazo activa")
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

        # Agente principal (SIEMPRE usando Groq - sin fallback)
        self.agent = StarAgentAgent(
            llm=self.llm,
            session_manager=self.session_manager,
            sentiment_analyzer=self.sentiment_analyzer,
            catalog_tool=self.catalog_tool,
            cart_tool=self.cart_tool,
            payment_tool=self.payment_tool,
            order_tool=self.order_tool,
            support_tool=self.support_tool,
            config=StarAgentConfig(
                brand_name=self.config.app_name if hasattr(self.config, "app_name") else "Your Brand",
                # Leer personalización desde variables de entorno (configurado en config.py)
                tone=self.config.chatbot_tone if hasattr(self.config, "chatbot_tone") else "friendly",
                personality=self.config.chatbot_personality if hasattr(self.config, "chatbot_personality") else "",
                custom_instructions=self.config.chatbot_custom_instructions if hasattr(self.config, "chatbot_custom_instructions") else "",
            ),
            fallback_llm=None,  # No hay fallback - siempre usamos Groq
            app_config=self.config,  # Pasar AppConfig para RAG y traducción
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
    
    def handle_omnicanal_message(self, incoming_message) -> Dict[str, Any]:
        """
        Procesa un mensaje entrante desde OmnicanalBridge (IncomingMessage).
        
        Args:
            incoming_message: IncomingMessage del OmnicanalBridge
            
        Returns:
            Dict con la respuesta del agente
        """
        try:
            # Mapear canal de OmnicanalBridge a formato interno
            channel_map = {
                "whatsapp": "whatsapp",
                "facebook": "messenger",
                "messenger": "messenger",
                "instagram": "instagram",
                "web": "web"
            }
            channel_name = channel_map.get(incoming_message.channel.value, "web")
            
            # Crear payload para process_message
            payload = {
                "session_id": f"{channel_name}_{incoming_message.sender_id}",
                "user_id": incoming_message.sender_id,
                "message": incoming_message.message_text,
                "channel": channel_name,
                "metadata": incoming_message.metadata or {}
            }
            
            # Procesar con el método existente
            result = self.process_message(payload, channel=channel_name)
            
            return result
        except Exception as e:
            import traceback
            print(f"❌ Error procesando mensaje omnicanal: {e}")
            print(traceback.format_exc())
            return {
                "text": "Lo siento, estoy teniendo problemas para procesar tu mensaje. Por favor, inténtalo de nuevo.",
                "error": str(e)
            }

    # --- Integración FastAPI ---

    def get_api_router(self) -> APIRouter:
        router = APIRouter(prefix="/star-agent", tags=["STAR AGENT"])

        @router.post("/chat")
        async def chat(payload: Dict[str, Any]) -> Dict[str, Any]:
            """Endpoint de chat para STAR AGENT Widget"""
            try:
                response_data = self.process_message(payload, channel=str(payload.get("channel", "web")))
            except Exception as e:
                # Manejar errores y devolver respuesta de error con CORS
                import traceback
                error_detail = str(e)
                print(f"❌ Error procesando mensaje: {error_detail}")
                traceback.print_exc()
                response_data = {
                    "text": f"Lo siento, hubo un error procesando tu mensaje: {error_detail}",
                    "error": True,
                    "error_detail": error_detail
                }
            
            # Los headers CORS ya están manejados por el middleware, pero los agregamos explícitamente
            from fastapi.responses import JSONResponse
            return JSONResponse(
                content=response_data,
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
                    "Access-Control-Allow-Headers": "*",
                }
            )

        # Agregar endpoint OPTIONS para CORS preflight (requerido para file://)
        @router.options("/chat")
        async def chat_options():
            """Handle CORS preflight requests - CRÍTICO para file://"""
            from fastapi.responses import Response
            return Response(
                status_code=200,
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
                    "Access-Control-Allow-Headers": "*",
                    "Access-Control-Max-Age": "3600",
                }
            )

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

        return gr.Interface(fn=_chat_fn, inputs=["text", "text"], outputs="text", title="STAR AGENT")

