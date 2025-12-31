"""
UI de Gradio Completa para Configuración de STAR AGENT.

Permite configurar TODO desde la interfaz sin tocar código:
- Ingesta automática (web, Instagram, Facebook, Google)
- Configuración del chatbot (tone, personality, instructions)
- RAG avanzado
- Sales Closer Elite
- Integraciones (Stripe, Meta Ads)
- Canales (WhatsApp, Instagram, Facebook)
- Métricas y analytics
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional

try:
    import gradio as gr
    GRADIO_AVAILABLE = True
except ImportError:
    GRADIO_AVAILABLE = False
    print("⚠️ Gradio no disponible. Instala con: pip install gradio")

from ...config import AppConfig, load_config


class StarAgentConfigUI:
    """
    UI de Gradio para configurar STAR AGENT completamente.
    
    Diseñado para personas sin conocimiento técnico.
    """
    
    def __init__(self, config_path: Optional[Path] = None, star_agent_mode=None):
        """
        Inicializa la UI de configuración.
        
        Args:
            config_path: Ruta donde guardar/cargar configuración (JSON)
            star_agent_mode: Instancia de StarAgentMode (opcional, se puede establecer después)
        """
        self.config_path = config_path or Path("docchat/star_agent/config/star_agent_config.json")
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Cargar configuración existente
        self.current_config = self._load_config()
        
        # Referencia a StarAgentMode (para el servidor API del widget)
        self.star_agent_mode = star_agent_mode
        
        # Estado del servidor API
        self.api_server_process = None
        self.api_server_thread = None
        self.api_server_running = False
        self.api_server_port = 7864
    
    def _load_config(self) -> Dict[str, Any]:
        """Carga configuración desde JSON."""
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️ Error cargando configuración: {e}")
        return {}
    
    def _save_config(self, config: Dict[str, Any]):
        """Guarda configuración en JSON."""
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            return True, "✅ Configuración guardada exitosamente"
        except Exception as e:
            return False, f"❌ Error guardando: {e}"
    
    def create_ui(self) -> gr.Blocks:
        """
        Crea la UI completa de Gradio.
        
        Returns:
            Gradio Blocks con todos los tabs de configuración
        """
        if not GRADIO_AVAILABLE:
            raise ImportError("Gradio no está instalado. Instala con: pip install gradio")
        
        with gr.Blocks(
            theme=gr.themes.Soft(),
            title="STAR AGENT - Configuración",
            css="""
            .gradio-container {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }
            .config-section {
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 20px;
                margin: 10px 0;
            }
            """
        ) as demo:
            gr.Markdown("""
            # ⭐ STAR AGENT - Panel de Configuración
            
            Configura tu asistente virtual 24/7 desde aquí. **No necesitas tocar código.**
            
            Todas las configuraciones se guardan automáticamente y se aplican inmediatamente.
            """)
            
            with gr.Tabs() as tabs:
                # TAB 1: Configuración Básica del Chatbot
                with gr.Tab("🤖 Chatbot Básico"):
                    gr.Markdown("### Configuración General del Chatbot")
                    
                    with gr.Row():
                        brand_name = gr.Textbox(
                            label="Nombre de tu Empresa/Marca",
                            value=self.current_config.get("brand_name", ""),
                            placeholder="Ej: Mi Tienda Online",
                            info="Este nombre aparecerá en las respuestas del agente"
                        )
                    
                    with gr.Row():
                        chatbot_tone = gr.Dropdown(
                            label="Tono de Comunicación",
                            choices=["friendly", "professional", "casual", "formal", "enthusiastic"],
                            value=self.current_config.get("chatbot_tone", "friendly"),
                            info="Define cómo habla el agente"
                        )
                    
                    with gr.Row():
                        chatbot_personality = gr.Textbox(
                            label="Personalidad del Chatbot (Opcional)",
                            value=self.current_config.get("chatbot_personality", ""),
                            placeholder="Ej: Soy un asistente amigable y entusiasta que ama ayudar a los clientes...",
                            lines=3,
                            info="Describe la personalidad del agente en tus propias palabras"
                        )
                    
                    with gr.Row():
                        chatbot_custom_instructions = gr.Textbox(
                            label="Instrucciones Personalizadas (Opcional)",
                            value=self.current_config.get("chatbot_custom_instructions", ""),
                            placeholder="Ej: Siempre menciona que tenemos envío gratis. Nunca ofrezcas descuentos mayores al 20%...",
                            lines=5,
                            info="Instrucciones específicas para tu negocio"
                        )
                    
                    with gr.Row():
                        default_language = gr.Dropdown(
                            label="Idioma por Defecto",
                            choices=["es", "en", "pt", "fr", "de"],
                            value=self.current_config.get("default_language", "es"),
                            info="Idioma principal del agente"
                        )
                    
                    with gr.Row():
                        multilingual_enabled = gr.Checkbox(
                            label="Soporte Multilingüe",
                            value=self.current_config.get("multilingual_enabled", False),
                            info="Permite que el agente responda en otros idiomas automáticamente"
                        )
                
                # TAB 2: Ingesta Automática
                with gr.Tab("📥 Ingesta Automática"):
                    gr.Markdown("### Configuración de Ingesta Multi-Fuente")
                    gr.Markdown("El agente aprenderá automáticamente de estas fuentes.")
                    
                    with gr.Accordion("🌐 Sitio Web", open=True):
                        enable_web_crawling = gr.Checkbox(
                            label="Habilitar Crawling Automático del Sitio Web",
                            value=self.current_config.get("enable_web_crawling", False),
                            info="El sistema crawleará tu sitio web cada 6 horas automáticamente"
                        )
                        
                        website_url = gr.Textbox(
                            label="URL de tu Sitio Web",
                            value=self.current_config.get("website_url", ""),
                            placeholder="https://tu-empresa.com",
                            info="URL principal de tu sitio web"
                        )
                    
                    with gr.Accordion("📷 Instagram", open=False):
                        enable_instagram = gr.Checkbox(
                            label="Habilitar Extracción de Instagram",
                            value=self.current_config.get("enable_instagram", False),
                            info="El agente aprenderá de tus posts de Instagram"
                        )
                        
                        instagram_access_token = gr.Textbox(
                            label="Instagram Access Token",
                            value=self.current_config.get("instagram_access_token", ""),
                            placeholder="Tu Instagram Access Token",
                            type="password",
                            info="Obtén tu token en https://developers.facebook.com/"
                        )
                        
                        gr.Markdown("""
                        **Cómo obtener tu Instagram Access Token:**
                        1. Ve a https://developers.facebook.com/
                        2. Crea una app
                        3. Agrega "Instagram Graph API"
                        4. Genera access token con permisos: `instagram_basic`, `instagram_content_publish`
                        """)
                    
                    with gr.Accordion("📘 Facebook", open=False):
                        enable_facebook = gr.Checkbox(
                            label="Habilitar Extracción de Facebook",
                            value=self.current_config.get("enable_facebook", False),
                            info="El agente aprenderá de tus posts de Facebook"
                        )
                        
                        facebook_access_token = gr.Textbox(
                            label="Facebook Access Token",
                            value=self.current_config.get("facebook_access_token", ""),
                            placeholder="Tu Facebook Access Token",
                            type="password"
                        )
                        
                        facebook_page_id = gr.Textbox(
                            label="Facebook Page ID",
                            value=self.current_config.get("facebook_page_id", ""),
                            placeholder="ID de tu página de Facebook",
                            info="Encuéntralo en la configuración de tu página"
                        )
                        
                        facebook_verify_token = gr.Textbox(
                            label="Facebook Verify Token (para Webhooks)",
                            value=self.current_config.get("facebook_verify_token", ""),
                            placeholder="Token de verificación para webhooks",
                            type="password"
                        )
                    
                    with gr.Accordion("🔍 Google Business", open=False):
                        enable_google = gr.Checkbox(
                            label="Habilitar Extracción de Google Business",
                            value=self.current_config.get("enable_google", False),
                            info="El agente aprenderá de tus reviews de Google"
                        )
                        
                        google_business_api_key = gr.Textbox(
                            label="Google Business API Key",
                            value=self.current_config.get("google_business_api_key", ""),
                            placeholder="Tu Google Places API Key",
                            type="password"
                        )
                        
                        google_place_id = gr.Textbox(
                            label="Google Place ID",
                            value=self.current_config.get("google_place_id", ""),
                            placeholder="ID de tu negocio en Google Maps",
                            info="Encuéntralo en la URL de Google Maps de tu negocio"
                        )
                    
                    with gr.Accordion("⚙️ Configuración Avanzada", open=False):
                        scheduler_web_interval = gr.Number(
                            label="Intervalo de Actualización Web (horas)",
                            value=self.current_config.get("scheduler_web_interval", 6),
                            minimum=1,
                            maximum=24,
                            info="Cada cuántas horas se actualiza el sitio web (default: 6h)"
                        )
                        
                        enable_webhooks = gr.Checkbox(
                            label="Habilitar Webhooks (Actualización en Tiempo Real)",
                            value=self.current_config.get("enable_webhooks", True),
                            info="Los nuevos posts se indexan inmediatamente (sin esperar scheduler)"
                        )
                
                # TAB 3: RAG y Documentos
                with gr.Tab("📚 RAG y Documentos"):
                    gr.Markdown("### Configuración de RAG (Base de Conocimiento)")
                    
                    rag_enabled = gr.Checkbox(
                        label="Habilitar RAG Avanzado",
                        value=self.current_config.get("rag_enabled", True),
                        info="El agente usará documentos para responder preguntas"
                    )
                    
                    with gr.Accordion("📁 Subir Documentos Manualmente", open=True):
                        gr.Markdown("**Sube documentos que el agente debe conocer (PDFs, Word, texto)**")
                        document_upload = gr.File(
                            label="Subir Documentos",
                            file_count="multiple",
                            file_types=[".pdf", ".docx", ".txt", ".md"]
                        )
                        
                        upload_btn = gr.Button("📤 Procesar y Agregar Documentos", variant="primary")
                        upload_status = gr.Textbox(label="Estado", interactive=False)
                    
                    with gr.Accordion("⚙️ Configuración Avanzada de RAG", open=False):
                        rag_k = gr.Number(
                            label="Número de Documentos a Recuperar (k)",
                            value=self.current_config.get("rag_k", 5),
                            minimum=1,
                            maximum=20,
                            info="Cuántos documentos recuperar por consulta"
                        )
                        
                        enable_verification = gr.Checkbox(
                            label="Habilitar Verificación de Respuestas",
                            value=self.current_config.get("enable_verification", True),
                            info="Verifica que las respuestas estén soportadas por documentos"
                        )
                
                # TAB 4: Sales Closer Elite
                with gr.Tab("💰 Sales Closer Elite"):
                    gr.Markdown("### Configuración de Cierre de Ventas")
                    
                    enable_sales_closer = gr.Checkbox(
                        label="Habilitar Sales Closer Elite",
                        value=self.current_config.get("enable_sales_closer", True),
                        info="Activa técnicas avanzadas de cierre de ventas"
                    )
                    
                    with gr.Accordion("🎯 Estrategias de Venta", open=True):
                        gr.Markdown("""
                        **Estrategias disponibles:**
                        - **ANCHORING**: Para queries sobre precio
                        - **ROI**: Para "vale la pena"
                        - **SOCIAL_PROOF**: Para opiniones/reseñas
                        - **URGENCY**: Para crear urgencia ética
                        - **STANDARD**: Default
                        """)
                        
                        sales_aggressiveness = gr.Slider(
                            label="Agresividad de Ventas (1-10)",
                            value=self.current_config.get("sales_aggressiveness", 5),
                            minimum=1,
                            maximum=10,
                            info="1 = Suave, 10 = Muy agresivo (pero ético)"
                        )
                    
                    with gr.Accordion("🛡️ Manejo de Objeciones", open=True):
                        gr.Markdown("**Define cómo responder a objeciones comunes (formato JSON)**")
                        # Asegurar que objection_responses sea siempre un dict válido
                        objection_default = {
                            "caro": "Entiendo. Justamente por eso incluye X, Y y Z que ahorran dinero a largo plazo.",
                            "después": "Tiene sentido. ¿Qué tendría que pasar para que lo veas útil ahora?",
                            "pensar": "Claro, es una decisión importante. ¿Hay algo específico en lo que pueda ayudarte a decidir?"
                        }
                        objection_value = self.current_config.get("objection_responses", objection_default)
                        if not isinstance(objection_value, dict):
                            objection_value = objection_default
                        
                        objection_responses = gr.JSON(
                            label="Respuestas a Objeciones Comunes",
                            value=objection_value
                        )
                
                # TAB 5: Integraciones
                with gr.Tab("🔌 Integraciones"):
                    gr.Markdown("### Integraciones con Servicios Externos")
                    
                    with gr.Accordion("💳 Stripe (Pagos)", open=True):
                        enable_stripe = gr.Checkbox(
                            label="Habilitar Stripe",
                            value=self.current_config.get("enable_stripe", False),
                            info="Permite procesar pagos con Stripe"
                        )
                        
                        stripe_secret_key = gr.Textbox(
                            label="Stripe Secret Key",
                            value=self.current_config.get("stripe_secret_key", ""),
                            placeholder="sk_test_...",
                            type="password",
                            info="Obtén tu clave en https://dashboard.stripe.com/apikeys"
                        )
                    
                    with gr.Accordion("📊 Google Analytics", open=False):
                        enable_google_analytics = gr.Checkbox(
                            label="Habilitar Google Analytics",
                            value=self.current_config.get("enable_google_analytics", False)
                        )
                        
                        google_analytics_id = gr.Textbox(
                            label="Google Analytics ID",
                            value=self.current_config.get("google_analytics_id", ""),
                            placeholder="G-XXXXXXXXXX"
                        )
                    
                    with gr.Accordion("📱 Meta Pixel", open=False):
                        enable_meta_pixel = gr.Checkbox(
                            label="Habilitar Meta Pixel",
                            value=self.current_config.get("enable_meta_pixel", False)
                        )
                        
                        meta_pixel_id = gr.Textbox(
                            label="Meta Pixel ID",
                            value=self.current_config.get("meta_pixel_id", ""),
                            placeholder="1234567890"
                        )
                
                # TAB 6: Links y URLs
                with gr.Tab("🔗 Links y URLs"):
                    gr.Markdown("### Configuración de Links Personalizados")
                    gr.Markdown("""
                    **Configura links que el agente puede usar y enviar a los clientes.**
                    
                    El agente puede acceder a estos links automáticamente cuando sea apropiado.
                    """)
                    
                    with gr.Accordion("📋 Links de Productos", open=True):
                        gr.Markdown("""
                        **⚠️ IMPORTANTE: URL Base para Links de Productos**
                        
                        El agente necesita esta URL para generar links automáticamente cuando un cliente pregunta por productos.
                        Ejemplo: Si pones `https://tu-tienda.com`, el agente generará links como `https://tu-tienda.com/products/producto-123`
                        """)
                        
                        base_url = gr.Textbox(
                            label="🔗 URL Base para Links de Productos (REQUERIDO)",
                            value=self.current_config.get("base_url", ""),
                            placeholder="https://tu-tienda.com",
                            info="URL base de tu e-commerce (sin / al final). El agente usará esto para generar links automáticos a productos."
                        )
                        
                        product_catalog_link = gr.Textbox(
                            label="Link del Catálogo de Productos",
                            value=self.current_config.get("product_catalog_link", ""),
                            placeholder="https://tu-tienda.com/productos",
                            info="Link al catálogo completo de productos (opcional)"
                        )
                        
                        store_link = gr.Textbox(
                            label="Link de la Tienda",
                            value=self.current_config.get("store_link", ""),
                            placeholder="https://tu-tienda.com",
                            info="Link principal de tu tienda/sitio web (opcional)"
                        )
                    
                    with gr.Accordion("💳 Links de Pago y Checkout", open=True):
                        gr.Markdown("**Links relacionados con pagos (checkout, carrito, etc.)**")
                        
                        checkout_link = gr.Textbox(
                            label="Link de Checkout",
                            value=self.current_config.get("checkout_link", ""),
                            placeholder="https://tu-tienda.com/checkout",
                            info="Link directo al checkout/carrito"
                        )
                        
                        payment_methods_link = gr.Textbox(
                            label="Link de Métodos de Pago",
                            value=self.current_config.get("payment_methods_link", ""),
                            placeholder="https://tu-tienda.com/metodos-pago",
                            info="Link con información de métodos de pago aceptados"
                        )
                    
                    with gr.Accordion("📞 Links de Contacto y Soporte", open=True):
                        gr.Markdown("**Links de contacto, soporte y ayuda**")
                        
                        support_link = gr.Textbox(
                            label="Link de Soporte/Ayuda",
                            value=self.current_config.get("support_link", ""),
                            placeholder="https://tu-tienda.com/soporte",
                            info="Link a página de soporte o centro de ayuda"
                        )
                        
                        contact_link = gr.Textbox(
                            label="Link de Contacto",
                            value=self.current_config.get("contact_link", ""),
                            placeholder="https://tu-tienda.com/contacto",
                            info="Link a página de contacto"
                        )
                        
                        faq_link = gr.Textbox(
                            label="Link de Preguntas Frecuentes (FAQ)",
                            value=self.current_config.get("faq_link", ""),
                            placeholder="https://tu-tienda.com/faq",
                            info="Link a página de preguntas frecuentes"
                        )
                    
                    with gr.Accordion("📦 Links de Entrega y Políticas", open=False):
                        gr.Markdown("**Links sobre envíos, políticas y términos**")
                        
                        shipping_link = gr.Textbox(
                            label="Link de Envíos/Entrega",
                            value=self.current_config.get("shipping_link", ""),
                            placeholder="https://tu-tienda.com/envios",
                            info="Link con información de envíos y entregas"
                        )
                        
                        returns_link = gr.Textbox(
                            label="Link de Devoluciones",
                            value=self.current_config.get("returns_link", ""),
                            placeholder="https://tu-tienda.com/devoluciones",
                            info="Link con política de devoluciones"
                        )
                        
                        privacy_policy_link = gr.Textbox(
                            label="Link de Política de Privacidad",
                            value=self.current_config.get("privacy_policy_link", ""),
                            placeholder="https://tu-tienda.com/privacidad",
                            info="Link a política de privacidad"
                        )
                        
                        terms_link = gr.Textbox(
                            label="Link de Términos y Condiciones",
                            value=self.current_config.get("terms_link", ""),
                            placeholder="https://tu-tienda.com/terminos",
                            info="Link a términos y condiciones"
                        )
                    
                    with gr.Accordion("🎁 Links Personalizados", open=False):
                        gr.Markdown("**Define tus propios links personalizados con etiquetas**")
                        gr.Markdown("**Formato JSON:** `{'etiqueta': 'url', ...}`")
                        
                        # Asegurar que custom_links sea siempre un dict válido
                        custom_links_default = {
                            "promocion_especial": "https://tu-tienda.com/promo",
                            "nuevos_lanzamientos": "https://tu-tienda.com/nuevos"
                        }
                        custom_links_value = self.current_config.get("custom_links", custom_links_default)
                        # Validar que sea un dict, si no, usar default
                        if not isinstance(custom_links_value, dict):
                            custom_links_value = custom_links_default
                        
                        custom_links = gr.JSON(
                            label="Links Personalizados",
                            value=custom_links_value
                        )
                        gr.Markdown("💡 Define links personalizados con etiquetas para usar en respuestas")
                
                # TAB 7: Canales
                with gr.Tab("📱 Canales"):
                    gr.Markdown("### Configuración de Canales de Comunicación")
                    
                    with gr.Accordion("🌐 Widget Web", open=True):
                        enable_widget = gr.Checkbox(
                            label="Habilitar Widget Web",
                            value=self.current_config.get("enable_widget", True),
                            info="Widget embebible para tu sitio web"
                        )
                        
                        widget_position = gr.Dropdown(
                            label="Posición del Widget",
                            choices=["bottom-right", "bottom-left", "top-right", "top-left"],
                            value=self.current_config.get("widget_position", "bottom-right")
                        )
                    
                    with gr.Accordion("💬 WhatsApp Business", open=False):
                        enable_whatsapp = gr.Checkbox(
                            label="Habilitar WhatsApp Business API",
                            value=self.current_config.get("enable_whatsapp", False),
                            info="Integración nativa con WhatsApp Business API de Meta"
                        )
                        
                        whatsapp_phone_number_id = gr.Textbox(
                            label="WhatsApp Phone Number ID",
                            value=self.current_config.get("whatsapp_phone_number_id", ""),
                            placeholder="123456789012345",
                            info="ID del número de teléfono de WhatsApp Business (encuéntralo en Meta Business Manager)"
                        )
                        
                        whatsapp_access_token = gr.Textbox(
                            label="WhatsApp Access Token",
                            value=self.current_config.get("whatsapp_access_token", ""),
                            type="password",
                            info="Access token de WhatsApp Business API"
                        )
                        
                        whatsapp_verify_token = gr.Textbox(
                            label="WhatsApp Verify Token",
                            value=self.current_config.get("whatsapp_verify_token", ""),
                            placeholder="star_agent_verify_token",
                            info="Token de verificación para webhooks (debe coincidir con el configurado en Meta)"
                        )
                        
                        gr.Markdown("""
                        **Cómo obtener credenciales:**
                        1. Ve a https://business.facebook.com/
                        2. Crea una app de WhatsApp Business
                        3. Obtén Phone Number ID y Access Token
                        4. Configura webhook: `https://tu-servidor.com/webhooks/meta/whatsapp`
                        5. Verify Token: usa el mismo que configuraste aquí
                        """)
                    
                    with gr.Accordion("📘 Facebook Messenger", open=False):
                        enable_messenger = gr.Checkbox(
                            label="Habilitar Facebook Messenger",
                            value=self.current_config.get("enable_messenger", False),
                            info="Integración nativa con Facebook Messenger usando Graph API"
                        )
                        
                        messenger_page_id = gr.Textbox(
                            label="Facebook Page ID",
                            value=self.current_config.get("messenger_page_id", "") or self.current_config.get("facebook_page_id", ""),
                            placeholder="123456789012345",
                            info="ID de tu página de Facebook"
                        )
                        
                        messenger_page_access_token = gr.Textbox(
                            label="Facebook Page Access Token",
                            value=self.current_config.get("messenger_page_access_token", "") or self.current_config.get("facebook_page_access_token", ""),
                            type="password",
                            info="Page Access Token (no confundir con User Access Token)"
                        )
                        
                        messenger_verify_token = gr.Textbox(
                            label="Messenger Verify Token",
                            value=self.current_config.get("messenger_verify_token", "") or self.current_config.get("facebook_verify_token", ""),
                            placeholder="star_agent_verify_token",
                            info="Token de verificación para webhooks"
                        )
                        
                        gr.Markdown("""
                        **Cómo obtener credenciales:**
                        1. Ve a https://developers.facebook.com/
                        2. Crea una app y agrega "Messenger"
                        3. Obtén Page ID y Page Access Token
                        4. Configura webhook: `https://tu-servidor.com/webhooks/meta/messenger`
                        5. Suscríbete a eventos: `messages`, `messaging_postbacks`
                        """)
                    
                    with gr.Accordion("📷 Instagram Direct", open=False):
                        enable_instagram_direct = gr.Checkbox(
                            label="Habilitar Instagram Direct",
                            value=self.current_config.get("enable_instagram_direct", False)
                        )
                
                # TAB 7: Handoff a Humanos
                with gr.Tab("👤 Handoff a Humanos"):
                    gr.Markdown("### Configuración de Handoff a Agentes Humanos")
                    gr.Markdown("""
                    **Configura la transferencia de conversaciones a humanos.**
                    
                    El agente puede transferir automáticamente cuando:
                    - Confianza baja en respuesta
                    - Objeción fuerte del cliente
                    - Frustración alta detectada
                    - Usuario solicita explícitamente
                    """)
                    
                    enable_handoff = gr.Checkbox(
                        label="✅ Habilitar Handoff a Humanos",
                        value=self.current_config.get("handoff_enabled", False),
                        info="Activa/desactiva la transferencia a humanos"
                    )
                    
                    handoff_provider = gr.Dropdown(
                        label="Proveedor de Handoff",
                        choices=["zendesk", "whatsapp", "email", "none"],
                        value=self.current_config.get("handoff_provider", "none"),
                        info="Selecciona el proveedor para handoff"
                    )
                    
                    with gr.Accordion("🔌 Configuración Zendesk", open=True):
                        gr.Markdown("**Configuración para Zendesk (Subdomain, API Token, Queue)**")
                        
                        handoff_zendesk_subdomain = gr.Textbox(
                            label="Zendesk Subdomain",
                            value=self.current_config.get("handoff_zendesk_subdomain", ""),
                            placeholder="tu-empresa",
                            info="Subdomain de Zendesk (ej: tu-empresa.zendesk.com)"
                        )
                        
                        handoff_zendesk_token = gr.Textbox(
                            label="Zendesk API Token",
                            value=self.current_config.get("handoff_zendesk_token", ""),
                            type="password",
                            placeholder="token_xxx",
                            info="API Token de Zendesk"
                        )
                        
                        handoff_zendesk_queue = gr.Textbox(
                            label="Queue / Departamento",
                            value=self.current_config.get("handoff_zendesk_queue", ""),
                            placeholder="soporte",
                            info="Queue o departamento en Zendesk"
                        )
                    
                    with gr.Accordion("💬 Configuración WhatsApp Handoff", open=False):
                        gr.Markdown("**Configuración para Handoff vía WhatsApp Business**")
                        
                        handoff_whatsapp_token = gr.Textbox(
                            label="WhatsApp Access Token",
                            value=self.current_config.get("handoff_whatsapp_token", ""),
                            type="password",
                            info="Access Token de WhatsApp Business API"
                        )
                    
                    with gr.Accordion("📧 Configuración Email Handoff", open=False):
                        gr.Markdown("**Configuración para Handoff vía Email**")
                        
                        handoff_email = gr.Textbox(
                            label="Email de Destino",
                            value=self.current_config.get("handoff_email", ""),
                            placeholder="soporte@tu-empresa.com",
                            info="Email donde se enviarán las consultas"
                        )
                    
                    with gr.Accordion("🎯 Triggers de Handoff", open=True):
                        gr.Markdown("**Configura cuándo hacer handoff automáticamente**")
                        
                        handoff_trigger_manual = gr.Checkbox(
                            label="Manual (Usuario lo solicita)",
                            value=self.current_config.get("handoff_trigger_manual", True),
                            info="Handoff cuando el usuario explícitamente lo pide"
                        )
                        
                        handoff_trigger_low_confidence = gr.Checkbox(
                            label="Automático: Confianza Baja",
                            value=self.current_config.get("handoff_trigger_low_confidence", False),
                            info="Handoff cuando la confianza en la respuesta es < 50%"
                        )
                        
                        handoff_trigger_strong_objection = gr.Checkbox(
                            label="Automático: Objeción Fuerte",
                            value=self.current_config.get("handoff_trigger_strong_objection", False),
                            info="Handoff cuando detecta objeción fuerte (> 70%)"
                        )
                        
                        handoff_trigger_frustration = gr.Checkbox(
                            label="Automático: Frustración Alta",
                            value=self.current_config.get("handoff_trigger_frustration", False),
                            info="Handoff cuando frustración > 70%"
                        )
                
                # TAB 8: Ingesta Automática
                with gr.Tab("🔄 Ingesta Automática"):
                    gr.Markdown("### Configuración de Ingesta Automática Multi-Fuente")
                    gr.Markdown("""
                    **Configura la ingesta automática de datos desde múltiples fuentes.**
                    
                    El sistema puede absorber automáticamente información de:
                    - Sitio web (crawling con Playwright)
                    - Instagram (posts, captions, productos)
                    - Facebook (posts, reviews)
                    """)
                    
                    ingestion_scheduler_enabled = gr.Checkbox(
                        label="✅ Habilitar Scheduler de Ingesta",
                        value=self.current_config.get("ingestion_scheduler_enabled", False),
                        info="Activa/desactiva la ingesta automática programada"
                    )
                    
                    ingestion_interval_hours = gr.Number(
                        label="Intervalo de Ingesta (horas)",
                        value=self.current_config.get("ingestion_interval_hours", 6),
                        minimum=1,
                        maximum=168,
                        info="Cada cuántas horas ejecutar ingesta automática (default: 6h)"
                    )
                    
                    with gr.Accordion("🌐 Ingesta de Website", open=True):
                        gr.Markdown("**Configuración para ingesta automática del sitio web**")
                        
                        ingestion_website_enabled = gr.Checkbox(
                            label="✅ Habilitar Ingesta de Website",
                            value=self.current_config.get("ingestion_website_enabled", False),
                            info="Activa/desactiva ingesta de website"
                        )
                        
                        ingestion_website_url = gr.Textbox(
                            label="URL del Website",
                            value=self.current_config.get("ingestion_website_url", ""),
                            placeholder="https://tu-empresa.com",
                            info="URL principal del sitio web a crawlear"
                        )
                    
                    with gr.Accordion("📷 Ingesta de Instagram", open=False):
                        gr.Markdown("**Configuración para ingesta automática de Instagram**")
                        
                        ingestion_instagram_enabled = gr.Checkbox(
                            label="✅ Habilitar Ingesta de Instagram",
                            value=self.current_config.get("ingestion_instagram_enabled", False),
                            info="Activa/desactiva ingesta de Instagram"
                        )
                        
                        ingestion_instagram_token = gr.Textbox(
                            label="Instagram Access Token",
                            value=self.current_config.get("ingestion_instagram_token", ""),
                            type="password",
                            info="Access Token de Instagram Graph API"
                        )
                    
                    with gr.Accordion("📘 Ingesta de Facebook", open=False):
                        gr.Markdown("**Configuración para ingesta automática de Facebook**")
                        
                        ingestion_facebook_enabled = gr.Checkbox(
                            label="✅ Habilitar Ingesta de Facebook",
                            value=self.current_config.get("ingestion_facebook_enabled", False),
                            info="Activa/desactiva ingesta de Facebook"
                        )
                        
                        ingestion_facebook_token = gr.Textbox(
                            label="Facebook Access Token",
                            value=self.current_config.get("ingestion_facebook_token", ""),
                            type="password",
                            info="Access Token de Facebook Graph API"
                        )
                    
                    run_ingestion_now_btn = gr.Button("▶️ Ejecutar Ingesta Ahora (Run Now)", variant="primary")
                    ingestion_status = gr.Textbox(
                        label="Estado de Ingesta",
                        value="No ejecutado",
                        interactive=False,
                        lines=5
                    )
                
                # TAB 9: Métricas y Analytics
                with gr.Tab("📊 Métricas"):
                    gr.Markdown("### Métricas y Analytics del Agente")
                    
                    with gr.Row():
                        # Asegurar que metrics_display tenga un dict válido
                        metrics_default = {}
                        metrics_config = self.current_config.get("metrics", metrics_default)
                        metrics_value = metrics_config if isinstance(metrics_config, dict) else metrics_default
                        metrics_display = gr.JSON(
                            label="Métricas Actuales",
                            value=metrics_value
                        )
                    
                    refresh_metrics_btn = gr.Button("🔄 Actualizar Métricas", variant="secondary")
                    
                    gr.Markdown("""
                    **Métricas disponibles:**
                    - Total de requests
                    - Conversion rate
                    - Revenue total
                    - Drop-off rate
                    - Tiempo promedio de respuesta
                    - Etapas de venta más comunes
                    - Objeciones más frecuentes
                    """)
                
                # TAB 10: Widget Embeddable - Generar Código
                with gr.Tab("🔧 Generar Código"):
                    with gr.Row():
                        with gr.Column():
                            widget_api_url = gr.Textbox(
                                label="🌐 URL del Servidor",
                                value="http://127.0.0.1:7864",
                                placeholder="https://tu-servidor.com",
                                info="URL donde está corriendo tu servidor STAR AGENT API"
                            )
                            widget_id = gr.Textbox(
                                label="🆔 Widget ID",
                                placeholder="widget_abc123",
                                info="ID único para este widget (se genera automáticamente si lo dejas vacío)"
                            )
                            widget_brand_name = gr.Textbox(
                                label="🏷️ Nombre de Marca",
                                placeholder="Mi Empresa",
                                value=self.current_config.get("brand_name", "Tu Marca"),
                                info="Nombre que aparecerá en el widget"
                            )
                            widget_primary_color = gr.Textbox(
                                label="🎨 Color Principal",
                                value="#007bff",
                                placeholder="#007bff",
                                info="Color hexadecimal para el widget"
                            )
                            widget_position = gr.Radio(
                                label="📍 Posición",
                                choices=[("Esquina inferior derecha", "bottom-right"), ("Esquina inferior izquierda", "bottom-left")],
                                value="bottom-right"
                            )
                            widget_welcome_message = gr.Textbox(
                                label="💬 Mensaje de Bienvenida",
                                value="👋 ¡Hola! Soy tu asistente virtual. ¿En qué puedo ayudarte hoy?",
                                lines=2,
                                info="Mensaje que verá el usuario al abrir el chat"
                            )
                            
                            gr.Markdown("---")
                            gr.Markdown("### 💬 Integración WhatsApp y Messenger")
                            
                            widget_enable_whatsapp = gr.Checkbox(
                                label="✅ Activar Botón de WhatsApp",
                                value=False,
                                info="Muestra botón 'Prefiero WhatsApp' dentro del chat"
                            )
                            widget_whatsapp_number = gr.Textbox(
                                label="📱 Número de WhatsApp Business",
                                placeholder="+1234567890",
                                info="Número con código de país (ej: +1234567890)"
                            )
                            widget_whatsapp_message = gr.Textbox(
                                label="💬 Mensaje Predefinido WhatsApp",
                                value="Hola, vi tu producto en tu website",
                                lines=2,
                                info="Mensaje que aparecerá al abrir WhatsApp"
                            )
                            
                            widget_enable_messenger = gr.Checkbox(
                                label="✅ Activar Botón de Messenger",
                                value=False,
                                info="Muestra botón 'Prefiero Messenger' dentro del chat"
                            )
                            widget_messenger_page = gr.Textbox(
                                label="📘 Página de Facebook",
                                placeholder="tu-pagina-facebook",
                                info="Nombre de tu página (sin @ ni facebook.com)"
                            )
                            
                            generate_widget_code_btn = gr.Button("📋 Generar Código", variant="primary", size="lg")
                        
                        with gr.Column():
                            widget_code_output = gr.Code(
                                label="📋 Código HTML para Copiar y Pegar",
                                language="html",
                                lines=15,
                                value="**💡 Configura los campos de la izquierda y haz click en 'Generar Código'**"
                            )
                            widget_preview = gr.Markdown(
                                label="👁️ Preview",
                                value="**El código generado aparecerá arriba**"
                            )
                    
                    def generate_widget_code(api_url, widget_id_input, brand_name, primary_color, position, welcome_message,
                                            enable_whatsapp, whatsapp_number, whatsapp_message,
                                            enable_messenger, messenger_page):
                        """Genera código HTML/JS para el widget embeddable"""
                        try:
                            import uuid
                            
                            # Generar widget_id si no se proporciona
                            if not widget_id_input or not widget_id_input.strip():
                                widget_id_final = f"widget_{uuid.uuid4().hex[:12]}"
                            else:
                                widget_id_final = widget_id_input.strip()
                            
                            # Validar URL
                            if not api_url or not api_url.strip():
                                return "⚠️ **URL del servidor es requerida**", "❌ Error: URL requerida"
                            
                            api_url_clean = api_url.strip().rstrip('/')
                            
                            # Construir código HTML con atributos base (SIN comentarios HTML)
                            code_lines = [
                                f'<script src="{api_url_clean}/static/business-ai-widget.js"',
                                f'        data-api-url="{api_url_clean}"',
                                f'        data-widget-id="{widget_id_final}"',
                                f'        data-brand-name="{brand_name}"',
                                f'        data-primary-color="{primary_color}"',
                                f'        data-position="{position}"',
                                f'        data-welcome-message="{welcome_message}"'
                            ]
                            
                            # Agregar atributos de WhatsApp si está habilitado
                            if enable_whatsapp and whatsapp_number and whatsapp_number.strip():
                                code_lines.append(f'        data-enable-whatsapp="true"')
                                code_lines.append(f'        data-whatsapp-number="{whatsapp_number.strip()}"')
                                if whatsapp_message and whatsapp_message.strip():
                                    code_lines.append(f'        data-whatsapp-message="{whatsapp_message.strip()}"')
                            
                            # Agregar atributos de Messenger si está habilitado
                            if enable_messenger and messenger_page and messenger_page.strip():
                                code_lines.append(f'        data-enable-messenger="true"')
                                code_lines.append(f'        data-messenger-page="{messenger_page.strip()}"')
                            
                            code_lines.append('        async></script>')
                            
                            code = '\n'.join(code_lines)
                            
                            preview = f"""## ✅ Código Generado Exitosamente

