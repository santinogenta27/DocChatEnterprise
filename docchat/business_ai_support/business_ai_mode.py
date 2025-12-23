"""Business AI Support - Modo principal.

Agente unificado de soporte al cliente 24/7 para todos los canales.
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
from .tools.crm_tool import CRMTool
from .agents.business_ai_agent import BusinessAIAgent, BusinessAIConfig
from .channels.base import ChannelMessage, BaseChannelAdapter
from .integrations.crm.crm_manager import CRMManager
from .integrations.crm.base import CRMConfig, CRMProvider


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


class BusinessAISupportMode:
    """Modo principal Business AI Support."""

    def __init__(self, config: Optional[AppConfig] = None, llm: Optional[BaseLanguageModel] = None) -> None:
        self.config = config or load_config()

        # LLM - Soporte para Groq (Enterprise - Velocidad Extrema)
        if llm is not None:
            self.llm = llm
        else:
            # SIEMPRE usar Groq para Business AI Support (como solicitado)
            groq_api_key = self.config.groq_api_key or os.getenv("GROQ_API_KEY")
            if not groq_api_key:
                raise ValueError("GROQ_API_KEY requerida para Business AI Support. Configura en .env: GROQ_API_KEY=tu-clave")
            
            try:
                from langchain_groq import ChatGroq
                # SIEMPRE usar Groq 3.3 70B para Business AI Support
                groq_llm = ChatGroq(
                    model="llama-3.3-70b-versatile",  # SIEMPRE usar este modelo
                    temperature=0.3,
                    groq_api_key=groq_api_key,
                    max_tokens=2000,
                )
                self.llm = groq_llm
                print("✅ Business AI usando Groq (Llama 3.3 70B Versatile) - Velocidad <0.5 seg")
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
        
        # Troubleshooting Engine y Internal Scheduler
        try:
            from .troubleshooting.troubleshooting_engine import TroubleshootingEngine
            from .scheduling.internal_scheduler import InternalScheduler
            self.troubleshooting_engine = TroubleshootingEngine(config=self.config)
            self.internal_scheduler = InternalScheduler(config=self.config, session_manager=self.session_manager if hasattr(self.session_manager, 'pool') else None)
        except Exception as e:
            print(f"⚠️ Error inicializando troubleshooting/scheduling: {e}")
            self.troubleshooting_engine = None
            self.internal_scheduler = None
        
        # Notification Manager (Email + Slack)
        try:
            from .notifications.notification_manager import NotificationManager
            # Configuración desde variables de entorno o defaults
            email_config = {
                "smtp_server": os.getenv("SMTP_SERVER", "smtp.gmail.com"),
                "smtp_port": int(os.getenv("SMTP_PORT", "587")),
                "smtp_user": os.getenv("SMTP_USER", ""),
                "smtp_password": os.getenv("SMTP_PASSWORD", ""),
                "from_email": os.getenv("SMTP_FROM_EMAIL", os.getenv("SMTP_USER", "")),
                "to_emails": os.getenv("SMTP_TO_EMAILS", "").split(",") if os.getenv("SMTP_TO_EMAILS") else []
            }
            slack_config = {
                "webhook_url": os.getenv("SLACK_WEBHOOK_URL", "")
            }
            self.notification_manager = NotificationManager(
                email_enabled=bool(email_config.get("smtp_user") and email_config.get("smtp_password")),
                slack_enabled=bool(slack_config.get("webhook_url")),
                email_config=email_config if email_config.get("smtp_user") else None,
                slack_config=slack_config if slack_config.get("webhook_url") else None
            )
            print("✅ Notification Manager inicializado")
        except Exception as e:
            print(f"⚠️ Error inicializando Notification Manager: {e}")
            self.notification_manager = None
        
        # CRM Integration - Deep Integration with Salesforce, HubSpot, Zendesk
        self.crm_manager = self._initialize_crm_manager()
        self.crm_tool = CRMTool(self.crm_manager) if self.crm_manager and self.crm_manager.connectors else None

        # Agente principal (SIEMPRE usando Groq - sin fallback)
        self.agent = BusinessAIAgent(
            llm=self.llm,
            session_manager=self.session_manager,
            sentiment_analyzer=self.sentiment_analyzer,
            catalog_tool=self.catalog_tool,
            cart_tool=self.cart_tool,
            payment_tool=self.payment_tool,
            order_tool=self.order_tool,
            support_tool=self.support_tool,
            crm_tool=self.crm_tool,  # Deep CRM integration
            config=BusinessAIConfig(
                brand_name=self.config.app_name if hasattr(self.config, "app_name") else "Your Brand",
                # Leer personalización desde variables de entorno (configurado en config.py)
                tone=self.config.chatbot_tone if hasattr(self.config, "chatbot_tone") else "friendly",
                personality=self.config.chatbot_personality if hasattr(self.config, "chatbot_personality") else "",
                custom_instructions=self.config.chatbot_custom_instructions if hasattr(self.config, "chatbot_custom_instructions") else "",
            ),
            fallback_llm=None,  # No hay fallback - siempre usamos Groq
            app_config=self.config,  # Pasar AppConfig para RAG y traducción
            troubleshooting_engine=self.troubleshooting_engine,
            internal_scheduler=self.internal_scheduler,
            notification_manager=self.notification_manager,  # Notification system
        )

        # Adaptador por defecto (web). Para WhatsApp/IG se pueden añadir otros.
        self.web_adapter = WebChannelAdapter()

    def _initialize_crm_manager(self) -> Optional[CRMManager]:
        """Initialize CRM Manager with configured CRM connections."""
        crm_configs = []
        
        # Salesforce Configuration
        salesforce_username = os.getenv("SALESFORCE_USERNAME")
        salesforce_password = os.getenv("SALESFORCE_PASSWORD")
        salesforce_security_token = os.getenv("SALESFORCE_SECURITY_TOKEN")
        salesforce_access_token = os.getenv("SALESFORCE_ACCESS_TOKEN")
        salesforce_instance_url = os.getenv("SALESFORCE_INSTANCE_URL")
        
        if salesforce_access_token and salesforce_instance_url:
            # OAuth flow
            crm_configs.append(CRMConfig(
                provider=CRMProvider.SALESFORCE,
                access_token=salesforce_access_token,
                instance_url=salesforce_instance_url,
                permissions=os.getenv("SALESFORCE_PERMISSIONS", "").split(",") if os.getenv("SALESFORCE_PERMISSIONS") else []
            ))
            print("✅ Configuración Salesforce (OAuth) detectada")
        elif salesforce_username and salesforce_password and salesforce_security_token:
            # Username/Password/Token flow
            crm_configs.append(CRMConfig(
                provider=CRMProvider.SALESFORCE,
                username=salesforce_username,
                password=salesforce_password,
                security_token=salesforce_security_token,
                permissions=os.getenv("SALESFORCE_PERMISSIONS", "").split(",") if os.getenv("SALESFORCE_PERMISSIONS") else []
            ))
            print("✅ Configuración Salesforce (Username/Password) detectada")
        
        # HubSpot Configuration
        hubspot_api_key = os.getenv("HUBSPOT_API_KEY")
        hubspot_access_token = os.getenv("HUBSPOT_ACCESS_TOKEN")
        
        if hubspot_access_token:
            crm_configs.append(CRMConfig(
                provider=CRMProvider.HUBSPOT,
                access_token=hubspot_access_token,
                permissions=os.getenv("HUBSPOT_PERMISSIONS", "").split(",") if os.getenv("HUBSPOT_PERMISSIONS") else []
            ))
            print("✅ Configuración HubSpot (OAuth) detectada")
        elif hubspot_api_key:
            crm_configs.append(CRMConfig(
                provider=CRMProvider.HUBSPOT,
                api_key=hubspot_api_key,
                permissions=os.getenv("HUBSPOT_PERMISSIONS", "").split(",") if os.getenv("HUBSPOT_PERMISSIONS") else []
            ))
            print("✅ Configuración HubSpot (API Key) detectada")
        
        # Zendesk Configuration
        zendesk_subdomain = os.getenv("ZENDESK_SUBDOMAIN")
        zendesk_email = os.getenv("ZENDESK_EMAIL")
        zendesk_api_token = os.getenv("ZENDESK_API_TOKEN")
        zendesk_access_token = os.getenv("ZENDESK_ACCESS_TOKEN")
        
        if zendesk_access_token and zendesk_subdomain:
            crm_configs.append(CRMConfig(
                provider=CRMProvider.ZENDESK,
                access_token=zendesk_access_token,
                subdomain=zendesk_subdomain,
                permissions=os.getenv("ZENDESK_PERMISSIONS", "").split(",") if os.getenv("ZENDESK_PERMISSIONS") else []
            ))
            print("✅ Configuración Zendesk (OAuth) detectada")
        elif zendesk_email and zendesk_api_token and zendesk_subdomain:
            crm_configs.append(CRMConfig(
                provider=CRMProvider.ZENDESK,
                username=zendesk_email,
                api_key=zendesk_api_token,
                subdomain=zendesk_subdomain,
                permissions=os.getenv("ZENDESK_PERMISSIONS", "").split(",") if os.getenv("ZENDESK_PERMISSIONS") else []
            ))
            print("✅ Configuración Zendesk (API Token) detectada")
        
        if crm_configs:
            try:
                crm_manager = CRMManager(crm_configs)
                if crm_manager.connectors:
                    print(f"✅ CRM Manager inicializado con {len(crm_manager.connectors)} conectores activos")
                    return crm_manager
            except Exception as e:
                print(f"⚠️ Error inicializando CRM Manager: {e}")
        
        print("ℹ️ No se detectó configuración de CRM. El agente funcionará sin integración CRM.")
        return None

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
        router = APIRouter(prefix="/business-ai-support", tags=["Business AI Support"])

        @router.post("/chat")
        async def chat(payload: Dict[str, Any]) -> Dict[str, Any]:
            """Endpoint de chat para Business AI Support Widget"""
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

        # Endpoint para servir el widget JavaScript
        @router.get("/widget.js")
        async def get_widget_js():
            """Sirve el archivo JavaScript del widget embeddable."""
            from pathlib import Path
            from fastapi.responses import FileResponse
            
            widget_path = Path(__file__).parent / "widget" / "business-ai-widget.js"
            if widget_path.exists():
                return FileResponse(
                    widget_path,
                    media_type="application/javascript",
                    headers={
                        "Access-Control-Allow-Origin": "*",
                        "Cache-Control": "public, max-age=3600"
                    }
                )
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Widget file not found")

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

        return gr.Interface(fn=_chat_fn, inputs=["text", "text"], outputs="text", title="Business AI Support")

















