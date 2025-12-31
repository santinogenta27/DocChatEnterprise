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
        # Cargar configuración base
        base_config = config or load_config()
        
        # Cargar configuración desde UI de Gradio (si existe)
        try:
            from .config.chatbot_config_loader import ChatbotConfigLoader
            config_loader = ChatbotConfigLoader()
            base_config = config_loader.apply_to_config(base_config)
            print("✅ Configuración cargada desde UI de Gradio")
        except Exception as e:
            print(f"⚠️ No se pudo cargar configuración desde UI: {e}")
        
        self.config = base_config

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
        # Para widget web, usar ReactSalesAgent optimizado si está disponible
        use_react_agent = getattr(self.config, "use_react_agent_for_widget", True)
        
        if use_react_agent:
            try:
                from .agents.react_sales_agent import ReactSalesAgent, ReactSalesAgentConfig
                self.react_agent = ReactSalesAgent(
                    llm=self.llm,
                    session_manager=self.session_manager,
                    sentiment_analyzer=self.sentiment_analyzer,
                    catalog_tool=self.catalog_tool,
                    cart_tool=self.cart_tool,
                    payment_tool=self.payment_tool,
                    order_tool=self.order_tool,
                    support_tool=self.support_tool,
                    config=ReactSalesAgentConfig(
                        brand_name=self.config.app_name if hasattr(self.config, "app_name") else "Your Brand",
                        language="es",
                        enable_sales_closer=True,
                        enable_rag_advanced=True,
                        enable_verification=True,
                        base_url=getattr(self.config, "base_url", None) or os.getenv("BASE_URL") or os.getenv("SHOPIFY_SHOP_URL"),  # URL base para links de productos
                    ),
                    app_config=self.config,
                )
                print("✅ ReactSalesAgent inicializado para widget optimizado con ReAct pattern completo")
                self.agent = self.react_agent  # Usar ReactSalesAgent como agente principal
                
                # Inicializar scheduler de ingesta automática si está configurado
                self._init_ingestion_scheduler_from_config()
            except Exception as e:
                print(f"⚠️ Error inicializando ReactSalesAgent: {e}")
                import traceback
                traceback.print_exc()
                use_react_agent = False
        
        if not use_react_agent:
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
        
        # Inicializar adaptadores de canales Meta (WhatsApp, Messenger e Instagram)
        self.whatsapp_adapter = None
        self.messenger_adapter = None
        self.instagram_adapter = None
        
        # Configurar WhatsApp Business API
        whatsapp_enabled = getattr(config, 'enable_whatsapp', False) or os.getenv("ENABLE_WHATSAPP", "false").lower() == "true"
        if whatsapp_enabled:
            try:
                from .channels.whatsapp_adapter import WhatsAppBusinessAdapter
                self.whatsapp_adapter = WhatsAppBusinessAdapter(
                    phone_number_id=getattr(config, 'whatsapp_phone_number_id', None) or os.getenv("WHATSAPP_PHONE_NUMBER_ID"),
                    access_token=getattr(config, 'whatsapp_access_token', None) or os.getenv("WHATSAPP_ACCESS_TOKEN"),
                    verify_token=getattr(config, 'whatsapp_verify_token', None) or os.getenv("WHATSAPP_VERIFY_TOKEN"),
                )
                print("✅ WhatsApp Business API adapter inicializado")
            except Exception as e:
                print(f"⚠️ Error inicializando WhatsApp adapter: {e}")
        
        # Configurar Facebook Messenger
        messenger_enabled = getattr(config, 'enable_messenger', False) or os.getenv("ENABLE_MESSENGER", "false").lower() == "true"
        if messenger_enabled:
            try:
                from .channels.messenger_adapter import MessengerAdapter
                self.messenger_adapter = MessengerAdapter(
                    page_id=getattr(config, 'facebook_page_id', None) or os.getenv("FACEBOOK_PAGE_ID"),
                    access_token=getattr(config, 'facebook_page_access_token', None) or os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN"),
                    verify_token=getattr(config, 'facebook_verify_token', None) or os.getenv("FACEBOOK_VERIFY_TOKEN"),
                )
                print("✅ Facebook Messenger adapter inicializado")
            except Exception as e:
                print(f"⚠️ Error inicializando Messenger adapter: {e}")
        
        # Configurar Instagram Direct (usa MessengerAdapter también)
        instagram_enabled = getattr(config, 'enable_instagram', False) or os.getenv("ENABLE_INSTAGRAM", "false").lower() == "true"
        if instagram_enabled:
            try:
                from .channels.messenger_adapter import MessengerAdapter
                self.instagram_adapter = MessengerAdapter(
                    page_id=getattr(config, 'instagram_page_id', None) or os.getenv("INSTAGRAM_PAGE_ID"),
                    access_token=getattr(config, 'instagram_access_token', None) or os.getenv("INSTAGRAM_ACCESS_TOKEN"),
                    verify_token=getattr(config, 'instagram_verify_token', None) or os.getenv("INSTAGRAM_VERIFY_TOKEN"),
                )
                print("✅ Instagram Direct adapter inicializado")
            except Exception as e:
                print(f"⚠️ Error inicializando Instagram adapter: {e}")
        
        # Inicializar scheduler de ingesta automática (nuevo sistema)
        self.ingestion_scheduler = None
        self._init_ingestion_scheduler_from_config()
        
        # Inicializar sistema de ingesta multi-fuente (opcional - legacy)
        self.multi_source_ingester = None
        # Verificar si RAG avanzado está habilitado (usar getattr para compatibilidad)
        enable_rag_advanced = getattr(config, 'enable_rag_advanced', True)  # Default True para STAR AGENT
        enable_auto_ingestion = getattr(config, 'enable_auto_ingestion', False)  # Default False (opcional)
        
        if enable_rag_advanced and enable_auto_ingestion:
            try:
                from .ingestion.multi_source_ingester import MultiSourceIngester
                from .rag.advanced_rag_manager import AdvancedRAGManager
                
                # Obtener AdvancedRAGManager del agente si está disponible
                advanced_rag = None
                if hasattr(self.agent, 'advanced_rag') and self.agent.advanced_rag:
                    advanced_rag = self.agent.advanced_rag
                elif hasattr(self.agent, 'react_agent') and hasattr(self.agent.react_agent, 'advanced_rag'):
                    advanced_rag = self.agent.react_agent.advanced_rag
                
                if advanced_rag:
                    website_url = getattr(config, 'website_url', None) or os.getenv("WEBSITE_URL")
                    self.multi_source_ingester = MultiSourceIngester(
                        advanced_rag=advanced_rag,
                        website_url=website_url,
                        enable_scheduler=True,  # Scheduler cada 6h
                        enable_webhooks=True,  # Webhooks para nuevos posts
                    )
                    
                    # Iniciar scheduler automático
                    self.multi_source_ingester.start_scheduler()
                    
                    # Ejecutar ingesta inicial
                    print("🔄 Ejecutando ingesta inicial de todas las fuentes...")
                    counts = self.multi_source_ingester.ingest_all_sources()
                    print(f"✅ Sistema de ingesta multi-fuente inicializado")
                    print(f"   - Website: {counts['website']} documentos")
                    print(f"   - Instagram: {counts['instagram']} documentos")
                    print(f"   - Facebook: {counts['facebook']} documentos")
                    print(f"   - Google: {counts['google']} documentos")
                    print(f"   - Scheduler: activo (web cada 6h, redes sociales diario)")
            except Exception as e:
                print(f"⚠️ Error inicializando ingesta multi-fuente: {e}")
                import traceback
                traceback.print_exc()
    
    def _init_ingestion_scheduler_from_config(self):
        """Inicializa el IngestionScheduler desde la configuración."""
        try:
            from .ingestion.ingestion_scheduler import IngestionScheduler
            
            # Obtener configuración de ingesta desde config
            enable_scheduler = getattr(self.config, 'ingestion_scheduler_enabled', False)
            interval_hours = getattr(self.config, 'ingestion_interval_hours', 6)
            enable_website = getattr(self.config, 'ingestion_website_enabled', False)
            website_url = getattr(self.config, 'ingestion_website_url', None)
            enable_instagram = getattr(self.config, 'ingestion_instagram_enabled', False)
            instagram_token = getattr(self.config, 'ingestion_instagram_token', None)
            enable_facebook = getattr(self.config, 'ingestion_facebook_enabled', False)
            facebook_token = getattr(self.config, 'ingestion_facebook_token', None)
            
            # Obtener AdvancedRAGManager del agente si está disponible
            advanced_rag = None
            if hasattr(self, 'agent') and self.agent:
                if hasattr(self.agent, 'advanced_rag') and self.agent.advanced_rag:
                    advanced_rag = self.agent.advanced_rag
                elif hasattr(self.agent, 'react_agent') and hasattr(self.agent.react_agent, 'advanced_rag'):
                    advanced_rag = self.agent.react_agent.advanced_rag
            
            # Inicializar IngestionScheduler
            self.ingestion_scheduler = IngestionScheduler(
                enabled=enable_scheduler,
                interval_hours=interval_hours,
                website_enabled=enable_website,
                website_url=website_url,
                instagram_enabled=enable_instagram,
                instagram_token=instagram_token,
                facebook_enabled=enable_facebook,
                facebook_token=facebook_token,
                rag_manager=advanced_rag
            )
            
            # El scheduler se inicia automáticamente si enabled=True
            if enable_scheduler and self.ingestion_scheduler:
                print("✅ IngestionScheduler inicializado y activo")
        except Exception as e:
            print(f"⚠️ Error inicializando IngestionScheduler: {e}")
            import traceback
            traceback.print_exc()
            self.ingestion_scheduler = None

    # --- Núcleo de procesamiento ---

    def process_message(self, payload: Dict[str, Any], channel: str = "web") -> Dict[str, Any]:
        """Procesa un mensaje entrante desde cualquier canal soportado.

        Args:
            payload: Dict con datos del mensaje bruto
            channel: Nombre del canal (web, whatsapp, instagram, messenger)
        """
        # Seleccionar adapter según el canal
        if channel == "web":
            adapter: BaseChannelAdapter = self.web_adapter
        elif channel == "whatsapp":
            # Usar adapter de WhatsApp si está configurado
            if hasattr(self, 'whatsapp_adapter') and self.whatsapp_adapter:
                adapter = self.whatsapp_adapter
            else:
                # Fallback a web adapter si WhatsApp no está configurado
                adapter = self.web_adapter
        elif channel in ["instagram", "messenger"]:
            # Instagram y Messenger usan MessengerAdapter
            if hasattr(self, 'instagram_adapter') and self.instagram_adapter:
                adapter = self.instagram_adapter
            elif hasattr(self, 'messenger_adapter') and self.messenger_adapter:
                adapter = self.messenger_adapter
            else:
                # Fallback a web adapter si no está configurado
                adapter = self.web_adapter
        else:
            # Fallback por defecto
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
        # Si es ReactSalesAgent, usar método process() optimizado para widget
        if hasattr(self.agent, 'process') and callable(getattr(self.agent, 'process')):
            # ReactSalesAgent - optimizado para widget con ReAct pattern
            payload_for_react = {
                "session_id": session.session_id,
                "user_id": session.profile.user_id if session.profile else "anonymous",
                "message": internal_msg.content,
                "channel": channel,
            }
            result = self.agent.process(payload_for_react)
            
            # Convertir resultado de ReactSalesAgent a formato esperado
            result = {
                "text": result.get("text", ""),
                "intent": result.get("intent", "general"),
                "sales_stage": result.get("sales_stage", "interest"),
                "needs_handoff": result.get("needs_handoff", False),
                "cart": result.get("cart", {}),
                "sentiment": "neutral",  # ReactSalesAgent maneja esto internamente
                "frustration_score": 0.0,
            }
        else:
            # StarAgentAgent - método tradicional
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

    # --- Integración FastAPI y Widget Optimizer ---
    
    def get_widget_app(self):
        """
        Crea aplicación FastAPI optimizada para widget web.
        
        Returns:
            FastAPI app con endpoints optimizados para widget
        """
        try:
            from .widget import create_widget_app
            from pathlib import Path
            import os
            
            # Directorio de archivos estáticos (business-ai-widget.js)
            # Intentar varias rutas posibles
            current_file = Path(__file__).resolve()
            static_dir = None
            
            # Ruta 1: Desde el directorio actual de trabajo (donde se ejecuta el script)
            import os
            cwd = Path(os.getcwd())
            possible_paths = [
                cwd / "docchat" / "static",  # Desde directorio de trabajo
                current_file.parent.parent.parent / "static",  # docchat/static (relativa al archivo)
                Path("docchat/static").resolve(),  # Ruta relativa resuelta
            ]
            
            for path in possible_paths:
                path_resolved = path.resolve() if hasattr(path, 'resolve') else Path(path).resolve()
                js_file = path_resolved / "business-ai-widget.js"
                if path_resolved.exists() and js_file.exists():
                    static_dir = path_resolved
                    print(f"✅ Archivos estáticos encontrados en: {static_dir}")
                    break
            
            if not static_dir:
                print(f"⚠️ No se encontró directorio de archivos estáticos.")
                print(f"   Rutas probadas: {[str(p) for p in possible_paths]}")
                print(f"   CWD: {os.getcwd()}")
                print(f"   Current file: {current_file}")
            
            return create_widget_app(self, static_dir=static_dir)
        except ImportError as e:
            print(f"⚠️ No se pudo crear widget app: {e}")
            import traceback
            traceback.print_exc()
            return None
        except Exception as e:
            print(f"⚠️ Error creando widget app: {e}")
            import traceback
            traceback.print_exc()
            return None

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
        """
        Retorna interfaz de Gradio para STAR AGENT.
        
        Incluye:
        - Chat con el agente
        - Panel de configuración completo
        - Métricas y analytics
        """
        try:
            import gradio as gr
        except ImportError as e:
            raise ImportError("Gradio no está instalado. Añade gradio al entorno para usar esta función.") from e

        # Importar UI de configuración
        try:
            from .ui.gradio_config_ui import StarAgentConfigUI
            config_ui = StarAgentConfigUI(star_agent_mode=self)  # Pasar instancia de StarAgentMode
        except Exception as e:
            print(f"⚠️ Error cargando UI de configuración: {e}")
            config_ui = None

        # Crear interfaz principal con tabs
        with gr.Blocks(
            theme=gr.themes.Soft(),
            title="⭐ STAR AGENT - Asistente Virtual 24/7",
            css="""
            .gradio-container {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }
            """
        ) as demo:
            gr.Markdown("""
            # ⭐ STAR AGENT - Asistente Virtual 24/7
            
            Tu asistente virtual inteligente para ventas y soporte. Configura todo desde aquí.
            """)
            
            with gr.Tabs() as main_tabs:
                # TAB 1: Chat con el Agente
                with gr.Tab("💬 Chat"):
                    gr.Markdown("### Prueba tu Agente")
                    
                    chatbot = gr.Chatbot(
                        label="Conversación",
                        height=500,
                        show_copy_button=True
                    )
                    
                    with gr.Row():
                        msg = gr.Textbox(
                            label="Escribe tu mensaje",
                            placeholder="Ej: ¿Cuánto cuesta el producto X?",
                            scale=4
                        )
                        submit_btn = gr.Button("Enviar", variant="primary", scale=1)
                    
                    clear_btn = gr.Button("🗑️ Limpiar Conversación", variant="secondary")
                    
                    session_id_input = gr.Textbox(
                        label="Session ID (opcional)",
                        value="demo_session",
                        visible=False
                    )
                    
                    def chat_fn(message, history, session_id):
                        """Función de chat."""
                        if not message:
                            return history, ""
                        
                        payload = {
                            "session_id": session_id or "demo_session",
                            "user_id": session_id or "demo_session",
                            "message": message,
                            "channel": "web"
                        }
                        
                        try:
                            resp = self.process_message(payload, channel="web")
                            response_text = resp.get("text", "Lo siento, no pude generar una respuesta.")
                            
                            # Agregar a historial
                            history.append([message, response_text])
                            
                            return history, ""
                        except Exception as e:
                            error_msg = f"Error: {str(e)}"
                            history.append([message, error_msg])
                            return history, ""
                    
                    msg.submit(chat_fn, [msg, chatbot, session_id_input], [chatbot, msg])
                    submit_btn.click(chat_fn, [msg, chatbot, session_id_input], [chatbot, msg])
                    clear_btn.click(lambda: ([], ""), outputs=[chatbot, msg])
                
                # TAB 2: Configuración
                with gr.Tab("⚙️ Configuración"):
                    if config_ui:
                        # Integrar UI de configuración
                        config_demo = config_ui.create_ui()
                        # Copiar componentes de config_ui a este tab
                        # Por ahora, redirigir a la UI de configuración
                        gr.Markdown("### Panel de Configuración Completo")
                        gr.Markdown("""
                        **Configura desde aquí:**
                        - Chatbot básico (tone, personality, instructions)
                        - Ingesta automática (web, Instagram, Facebook, Google)
                        - RAG y documentos
                        - Sales Closer Elite
                        - Integraciones (Stripe, Analytics)
                        - Canales (Widget, WhatsApp, Messenger)
                        - Métricas y analytics
                        """)
                        
                        # Crear UI de configuración inline
                        with gr.Accordion("🤖 Chatbot Básico", open=True):
                            brand_name = gr.Textbox(
                                label="Nombre de tu Empresa",
                                value="",
                                placeholder="Ej: Mi Tienda Online"
                            )
                            chatbot_tone = gr.Dropdown(
                                label="Tono",
                                choices=["friendly", "professional", "casual", "formal", "enthusiastic"],
                                value="friendly"
                            )
                        
                        with gr.Accordion("📥 Ingesta Automática", open=False):
                            enable_auto_ingestion = gr.Checkbox(label="Habilitar Ingesta Automática", value=False)
                            website_url = gr.Textbox(label="URL del Sitio Web", placeholder="https://tu-empresa.com")
                            enable_instagram = gr.Checkbox(label="Habilitar Instagram", value=False)
                            instagram_token = gr.Textbox(label="Instagram Token", type="password")
                            enable_facebook = gr.Checkbox(label="Habilitar Facebook", value=False)
                            facebook_token = gr.Textbox(label="Facebook Token", type="password")
                        
                        save_config_btn = gr.Button("💾 Guardar Configuración", variant="primary")
                        config_status = gr.Textbox(label="Estado", interactive=False)
                        
                        def save_config_fn(
                            brand, tone,
                            auto_ingest, web_url,
                            ig_enable, ig_token,
                            fb_enable, fb_token
                        ):
                            """Guarda configuración."""
                            try:
                                from .ui.gradio_config_ui import StarAgentConfigUI
                                ui = StarAgentConfigUI()
                                config = {
                                    "brand_name": brand,
                                    "chatbot_tone": tone,
                                    "enable_auto_ingestion": auto_ingest,
                                    "website_url": web_url,
                                    "enable_instagram": ig_enable,
                                    "instagram_access_token": ig_token,
                                    "enable_facebook": fb_enable,
                                    "facebook_access_token": fb_token,
                                }
                                success, msg = ui._save_config(config)
                                
                                # Aplicar configuración al agente en tiempo real
                                if success:
                                    # Recargar configuración en el agente
                                    self.config.app_name = brand
                                    self.config.chatbot_tone = tone
                                    self.config.enable_auto_ingestion = auto_ingest
                                    self.config.website_url = web_url
                                    
                                    return f"✅ {msg}. Configuración aplicada al agente."
                                else:
                                    return f"❌ {msg}"
                            except Exception as e:
                                return f"❌ Error: {e}"
                        
                        save_config_btn.click(
                            save_config_fn,
                            inputs=[brand_name, chatbot_tone, enable_auto_ingestion, website_url,
                                   enable_instagram, instagram_token, enable_facebook, facebook_token],
                            outputs=[config_status]
                        )
                    else:
                        gr.Markdown("⚠️ UI de configuración no disponible. Instala dependencias.")
                
                # TAB 3: WhatsApp & Instagram
                with gr.Tab("📱 WhatsApp & Instagram"):
                    gr.Markdown("### Configuración de Canales Sociales")
                    gr.Markdown("""
                    **Conecta tu agente con WhatsApp Business e Instagram Direct**
                    
                    Tu agente STAR AGENT puede responder automáticamente a mensajes recibidos en:
                    - 💬 WhatsApp Business API
                    - 📷 Instagram Direct Messages
                    """)
                    
                    with gr.Tabs() as social_tabs:
                        # WhatsApp Tab
                        with gr.Tab("💬 WhatsApp Business"):
                            gr.Markdown("### Configuración WhatsApp Business API")
                            
                            with gr.Accordion("📋 Requisitos Previos", open=False):
                                gr.Markdown("""
                                **Antes de configurar, necesitas:**
                                1. Una cuenta de WhatsApp Business API (Meta Business)
                                2. Un número de teléfono verificado
                                3. Access Token de WhatsApp Business API
                                4. Phone Number ID de tu cuenta
                                5. Verify Token (puedes usar uno personalizado)
                                
                                **Guía:** https://developers.facebook.com/docs/whatsapp/cloud-api/get-started
                                """)
                            
                            whatsapp_enabled = gr.Checkbox(
                                label="✅ Habilitar WhatsApp Business",
                                value=False,
                                info="Activa/desactiva la integración con WhatsApp"
                            )
                            
                            with gr.Row():
                                whatsapp_phone_id = gr.Textbox(
                                    label="Phone Number ID",
                                    placeholder="Ej: 123456789012345",
                                    info="ID del número de teléfono de WhatsApp Business"
                                )
                                whatsapp_access_token = gr.Textbox(
                                    label="Access Token",
                                    type="password",
                                    placeholder="EAAxxxxxxxxxxxx",
                                    info="Access Token de WhatsApp Business API"
                                )
                            
                            whatsapp_verify_token = gr.Textbox(
                                label="Verify Token",
                                value="star_agent_whatsapp_verify",
                                info="Token personalizado para verificar webhooks (configúralo en Meta)"
                            )
                            
                            whatsapp_webhook_url = gr.Textbox(
                                label="Webhook URL",
                                value="",
                                interactive=False,
                                info="URL del webhook (se generará automáticamente)"
                            )
                            
                            with gr.Row():
                                save_whatsapp_btn = gr.Button("💾 Guardar Configuración WhatsApp", variant="primary")
                                test_whatsapp_btn = gr.Button("🧪 Probar Conexión", variant="secondary")
                            
                            whatsapp_status = gr.Textbox(
                                label="Estado",
                                interactive=False,
                                value="No configurado"
                            )
                            
                            def save_whatsapp_config(enabled, phone_id, access_token, verify_token):
                                """Guarda configuración de WhatsApp."""
                                try:
                                    if not enabled:
                                        return "⚠️ WhatsApp deshabilitado. Habilítalo para guardar configuración."
                                    
                                    if not phone_id or not access_token:
                                        return "❌ Phone Number ID y Access Token son requeridos"
                                    
                                    # Guardar en variables de entorno o configuración
                                    os.environ["WHATSAPP_PHONE_NUMBER_ID"] = phone_id
                                    os.environ["WHATSAPP_ACCESS_TOKEN"] = access_token
                                    os.environ["WHATSAPP_VERIFY_TOKEN"] = verify_token or "star_agent_whatsapp_verify"
                                    
                                    # Guardar en configuración
                                    if hasattr(self.config, 'whatsapp_phone_number_id'):
                                        self.config.whatsapp_phone_number_id = phone_id
                                    if hasattr(self.config, 'whatsapp_access_token'):
                                        self.config.whatsapp_access_token = access_token
                                    
                                    # Inicializar adapter
                                    try:
                                        from .channels.whatsapp_adapter import WhatsAppBusinessAdapter
                                        self.whatsapp_adapter = WhatsAppBusinessAdapter(
                                            phone_number_id=phone_id,
                                            access_token=access_token,
                                            verify_token=verify_token
                                        )
                                        
                                        # Generar webhook URL (necesitarías el dominio/host público)
                                        webhook_base = os.getenv("WEBHOOK_BASE_URL", "https://tu-dominio.com")
                                        webhook_url = f"{webhook_base}/webhooks/meta/whatsapp"
                                        
                                        return f"✅ Configuración guardada. Webhook URL: {webhook_url}\n\n⚠️ Configura este URL en Meta Business Suite > Webhooks"
                                    except Exception as e:
                                        return f"⚠️ Configuración guardada pero error inicializando adapter: {e}"
                                    
                                except Exception as e:
                                    return f"❌ Error: {e}"
                            
                            def test_whatsapp_connection(enabled, phone_id, access_token):
                                """Prueba conexión con WhatsApp."""
                                try:
                                    if not enabled or not phone_id or not access_token:
                                        return "⚠️ Configura primero Phone Number ID y Access Token"
                                    
                                    from .channels.whatsapp_adapter import WhatsAppBusinessAdapter
                                    adapter = WhatsAppBusinessAdapter(
                                        phone_number_id=phone_id,
                                        access_token=access_token
                                    )
                                    
                                    # Intentar obtener info del número (prueba de conexión)
                                    import requests
                                    url = f"{adapter.base_url}/{phone_id}"
                                    headers = {"Authorization": f"Bearer {access_token}"}
                                    response = requests.get(url, headers=headers, timeout=10)
                                    
                                    if response.status_code == 200:
                                        data = response.json()
                                        return f"✅ Conexión exitosa!\n\nNúmero: {data.get('display_phone_number', 'N/A')}\nVerificado: {data.get('verified_name', 'N/A')}"
                                    else:
                                        return f"❌ Error de conexión: {response.status_code} - {response.text}"
                                        
                                except Exception as e:
                                    return f"❌ Error probando conexión: {e}"
                            
                            save_whatsapp_btn.click(
                                save_whatsapp_config,
                                inputs=[whatsapp_enabled, whatsapp_phone_id, whatsapp_access_token, whatsapp_verify_token],
                                outputs=[whatsapp_status]
                            )
                            
                            test_whatsapp_btn.click(
                                test_whatsapp_connection,
                                inputs=[whatsapp_enabled, whatsapp_phone_id, whatsapp_access_token],
                                outputs=[whatsapp_status]
                            )
                        
                        # Instagram Tab
                        with gr.Tab("📷 Instagram Direct"):
                            gr.Markdown("### Configuración Instagram Direct Messages")
                            
                            with gr.Accordion("📋 Requisitos Previos", open=False):
                                gr.Markdown("""
                                **Antes de configurar, necesitas:**
                                1. Una cuenta de Instagram Business o Creator
                                2. Una página de Facebook conectada
                                3. Instagram Graph API habilitada en Meta for Developers
                                4. Access Token con permisos: `instagram_basic`, `instagram_manage_messages`, `pages_messaging`
                                5. Page Access Token de la página de Facebook conectada
                                
                                **Guía:** https://developers.facebook.com/docs/instagram-platform/instagram-api-with-facebook-login
                                """)
                            
                            instagram_enabled = gr.Checkbox(
                                label="✅ Habilitar Instagram Direct",
                                value=False,
                                info="Activa/desactiva la integración con Instagram Direct"
                            )
                            
                            with gr.Row():
                                instagram_page_id = gr.Textbox(
                                    label="Page ID",
                                    placeholder="Ej: 123456789012345",
                                    info="ID de la página de Facebook conectada a Instagram"
                                )
                                instagram_access_token = gr.Textbox(
                                    label="Page Access Token",
                                    type="password",
                                    placeholder="EAAxxxxxxxxxxxx",
                                    info="Page Access Token con permisos de Instagram"
                                )
                            
                            instagram_verify_token = gr.Textbox(
                                label="Verify Token",
                                value="star_agent_instagram_verify",
                                info="Token personalizado para verificar webhooks"
                            )
                            
                            instagram_webhook_url = gr.Textbox(
                                label="Webhook URL",
                                value="",
                                interactive=False,
                                info="URL del webhook (se generará automáticamente)"
                            )
                            
                            with gr.Row():
                                save_instagram_btn = gr.Button("💾 Guardar Configuración Instagram", variant="primary")
                                test_instagram_btn = gr.Button("🧪 Probar Conexión", variant="secondary")
                            
                            instagram_status = gr.Textbox(
                                label="Estado",
                                interactive=False,
                                value="No configurado"
                            )
                            
                            def save_instagram_config(enabled, page_id, access_token, verify_token):
                                """Guarda configuración de Instagram."""
                                try:
                                    if not enabled:
                                        return "⚠️ Instagram deshabilitado. Habilítalo para guardar configuración."
                                    
                                    if not page_id or not access_token:
                                        return "❌ Page ID y Access Token son requeridos"
                                    
                                    # Guardar en variables de entorno
                                    os.environ["INSTAGRAM_PAGE_ID"] = page_id
                                    os.environ["INSTAGRAM_ACCESS_TOKEN"] = access_token
                                    os.environ["INSTAGRAM_VERIFY_TOKEN"] = verify_token or "star_agent_instagram_verify"
                                    
                                    # Guardar en configuración
                                    if hasattr(self.config, 'instagram_page_id'):
                                        self.config.instagram_page_id = page_id
                                    if hasattr(self.config, 'instagram_access_token'):
                                        self.config.instagram_access_token = access_token
                                    
                                    # Inicializar adapter (Instagram usa Messenger API)
                                    try:
                                        from .channels.messenger_adapter import MessengerAdapter
                                        self.instagram_adapter = MessengerAdapter(
                                            page_id=page_id,
                                            access_token=access_token,
                                            verify_token=verify_token
                                        )
                                        
                                        # Generar webhook URL
                                        webhook_base = os.getenv("WEBHOOK_BASE_URL", "https://tu-dominio.com")
                                        webhook_url = f"{webhook_base}/webhooks/meta/messenger"
                                        
                                        return f"✅ Configuración guardada. Webhook URL: {webhook_url}\n\n⚠️ Configura este URL en Meta for Developers > Webhooks"
                                    except Exception as e:
                                        return f"⚠️ Configuración guardada pero error inicializando adapter: {e}"
                                    
                                except Exception as e:
                                    return f"❌ Error: {e}"
                            
                            def test_instagram_connection(enabled, page_id, access_token):
                                """Prueba conexión con Instagram."""
                                try:
                                    if not enabled or not page_id or not access_token:
                                        return "⚠️ Configura primero Page ID y Access Token"
                                    
                                    # Intentar obtener info de la página
                                    import requests
                                    url = f"https://graph.facebook.com/v18.0/{page_id}"
                                    params = {
                                        "access_token": access_token,
                                        "fields": "name,instagram_business_account"
                                    }
                                    response = requests.get(url, params=params, timeout=10)
                                    
                                    if response.status_code == 200:
                                        data = response.json()
                                        ig_account_id = data.get("instagram_business_account", {}).get("id", "No encontrado")
                                        return f"✅ Conexión exitosa!\n\nPágina: {data.get('name', 'N/A')}\nInstagram Business Account ID: {ig_account_id}"
                                    else:
                                        return f"❌ Error de conexión: {response.status_code} - {response.text}"
                                        
                                except Exception as e:
                                    return f"❌ Error probando conexión: {e}"
                            
                            save_instagram_btn.click(
                                save_instagram_config,
                                inputs=[instagram_enabled, instagram_page_id, instagram_access_token, instagram_verify_token],
                                outputs=[instagram_status]
                            )
                            
                            test_instagram_btn.click(
                                test_instagram_connection,
                                inputs=[instagram_enabled, instagram_page_id, instagram_access_token],
                                outputs=[instagram_status]
                            )
                        
                        # Estado y Webhooks Tab
                        with gr.Tab("🌐 Estado y Webhooks"):
                            gr.Markdown("### Estado de Conexiones y Webhooks")
                            
                            with gr.Accordion("📖 Instrucciones de Configuración", open=True):
                                gr.Markdown("""
                                **Pasos para configurar webhooks:**
                                
                                **1. WhatsApp Business:**
                                1. Ve a Meta Business Suite > WhatsApp > API Setup
                                2. Copia la Webhook URL mostrada arriba
                                3. Configura el Verify Token (el mismo que ingresaste)
                                4. Selecciona los eventos: `messages`
                                5. Guarda la configuración
                                
                                **2. Instagram Direct:**
                                1. Ve a Meta for Developers > Tu App > Webhooks
                                2. Selecciona "Instagram" o "Page"
                                3. Copia la Webhook URL mostrada arriba
                                4. Configura el Verify Token
                                5. Suscríbete a: `messages`, `messaging_postbacks`
                                6. Guarda la configuración
                                
                                **3. Probar Conexión:**
                                - Usa los botones "Probar Conexión" en cada tab
                                - Verifica que el estado muestre "✅ Conexión exitosa"
                                - Envía un mensaje de prueba desde WhatsApp/Instagram
                                """)
                            
                            connection_status_json = gr.JSON(
                                label="Estado de Conexiones",
                                value={
                                    "whatsapp": {
                                        "enabled": False,
                                        "configured": False,
                                        "connected": False
                                    },
                                    "instagram": {
                                        "enabled": False,
                                        "configured": False,
                                        "connected": False
                                    }
                                }
                            )
                            
                            refresh_status_btn = gr.Button("🔄 Actualizar Estado", variant="secondary")
                            
                            def get_connection_status():
                                """Obtiene estado actual de conexiones."""
                                try:
                                    status = {
                                        "whatsapp": {
                                            "enabled": hasattr(self, 'whatsapp_adapter') and self.whatsapp_adapter is not None,
                                            "configured": bool(os.getenv("WHATSAPP_PHONE_NUMBER_ID")),
                                            "connected": False  # Se podría verificar con una API call
                                        },
                                        "instagram": {
                                            "enabled": hasattr(self, 'instagram_adapter') and self.instagram_adapter is not None,
                                            "configured": bool(os.getenv("INSTAGRAM_PAGE_ID")),
                                            "connected": False
                                        }
                                    }
                                    return status
                                except:
                                    return {
                                        "whatsapp": {"enabled": False, "configured": False, "connected": False},
                                        "instagram": {"enabled": False, "configured": False, "connected": False}
                                    }
                            
                            refresh_status_btn.click(fn=get_connection_status, outputs=[connection_status_json])
                            
                            # Generar URLs de webhooks
                            webhook_base = os.getenv("WEBHOOK_BASE_URL", "https://tu-dominio.com")
                            
                            gr.Markdown(f"""
                            **URLs de Webhooks:**
                            - WhatsApp: `{webhook_base}/webhooks/meta/whatsapp`
                            - Instagram/Messenger: `{webhook_base}/webhooks/meta/messenger`
                            
                            ⚠️ **Importante:** Reemplaza `tu-dominio.com` con tu dominio público real. Si estás en desarrollo local, usa ngrok o similar.
                            """)
                
                # TAB 4: Métricas
                with gr.Tab("📊 Métricas"):
                    gr.Markdown("### Métricas y Analytics")
                    
                    if hasattr(self, 'agent') and hasattr(self.agent, 'react_agent'):
                        # Obtener métricas del widget optimizer si está disponible
                        metrics_json = gr.JSON(label="Métricas Actuales", value={})
                        refresh_btn = gr.Button("🔄 Actualizar", variant="secondary")
                        
                        def get_metrics():
                            """Obtiene métricas actuales."""
                            try:
                                # Intentar obtener métricas del widget optimizer
                                # Por ahora, retornar métricas de ejemplo
                                return {
                                    "total_requests": 0,
                                    "conversions": 0,
                                    "conversion_rate": 0.0,
                                    "total_revenue": 0.0,
                                    "drop_off_rate": 0.0,
                                    "avg_response_time": 0.0,
                                    "sales_stages": {},
                                    "intents": {},
                                }
                            except:
                                return {}
                        
                        refresh_btn.click(fn=get_metrics, outputs=[metrics_json])
                    else:
                        gr.Markdown("Las métricas estarán disponibles cuando el agente esté en uso.")
            
            return demo