**Widget ID:** `{widget_id_final}`

**Instrucciones:**
1. Copia el código HTML de arriba
2. Pégalo antes de `</body>` en tu website
3. El widget aparecerá automáticamente en la esquina {position.replace('bottom-', 'inferior ').replace('right', 'derecha').replace('left', 'izquierda')}

**Características del Widget:**
- ✅ Chat flotante con interfaz moderna
- ✅ Conectado con STAR AGENT
- ✅ Ventas + Soporte 24/7
- ✅ Carrito de compras integrado
- ✅ Detección de sentimiento
- ✅ Handoff humano automático
- ✅ Procesamiento de imágenes
- ✅ Botones de WhatsApp y Messenger (si están configurados)

**URL del Widget:** `{api_url_clean}/static/business-ai-widget.js`

**⚠️ IMPORTANTE:** El servidor API debe estar corriendo para que el widget funcione (ve a la pestaña "🚀 Servidor API")
"""
                            
                            return code, preview
                        except Exception as e:
                            import traceback
                            return f"❌ Error generando código: {str(e)}\n\n```\n{traceback.format_exc()}\n```", f"❌ Error: {str(e)}"
                    
                    generate_widget_code_btn.click(
                        fn=generate_widget_code,
                        inputs=[
                            widget_api_url, widget_id, widget_brand_name, widget_primary_color, widget_position, widget_welcome_message,
                            widget_enable_whatsapp, widget_whatsapp_number, widget_whatsapp_message,
                            widget_enable_messenger, widget_messenger_page
                        ],
                        outputs=[widget_code_output, widget_preview]
                    )
                
                # TAB 11: Configuración Enterprise
                with gr.Tab("⚙️ Configuración Enterprise"):
                    gr.Markdown("### ⚙️ Configuración Enterprise (Groq + PostgreSQL + n8n)")
                    gr.Markdown("""
                    **Para velocidad extrema y memoria de largo plazo:**
                    - **Groq:** Responde en <0.5 segundos (Llama 3.3 70B)
                    - **PostgreSQL:** Recuerda clientes meses después
                    - **n8n:** Conecta con WhatsApp/Instagram automáticamente
                    """)
                    
                    with gr.Row():
                        with gr.Column():
                            gr.Markdown("### 🔥 Groq Cloud (Velocidad Extrema)")
                            groq_api_key_input = gr.Textbox(
                                label="🔑 Groq API Key",
                                type="password",
                                placeholder="gsk_...",
                                value=os.getenv("GROQ_API_KEY", ""),
                                info="Obtén tu API key gratis en https://console.groq.com"
                            )
                            use_groq_checkbox = gr.Checkbox(
                                label="✅ Usar Groq (Llama 3.3 70B)",
                                value=os.getenv("DOCCHAT_USE_GROQ", "false").lower() == "true",
                                info="Activa para respuestas <0.5 segundos"
                            )
                            groq_model_select = gr.Dropdown(
                                label="🤖 Modelo Groq",
                                choices=[
                                    ("llama-3.3-70b-versatile", "Llama 3.3 70B (Recomendado)"),
                                    ("llama-3.1-70b-versatile", "Llama 3.1 70B"),
                                    ("llama-3.1-8b-instant", "Llama 3.1 8B (Más rápido)")
                                ],
                                value=os.getenv("DOCCHAT_GROQ_MODEL", "llama-3.3-70b-versatile"),
                                allow_custom_value=True
                            )
                            save_groq_btn = gr.Button("💾 Guardar Configuración Groq", variant="primary")
                            groq_status = gr.Markdown(label="📊 Estado Groq")
                        
                        with gr.Column():
                            gr.Markdown("### 🗄️ PostgreSQL (Memoria de Largo Plazo)")
                            postgresql_url_input = gr.Textbox(
                                label="🔗 Database URL",
                                placeholder="postgresql://user:pass@host:port/db",
                                type="password",
                                value=os.getenv("DATABASE_URL", ""),
                                info="URL de conexión PostgreSQL"
                            )
                            use_postgresql_checkbox = gr.Checkbox(
                                label="✅ Usar PostgreSQL",
                                value=os.getenv("DOCCHAT_POSTGRESQL_ENABLED", "false").lower() == "true",
                                info="Activa para recordar clientes meses después"
                            )
                            save_postgresql_btn = gr.Button("💾 Guardar Configuración PostgreSQL", variant="primary")
                            postgresql_status = gr.Markdown(label="📊 Estado PostgreSQL")
                    
                    gr.Markdown("---")
                    gr.Markdown("### 🔗 n8n (WhatsApp/Instagram)")
                    gr.Markdown("""
                    **Para conectar con Meta (WhatsApp/Instagram):**
                    1. Instala n8n (self-hosted o cloud)
                    2. Configura webhook de Meta
                    3. Crea workflow que llame a: `https://tu-servidor.com/star-agent/n8n/webhook`
                    """)
                    
                    n8n_webhook_url_display = gr.Markdown(
                        value="**Endpoint n8n:** `POST https://tu-servidor.com/star-agent/n8n/webhook`"
                    )
                    
                    def save_groq_config(api_key, use_groq, model):
                        """Guarda configuración de Groq en .env"""
                        try:
                            from pathlib import Path
                            
                            env_path = Path(".env")
                            
                            # Leer .env actual
                            env_vars = {}
                            if env_path.exists():
                                with open(env_path, "r", encoding="utf-8") as f:
                                    for line in f:
                                        if "=" in line and not line.strip().startswith("#"):
                                            parts = line.strip().split("=", 1)
                                            if len(parts) == 2:
                                                key, value = parts
                                                env_vars[key] = value
                            
                            # Actualizar variables
                            if api_key:
                                env_vars["GROQ_API_KEY"] = api_key
                            env_vars["DOCCHAT_USE_GROQ"] = "true" if use_groq else "false"
                            env_vars["DOCCHAT_GROQ_MODEL"] = model
                            
                            # Escribir .env
                            with open(env_path, "w", encoding="utf-8") as f:
                                for key, value in env_vars.items():
                                    f.write(f"{key}={value}\n")
                            
                            status = f"""✅ **Configuración Groq guardada**

**Estado:**
- API Key: {'✅ Configurada' if api_key else '❌ No configurada'}
- Usar Groq: {'✅ Activado' if use_groq else '❌ Desactivado'}
- Modelo: {model}

**⚠️ IMPORTANTE:** Reinicia el servidor para aplicar cambios.
```bash
# Reinicia run_star_agent_ui.py
```
"""
                            return status
                        except Exception as e:
                            return f"❌ Error: {str(e)}"
                    
                    def save_postgresql_config(db_url, use_postgresql):
                        """Guarda configuración de PostgreSQL en .env"""
                        try:
                            from pathlib import Path
                            
                            env_path = Path(".env")
                            
                            # Leer .env actual
                            env_vars = {}
                            if env_path.exists():
                                with open(env_path, "r", encoding="utf-8") as f:
                                    for line in f:
                                        if "=" in line and not line.strip().startswith("#"):
                                            parts = line.strip().split("=", 1)
                                            if len(parts) == 2:
                                                key, value = parts
                                                env_vars[key] = value
                            
                            # Actualizar variables
                            if db_url:
                                env_vars["DATABASE_URL"] = db_url
                            env_vars["DOCCHAT_POSTGRESQL_ENABLED"] = "true" if use_postgresql else "false"
                            
                            # Escribir .env
                            with open(env_path, "w", encoding="utf-8") as f:
                                for key, value in env_vars.items():
                                    f.write(f"{key}={value}\n")
                            
                            status = f"""✅ **Configuración PostgreSQL guardada**

**Estado:**
- Database URL: {'✅ Configurada' if db_url else '❌ No configurada'}
- Usar PostgreSQL: {'✅ Activado' if use_postgresql else '❌ Desactivado'}

**⚠️ IMPORTANTE:** 
1. Instala psycopg2: `pip install psycopg2-binary`
2. Reinicia el servidor para aplicar cambios.
3. Las tablas se crearán automáticamente al iniciar.
"""
                            return status
                        except Exception as e:
                            return f"❌ Error: {str(e)}"
                    
                    save_groq_btn.click(
                        fn=save_groq_config,
                        inputs=[groq_api_key_input, use_groq_checkbox, groq_model_select],
                        outputs=[groq_status]
                    )
                    
                    save_postgresql_btn.click(
                        fn=save_postgresql_config,
                        inputs=[postgresql_url_input, use_postgresql_checkbox],
                        outputs=[postgresql_status]
                    )
                
                # TAB 12: Servidor API
                with gr.Tab("🚀 Servidor API"):
                    gr.Markdown("### 🚀 Control del Servidor API para Widget Embeddable")
                    gr.Markdown("""
                    Inicia o detén el servidor API necesario para que el widget funcione en tu website.
                    
                    **📋 El servidor API proporciona:**
                    - 🔗 Endpoints REST para el widget embeddable
                    - 📦 Servicio del archivo JavaScript del widget (/static/business-ai-widget.js)
                    - 🔌 Endpoints de chat para STAR AGENT
                    - 📚 Documentación interactiva en /docs
                    
                    **⚠️ IMPORTANTE:** El servidor API debe estar corriendo para que el widget funcione en tu website.
                    """)
                    
                    api_server_status = gr.Markdown(
                        value="**Estado:** No iniciado",
                        label="Estado del Servidor"
                    )
                    
                    api_server_port = gr.Number(
                        label="🔌 Puerto del Servidor API",
                        value=7864,
                        minimum=1000,
                        maximum=65535,
                        info="Puerto donde correrá el servidor API (por defecto: 7864)"
                    )
                    
                    with gr.Row():
                        start_api_server_btn = gr.Button("▶️ Iniciar Servidor API", variant="primary")
                        stop_api_server_btn = gr.Button("⏹️ Detener Servidor API", variant="stop")
                        check_api_server_btn = gr.Button("🔍 Verificar Estado", variant="secondary")
                    
                    api_server_logs = gr.Textbox(
                        label="📋 Logs del Servidor",
                        lines=10,
                        interactive=False,
                        value="Los logs aparecerán aquí cuando inicies el servidor..."
                    )
                    
                    def start_api_server(port):
                        """Inicia el servidor API en un thread separado"""
                        try:
                            import threading
                            import time
                            import sys
                            
                            # Verificar si ya está corriendo
                            try:
                                import requests
                                response = requests.get(f"http://127.0.0.1:{int(port)}/api/widget/health", timeout=2)
                                if response.status_code == 200:
                                    return f"✅ **Servidor API ya está corriendo en puerto {port}**\n\n**URL:** http://127.0.0.1:{port}", "Servidor ya está corriendo"
                            except:
                                pass
                            
                            # Verificar que tengamos referencia a StarAgentMode
                            if not self.star_agent_mode:
                                return "❌ **Error: No hay referencia a StarAgentMode.**\n\nReinicia la aplicación.", "Error: StarAgentMode no disponible"
                            
                            # Si ya hay un thread corriendo, detenerlo primero
                            if self.api_server_thread and self.api_server_thread.is_alive():
                                return "⚠️ **El servidor ya está corriendo.**\n\nUsa 'Detener Servidor API' primero.", "Servidor ya está corriendo"
                            
                            # Crear la app FastAPI
                            try:
                                widget_app = self.star_agent_mode.get_widget_app()
                                if not widget_app:
                                    return "❌ **Error: No se pudo crear la aplicación FastAPI.**\n\nVerifica que FastAPI esté instalado: pip install fastapi uvicorn", "Error creando app"
                            except Exception as e:
                                return f"❌ **Error creando aplicación:** {str(e)}", f"Error: {str(e)}"
                            
                            # Función para ejecutar uvicorn en el thread
                            def run_server():
                                try:
                                    import uvicorn
                                    uvicorn.run(
                                        widget_app,
                                        host="0.0.0.0",
                                        port=int(port),
                                        log_level="info"
                                    )
                                except Exception as e:
                                    print(f"❌ Error en servidor API: {e}")
                                    import traceback
                                    traceback.print_exc()
                            
                            # Iniciar thread del servidor
                            self.api_server_thread = threading.Thread(
                                target=run_server,
                                daemon=True,
                                name="API-Server-Thread"
                            )
                            self.api_server_thread.start()
                            self.api_server_running = True
                            self.api_server_port = int(port)
                            
                            # Esperar un poco para verificar que inició
                            time.sleep(2)
                            
                            # Verificar que está corriendo
                            try:
                                import requests
                                response = requests.get(f"http://127.0.0.1:{int(port)}/api/widget/health", timeout=2)
                                if response.status_code == 200:
                                    status = f"""✅ **Servidor API iniciado exitosamente en puerto {port}**

**URL del Servidor:** http://127.0.0.1:{port}
**Health Check:** http://127.0.0.1:{port}/api/widget/health
**Docs:** http://127.0.0.1:{port}/docs
**Widget JS:** http://127.0.0.1:{port}/static/business-ai-widget.js

**El servidor está corriendo en background.**
"""
                                    logs = f"Servidor iniciado en puerto {port}\nThread: {self.api_server_thread.name}\nThread ID: {self.api_server_thread.ident}"
                                    return status, logs
                            except Exception as e:
                                # El servidor puede estar iniciando aún
                                status = f"""⚠️ **Servidor API iniciando...**

**Puerto:** {port}

**Espera unos segundos y verifica el estado con el botón 'Verificar Estado'.**

Si el servidor no inicia, verifica que el puerto {port} no esté en uso.
"""
                                logs = f"Servidor iniciando en puerto {port}...\nError de verificación: {str(e)}"
                                return status, logs
                            
                            status = f"""✅ **Servidor API iniciado en puerto {port}**

**URL del Servidor:** http://127.0.0.1:{port}
"""
                            logs = f"Servidor iniciado en puerto {port}"
                            return status, logs
                        except Exception as e:
                            import traceback
                            error_detail = f"{str(e)}\n\n{traceback.format_exc()}"
                            return f"❌ **Error iniciando servidor:**\n\n{error_detail}", f"Error: {error_detail}"
                    
                    def stop_api_server(port):
                        """Detiene el servidor API"""
                        try:
                            if not self.api_server_thread or not self.api_server_thread.is_alive():
                                return "⚠️ **El servidor no está corriendo.**", "Servidor no está corriendo"
                            
                            # El servidor está corriendo en un thread daemon
                            # No podemos detenerlo directamente desde Python de forma limpia
                            # Por ahora, informamos que se detendrá cuando termine la aplicación
                            # O podríamos usar un flag compartido y modificar el servidor para escucharlo
                            
                            self.api_server_running = False
                            
                            # Verificar si realmente está corriendo
                            try:
                                import requests
                                response = requests.get(f"http://127.0.0.1:{int(port)}/api/widget/health", timeout=1)
                                if response.status_code == 200:
                                    return "⚠️ **Para detener el servidor completamente, reinicia la aplicación Gradio.**\n\nEl servidor se detendrá automáticamente cuando cierres la aplicación.", "Servidor seguirá corriendo hasta reiniciar"
                            except:
                                pass
                            
                            return "✅ **Servidor API detenido**\n\nEl thread se ha marcado como detenido.", "Servidor detenido"
                        except Exception as e:
                            return f"❌ Error: {str(e)}", f"Error: {str(e)}"
                    
                    def check_api_server_status(port):
                        """Verifica el estado del servidor API"""
                        try:
                            import requests
                            # Health endpoint está en /api/widget/health
                            response = requests.get(f"http://127.0.0.1:{int(port)}/api/widget/health", timeout=2)
                            if response.status_code == 200:
                                health_data = response.json()
                                status_text = health_data.get("status", "unknown")
                                return f"""✅ **Servidor API está corriendo**

**Puerto:** {port}
**Status:** {status_text}
**URL:** http://127.0.0.1:{port}
**Health:** http://127.0.0.1:{port}/api/widget/health
**Docs:** http://127.0.0.1:{port}/docs
**Widget JS:** http://127.0.0.1:{port}/static/business-ai-widget.js
"""
                            else:
                                return f"⚠️ **Servidor API responde con error**\n\n**Status Code:** {response.status_code}"
                        except requests.exceptions.ConnectionError:
                            return f"""❌ **Servidor API no está corriendo**

**Puerto:** {port}

Inicia el servidor usando el botón '▶️ Iniciar Servidor API' arriba.
"""
                        except Exception as e:
                            return f"❌ **Error verificando servidor:** {str(e)}"
                    
                    start_api_server_btn.click(
                        fn=start_api_server,
                        inputs=[api_server_port],
                        outputs=[api_server_status, api_server_logs]
                    )
                    
                    stop_api_server_btn.click(
                        fn=stop_api_server,
                        inputs=[api_server_port],
                        outputs=[api_server_status, api_server_logs]
                    )
                    
                    check_api_server_btn.click(
                        fn=check_api_server_status,
                        inputs=[api_server_port],
                        outputs=[api_server_status]
                    )
                
                # TAB 13: Instrucciones
                with gr.Tab("📖 Instrucciones"):
                    gr.Markdown("### 📖 Cómo Usar el Widget en tu Website")
                    gr.Markdown("""
                    ## Paso 1: Genera tu Código
                    
                    1. Ve a la pestaña **"🔧 Generar Código"**
                    2. Configura:
                       - URL de tu servidor STAR AGENT API
                       - Nombre de tu marca
                       - Color principal del widget
                       - Posición (derecha o izquierda)
                       - Mensaje de bienvenida
                    3. Haz click en **"📋 Generar Código"**
                    
                    ## Paso 2: Copia el Código
                    
                    Copia el código HTML que se genera
                    
                    ## Paso 3: Pega en tu Website
                    
                    1. Abre el código HTML de tu website
                    2. Busca la etiqueta `</body>`
                    3. Pega el código **ANTES** de `</body>`
                    4. Guarda y publica tu website
                    
                    ## Paso 4: ¡Listo!
                    
                    - El widget aparecerá automáticamente en tu website
                    - Los usuarios podrán chatear directamente
                    - El agente responderá usando STAR AGENT
                    
                    ---
                    
                    ## 🎯 Características del Widget
                    
                    Basado en los mejores papers de e-commerce:
                    - ✅ **Mix-ECom**: Manejo de diálogos mixtos (QA, recomendación, ventas, chit-chat)
                    - ✅ **Retail-GPT**: RAG para recomendaciones de productos
                    - ✅ **CSALES**: Personalización y persuasión estratégica
                    - ✅ **MegaChat**: Generación de respuestas de alta calidad
                    
                    **Funcionalidades:**
                    - 💬 Chat en tiempo real
                    - 🛒 Carrito de compras integrado
                    - 💳 Procesamiento de pagos
                    - 📦 Gestión de pedidos
                    - 🎯 Cross-selling inteligente
                    - 📊 Análisis de sentimiento
                    - 🔗 Handoff humano automático
                    - 🖼️ Procesamiento de imágenes
                    - 📍 Pixel tracking (sabe qué productos vio el usuario)
                    
                    ---
                    
                    ## 🔧 Configuración Avanzada
                    
                    **Personalización:**
                    - Cambia el color con `data-primary-color`
                    - Cambia la posición con `data-position`
                    - Personaliza el mensaje con `data-welcome-message`
                    
                    **Ejemplo completo:**
                    ```html
                    <script src="https://tu-servidor.com/static/business-ai-widget.js" 
                            data-api-url="https://tu-servidor.com"
                            data-widget-id="mi-widget-123"
                            data-brand-name="Mi Empresa"
                            data-primary-color="#ff6b6b"
                            data-position="bottom-left"
                            data-welcome-message="¡Hola! ¿Cómo puedo ayudarte?"
                            async></script>
                    ```
                    
                    ---
                    
                    ## ⚙️ Configuración Enterprise
                    
                    Para máxima velocidad y memoria:
                    1. Ve a la pestaña **"⚙️ Configuración Enterprise"**
                    2. Configura Groq para respuestas <0.5 segundos
                    3. Configura PostgreSQL para memoria de largo plazo
                    4. Guarda y reinicia el servidor
                    
                    ---
                    
                    ## 🚀 Servidor API
                    
                    El widget requiere que el servidor API esté corriendo:
                    1. Ve a la pestaña **"🚀 Servidor API"**
                    2. Configura el puerto (por defecto: 7864)
                    3. Inicia el servidor API
                    4. Verifica que esté corriendo con "Verificar Estado"
                    """)
            
            # Botones de acción
            with gr.Row():
                save_btn = gr.Button("💾 Guardar Configuración", variant="primary", size="lg")
                load_btn = gr.Button("📂 Cargar Configuración", variant="secondary")
                reset_btn = gr.Button("🔄 Restablecer a Valores por Defecto", variant="stop")
            
            save_status = gr.Textbox(label="Estado", interactive=False)
            
            # Funciones de callback
            def save_all_config(
                brand_name_val, tone_val, personality_val, instructions_val,
                lang_val, multilingual_val,
                web_enable, website_url_val,
                ig_enable, ig_token,
                fb_enable, fb_token, fb_page, fb_verify,
                google_enable, google_key, google_place,
                scheduler_interval, webhooks_enable,
                rag_enable, rag_k_val, verification_enable,
                sales_enable, sales_aggressiveness_val, objections_val,
                stripe_enable, stripe_key,
                ga_enable, ga_id,
                pixel_enable, pixel_id,
                base_url_val,
                product_catalog_link, store_link,
                checkout_link, payment_methods_link,
                support_link, contact_link, faq_link,
                shipping_link, returns_link, privacy_policy_link, terms_link,
                custom_links,
                widget_enable, widget_pos,
                whatsapp_enable, whatsapp_phone_id_val, whatsapp_token_val, whatsapp_verify_val,
                messenger_enable, messenger_page_id_val, messenger_token_val, messenger_verify_val,
                instagram_direct_enable,
                handoff_enable, handoff_provider_val,
                handoff_zendesk_subdomain, handoff_zendesk_token, handoff_zendesk_queue,
                handoff_whatsapp_token, handoff_email_val,
                handoff_trigger_manual, handoff_trigger_low_confidence,
                handoff_trigger_strong_objection, handoff_trigger_frustration,
                ingestion_scheduler_enable, ingestion_interval_hours_val,
                ingestion_website_enable, ingestion_website_url_val,
                ingestion_instagram_enable, ingestion_instagram_token_val,
                ingestion_facebook_enable, ingestion_facebook_token_val
            ):
                """Guarda toda la configuración."""
                config = {
                    "brand_name": brand_name_val,
                    "chatbot_tone": tone_val,
                    "chatbot_personality": personality_val,
                    "chatbot_custom_instructions": instructions_val,
                    "default_language": lang_val,
                    "multilingual_enabled": multilingual_val,
                    
                    # Ingesta
                    "enable_web_crawling": web_enable,
                    "website_url": website_url_val,
                    "enable_instagram": ig_enable,
                    "instagram_access_token": ig_token,
                    "enable_facebook": fb_enable,
                    "facebook_access_token": fb_token,
                    "facebook_page_id": fb_page,
                    "facebook_verify_token": fb_verify,
                    "enable_google": google_enable,
                    "google_business_api_key": google_key,
                    "google_place_id": google_place,
                    "scheduler_web_interval": scheduler_interval,
                    "enable_webhooks": webhooks_enable,
                    
                    # RAG
                    "rag_enabled": rag_enable,
                    "rag_k": rag_k_val,
                    "enable_verification": verification_enable,
                    
                    # Sales
                    "enable_sales_closer": sales_enable,
                    "sales_aggressiveness": sales_aggressiveness_val,
                    "objection_responses": objections_val if isinstance(objections_val, dict) else {},
                    
                    # Integraciones
                    "enable_stripe": stripe_enable,
                    "stripe_secret_key": stripe_key,
                    "enable_google_analytics": ga_enable,
                    "google_analytics_id": ga_id,
                    "enable_meta_pixel": pixel_enable,
                    "meta_pixel_id": pixel_id,
                    
                    # Links y URLs
                    "base_url": base_url_val,  # URL base para generar links de productos automáticamente
                    "product_catalog_link": product_catalog_link,
                    "store_link": store_link,
                    "checkout_link": checkout_link,
                    "payment_methods_link": payment_methods_link,
                    "support_link": support_link,
                    "contact_link": contact_link,
                    "faq_link": faq_link,
                    "shipping_link": shipping_link,
                    "returns_link": returns_link,
                    "privacy_policy_link": privacy_policy_link,
                    "terms_link": terms_link,
                    "custom_links": custom_links if isinstance(custom_links, dict) else {},
                    
                    # Canales
                    "enable_widget": widget_enable,
                    "widget_position": widget_pos,
                    "enable_whatsapp": whatsapp_enable,
                    "whatsapp_phone_number_id": whatsapp_phone_id_val,
                    "whatsapp_access_token": whatsapp_token_val,
                    "whatsapp_verify_token": whatsapp_verify_val,
                    "enable_messenger": messenger_enable,
                    "messenger_page_id": messenger_page_id_val,
                    "messenger_page_access_token": messenger_token_val,
                    "messenger_verify_token": messenger_verify_val,
                    "enable_instagram_direct": instagram_direct_enable,
                    
                    # Handoff a Humanos
                    "handoff_enabled": handoff_enable,
                    "handoff_provider": handoff_provider_val,
                    "handoff_zendesk_subdomain": handoff_zendesk_subdomain,
                    "handoff_zendesk_token": handoff_zendesk_token,
                    "handoff_zendesk_queue": handoff_zendesk_queue,
                    "handoff_whatsapp_token": handoff_whatsapp_token,
                    "handoff_email": handoff_email_val,
                    "handoff_triggers": {
                        "manual": handoff_trigger_manual,
                        "auto_low_confidence": handoff_trigger_low_confidence,
                        "auto_strong_objection": handoff_trigger_strong_objection,
                        "auto_frustration": handoff_trigger_frustration,
                    },
                    
                    # Ingesta Automática
                    "ingestion_scheduler_enabled": ingestion_scheduler_enable,
                    "ingestion_interval_hours": int(ingestion_interval_hours_val) if ingestion_interval_hours_val else 6,
                    "ingestion_website_enabled": ingestion_website_enable,
                    "ingestion_website_url": ingestion_website_url_val,
                    "ingestion_instagram_enabled": ingestion_instagram_enable,
                    "ingestion_instagram_token": ingestion_instagram_token_val,
                    "ingestion_facebook_enabled": ingestion_facebook_enable,
                    "ingestion_facebook_token": ingestion_facebook_token_val,
                }
                
                success, message = self._save_config(config)
                return message
            
            def load_config_ui():
                """Carga configuración y actualiza UI."""
                config = self._load_config()
                handoff_triggers = config.get("handoff_triggers", {})
                return (
                    config.get("brand_name", ""),
                    config.get("chatbot_tone", "friendly"),
                    config.get("chatbot_personality", ""),
                    config.get("chatbot_custom_instructions", ""),
                    config.get("default_language", "es"),
                    config.get("multilingual_enabled", False),
                    config.get("enable_web_crawling", False),
                    config.get("website_url", ""),
                    config.get("enable_instagram", False),
                    config.get("instagram_access_token", ""),
                    config.get("enable_facebook", False),
                    config.get("facebook_access_token", ""),
                    config.get("facebook_page_id", ""),
                    config.get("facebook_verify_token", ""),
                    config.get("enable_google", False),
                    config.get("google_business_api_key", ""),
                    config.get("google_place_id", ""),
                    config.get("scheduler_web_interval", 6),
                    config.get("enable_webhooks", True),
                    config.get("rag_enabled", True),
                    config.get("rag_k", 5),
                    config.get("enable_verification", True),
                    config.get("enable_sales_closer", True),
                    config.get("sales_aggressiveness", 5),
                    config.get("objection_responses", {}),
                    config.get("enable_stripe", False),
                    config.get("stripe_secret_key", ""),
                    config.get("enable_google_analytics", False),
                    config.get("google_analytics_id", ""),
                    config.get("enable_meta_pixel", False),
                    config.get("meta_pixel_id", ""),
                    config.get("base_url", ""),  # URL base para links de productos
                    config.get("product_catalog_link", ""),
                    config.get("store_link", ""),
                    config.get("checkout_link", ""),
                    config.get("payment_methods_link", ""),
                    config.get("support_link", ""),
                    config.get("contact_link", ""),
                    config.get("faq_link", ""),
                    config.get("shipping_link", ""),
                    config.get("returns_link", ""),
                    config.get("privacy_policy_link", ""),
                    config.get("terms_link", ""),
                    config.get("custom_links", {}),
                    config.get("enable_widget", True),
                    config.get("widget_position", "bottom-right"),
                    config.get("enable_whatsapp", False),
                    config.get("whatsapp_phone_number_id", ""),
                    config.get("whatsapp_access_token", ""),
                    config.get("whatsapp_verify_token", ""),
                    config.get("enable_messenger", False),
                    config.get("messenger_page_id", "") or config.get("facebook_page_id", ""),
                    config.get("messenger_page_access_token", "") or config.get("facebook_page_access_token", ""),
                    config.get("messenger_verify_token", "") or config.get("facebook_verify_token", ""),
                    config.get("enable_instagram_direct", False),
                    config.get("handoff_enabled", False),
                    config.get("handoff_provider", "none"),
                    config.get("handoff_zendesk_subdomain", ""),
                    config.get("handoff_zendesk_token", ""),
                    config.get("handoff_zendesk_queue", ""),
                    config.get("handoff_whatsapp_token", ""),
                    config.get("handoff_email", ""),
                    handoff_triggers.get("manual", True),
                    handoff_triggers.get("auto_low_confidence", False),
                    handoff_triggers.get("auto_strong_objection", False),
                    handoff_triggers.get("auto_frustration", False),
                    config.get("ingestion_scheduler_enabled", False),
                    config.get("ingestion_interval_hours", 6),
                    config.get("ingestion_website_enabled", False),
                    config.get("ingestion_website_url", ""),
                    config.get("ingestion_instagram_enabled", False),
                    config.get("ingestion_instagram_token", ""),
                    config.get("ingestion_facebook_enabled", False),
                    config.get("ingestion_facebook_token", ""),
                    "✅ Configuración cargada"
                )
            
            def reset_config():
                """Restablece a valores por defecto."""
                default_config = {
                    "brand_name": "",
                    "chatbot_tone": "friendly",
                    "chatbot_personality": "",
                    "chatbot_custom_instructions": "",
                    "default_language": "es",
                    "multilingual_enabled": False,
                    "enable_web_crawling": False,
                    "website_url": "",
                    "enable_instagram": False,
                    "instagram_access_token": "",
                    "enable_facebook": False,
                    "facebook_access_token": "",
                    "facebook_page_id": "",
                    "facebook_verify_token": "",
                    "enable_google": False,
                    "google_business_api_key": "",
                    "google_place_id": "",
                    "scheduler_web_interval": 6,
                    "enable_webhooks": True,
                    "rag_enabled": True,
                    "rag_k": 5,
                    "enable_verification": True,
                    "enable_sales_closer": True,
                    "sales_aggressiveness": 5,
                    "objection_responses": {},
                    "enable_stripe": False,
                    "stripe_secret_key": "",
                    "enable_google_analytics": False,
                    "google_analytics_id": "",
                    "enable_meta_pixel": False,
                    "meta_pixel_id": "",
                    "base_url": "",  # URL base para links de productos
                    "product_catalog_link": "",
                    "store_link": "",
                    "checkout_link": "",
                    "payment_methods_link": "",
                    "support_link": "",
                    "contact_link": "",
                    "faq_link": "",
                    "shipping_link": "",
                    "returns_link": "",
                    "privacy_policy_link": "",
                    "terms_link": "",
                    "custom_links": {},
                    "enable_widget": True,
                    "widget_position": "bottom-right",
                    "enable_whatsapp": False,
                    "whatsapp_phone_number_id": "",
                    "whatsapp_access_token": "",
                    "whatsapp_verify_token": "",
                    "enable_messenger": False,
                    "messenger_page_id": "",
                    "messenger_page_access_token": "",
                    "messenger_verify_token": "",
                    "enable_instagram_direct": False,
                    "handoff_enabled": False,
                    "handoff_provider": "none",
                    "handoff_zendesk_subdomain": "",
                    "handoff_zendesk_token": "",
                    "handoff_zendesk_queue": "",
                    "handoff_whatsapp_token": "",
                    "handoff_email": "",
                    "handoff_triggers": {
                        "manual": True,
                        "auto_low_confidence": False,
                        "auto_strong_objection": False,
                        "auto_frustration": False,
                    },
                    "ingestion_scheduler_enabled": False,
                    "ingestion_interval_hours": 6,
                    "ingestion_website_enabled": False,
                    "ingestion_website_url": "",
                    "ingestion_instagram_enabled": False,
                    "ingestion_instagram_token": "",
                    "ingestion_facebook_enabled": False,
                    "ingestion_facebook_token": "",
                }
                self._save_config(default_config)
                return load_config_ui()
            
            def process_documents(files):
                """Procesa documentos subidos y los agrega al RAG."""
                if not files:
                    return "⚠️ No se seleccionaron archivos"
                
                try:
                    # Obtener AdvancedRAGManager del agente
                    if not self.star_agent_mode or not hasattr(self.star_agent_mode, 'agent'):
                        return "❌ Error: Agente no disponible. Inicia el servidor API primero."
                    
                    agent = self.star_agent_mode.agent
                    advanced_rag = None
                    
                    # Obtener advanced_rag del agente
                    if hasattr(agent, 'advanced_rag') and agent.advanced_rag:
                        advanced_rag = agent.advanced_rag
                    elif hasattr(agent, 'react_agent') and hasattr(agent.react_agent, 'advanced_rag'):
                        advanced_rag = agent.react_agent.advanced_rag
                    else:
                        return "❌ Error: RAG no disponible. ¿Está habilitado RAG Avanzado?"
                    
                    if not advanced_rag:
                        return "❌ Error: AdvancedRAGManager no inicializado."
                    
                    # Procesar cada archivo
                    from langchain_community.document_loaders import PyPDFLoader, TextLoader, Docx2txtLoader
                    from langchain.text_splitter import RecursiveCharacterTextSplitter
                    from langchain_core.documents import Document
                    from pathlib import Path
                    
                    processed_count = 0
                    total_docs = 0
                    
                    text_splitter = RecursiveCharacterTextSplitter(
                        chunk_size=1000,
                        chunk_overlap=200,
                        length_function=len,
                    )
                    
                    all_documents = []
                    
                    for file_path in files:
                        try:
                            file_path_obj = Path(file_path)
                            file_ext = file_path_obj.suffix.lower()
                            
                            # Cargar documento según extensión
                            if file_ext == '.pdf':
                                loader = PyPDFLoader(file_path)
                                docs = loader.load()
                            elif file_ext in ['.txt', '.md']:
                                loader = TextLoader(file_path, encoding='utf-8')
                                docs = loader.load()
                            elif file_ext in ['.docx', '.doc']:
                                loader = Docx2txtLoader(file_path)
                                docs = loader.load()
                            else:
                                return f"❌ Formato no soportado: {file_ext}. Soporta: PDF, TXT, MD, DOCX"
                            
                            # Dividir en chunks
                            chunks = text_splitter.split_documents(docs)
                            all_documents.extend(chunks)
                            processed_count += 1
                            total_docs += len(chunks)
                            
                        except Exception as e:
                            return f"❌ Error procesando {Path(file_path).name}: {str(e)}"
                    
                    # Agregar todos los documentos al RAG
                    if all_documents:
                        advanced_rag.add_documents(all_documents)
                        return f"✅ {processed_count} archivo(s) procesado(s), {total_docs} fragmentos agregados a la base de conocimiento RAG. El agente ahora puede usar esta información."
                    else:
                        return "⚠️ No se pudieron procesar los documentos."
                        
                except ImportError as e:
                    return f"❌ Error: Dependencias faltantes. Instala: pip install pypdf langchain-community python-docx"
                except Exception as e:
                    import traceback
                    return f"❌ Error procesando documentos: {str(e)}\n\n{traceback.format_exc()}"
            
            def refresh_metrics():
                """Actualiza métricas."""
                # Por ahora retorna métricas de ejemplo
                # En producción, se obtendrían del WidgetOptimizer
                return {
                    "total_requests": 0,
                    "conversions": 0,
                    "conversion_rate": 0.0,
                    "total_revenue": 0.0,
                    "drop_off_rate": 0.0,
                    "avg_response_time": 0.0,
                }
            
            # Función para ejecutar ingesta manualmente
            def run_ingestion_manual():
                """Ejecuta ingesta manualmente (Run now)."""
                try:
                    # Cargar configuración actual
                    config = self._load_config()
                    
                    # Crear scheduler temporal para ejecución
                    from ..ingestion.ingestion_scheduler import IngestionScheduler
                    
                    scheduler = IngestionScheduler(
                        enabled=False,  # No iniciar scheduler, solo ejecutar manualmente
                        interval_hours=config.get("ingestion_interval_hours", 6),
                        website_enabled=config.get("ingestion_website_enabled", False),
                        website_url=config.get("ingestion_website_url"),
                        instagram_enabled=config.get("ingestion_instagram_enabled", False),
                        instagram_token=config.get("ingestion_instagram_token"),
                        facebook_enabled=config.get("ingestion_facebook_enabled", False),
                        facebook_token=config.get("ingestion_facebook_token"),
                        rag_manager=None,  # Se integrará con RAG manager del agente
                    )
                    
                    results = scheduler.run_ingestion_now()
                    
                    # Formatear resultado
                    status_parts = []
                    for source, result in results.items():
                        if result.get("success"):
                            status_parts.append(f"✅ {source.upper()}: {result.get('message', 'Completado')}")
                        elif result.get("message"):
                            status_parts.append(f"ℹ️ {source.upper()}: {result.get('message', 'No ejecutado')}")
                    
                    if not status_parts:
                        return "⚠️ No hay fuentes habilitadas para ingesta"
                    
                    return "\n".join(status_parts)
                except Exception as e:
                    return f"❌ Error ejecutando ingesta: {e}"
            
            # Conectar callbacks
            save_btn.click(
                fn=save_all_config,
                inputs=[
                    brand_name, chatbot_tone, chatbot_personality, chatbot_custom_instructions,
                    default_language, multilingual_enabled,
                    enable_web_crawling, website_url,
                    enable_instagram, instagram_access_token,
                    enable_facebook, facebook_access_token, facebook_page_id, facebook_verify_token,
                    enable_google, google_business_api_key, google_place_id,
                    scheduler_web_interval, enable_webhooks,
                    rag_enabled, rag_k, enable_verification,
                    enable_sales_closer, sales_aggressiveness, objection_responses,
                    enable_stripe, stripe_secret_key,
                    enable_google_analytics, google_analytics_id,
                    enable_meta_pixel, meta_pixel_id,
                    base_url,  # Agregar base_url aquí en load outputs
                    product_catalog_link, store_link,
                    checkout_link, payment_methods_link,
                    support_link, contact_link, faq_link,
                    shipping_link, returns_link, privacy_policy_link, terms_link,
                    custom_links,
                    enable_widget, widget_position,
                    enable_whatsapp, whatsapp_phone_number_id, whatsapp_access_token, whatsapp_verify_token,
                    enable_messenger, messenger_page_id, messenger_page_access_token, messenger_verify_token,
                    enable_instagram_direct,
                    # Handoff inputs
                    enable_handoff, handoff_provider,
                    handoff_zendesk_subdomain, handoff_zendesk_token, handoff_zendesk_queue,
                    handoff_whatsapp_token, handoff_email,
                    handoff_trigger_manual, handoff_trigger_low_confidence,
                    handoff_trigger_strong_objection, handoff_trigger_frustration,
                    # Ingestion inputs
                    ingestion_scheduler_enabled, ingestion_interval_hours,
                    ingestion_website_enabled, ingestion_website_url,
                    ingestion_instagram_enabled, ingestion_instagram_token,
                    ingestion_facebook_enabled, ingestion_facebook_token,
                ],
                outputs=[save_status]
            )
            
            load_btn.click(
                fn=load_config_ui,
                outputs=[
                    brand_name, chatbot_tone, chatbot_personality, chatbot_custom_instructions,
                    default_language, multilingual_enabled,
                    enable_web_crawling, website_url,
                    enable_instagram, instagram_access_token,
                    enable_facebook, facebook_access_token, facebook_page_id, facebook_verify_token,
                    enable_google, google_business_api_key, google_place_id,
                    scheduler_web_interval, enable_webhooks,
                    rag_enabled, rag_k, enable_verification,
                    enable_sales_closer, sales_aggressiveness, objection_responses,
                    enable_stripe, stripe_secret_key,
                    enable_google_analytics, google_analytics_id,
                    enable_meta_pixel, meta_pixel_id,
                    base_url,  # Agregar base_url aquí en load outputs
                    product_catalog_link, store_link,
                    checkout_link, payment_methods_link,
                    support_link, contact_link, faq_link,
                    shipping_link, returns_link, privacy_policy_link, terms_link,
                    custom_links,
                    enable_widget, widget_position,
                    enable_whatsapp, whatsapp_phone_number_id, whatsapp_access_token, whatsapp_verify_token,
                    enable_messenger, messenger_page_id, messenger_page_access_token, messenger_verify_token,
                    enable_instagram_direct,
                    enable_handoff, handoff_provider,
                    handoff_zendesk_subdomain, handoff_zendesk_token, handoff_zendesk_queue,
                    handoff_whatsapp_token, handoff_email,
                    handoff_trigger_manual, handoff_trigger_low_confidence,
                    handoff_trigger_strong_objection, handoff_trigger_frustration,
                    ingestion_scheduler_enabled, ingestion_interval_hours,
                    ingestion_website_enabled, ingestion_website_url,
                    ingestion_instagram_enabled, ingestion_instagram_token,
                    ingestion_facebook_enabled, ingestion_facebook_token,
                    save_status,
                ]
            )
            
            reset_btn.click(fn=reset_config, outputs=[
                brand_name, chatbot_tone, chatbot_personality, chatbot_custom_instructions,
                default_language, multilingual_enabled,
                enable_web_crawling, website_url,
                enable_instagram, instagram_access_token,
                enable_facebook, facebook_access_token, facebook_page_id, facebook_verify_token,
                enable_google, google_business_api_key, google_place_id,
                scheduler_web_interval, enable_webhooks,
                rag_enabled, rag_k, enable_verification,
                enable_sales_closer, sales_aggressiveness, objection_responses,
                enable_stripe, stripe_secret_key,
                enable_google_analytics, google_analytics_id,
                enable_meta_pixel, meta_pixel_id,
                enable_widget, widget_position,
                enable_whatsapp, whatsapp_phone_number_id, whatsapp_access_token, whatsapp_verify_token,
                enable_messenger, messenger_page_id, messenger_page_access_token, messenger_verify_token,
                enable_instagram_direct,
                save_status,
            ])
            
            upload_btn.click(fn=process_documents, inputs=[document_upload], outputs=[upload_status])
            refresh_metrics_btn.click(fn=refresh_metrics, outputs=[metrics_display])
            
            # Botón Run now para ingesta
            run_ingestion_now_btn.click(
                fn=run_ingestion_manual,
                inputs=[],
                outputs=[ingestion_status]
            )
        
        return demo
    
    def launch(self, share: bool = False, server_name: str = "127.0.0.1", server_port: int = 7860):
        """
        Lanza la UI de Gradio.
        
        Args:
            share: Crear link público (Gradio share)
            server_name: Dirección del servidor
            server_port: Puerto del servidor
        """
        demo = self.create_ui()
        demo.launch(share=share, server_name=server_name, server_port=server_port)

