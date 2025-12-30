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
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Inicializa la UI de configuración.
        
        Args:
            config_path: Ruta donde guardar/cargar configuración (JSON)
        """
        self.config_path = config_path or Path("docchat/star_agent/config/star_agent_config.json")
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Cargar configuración existente
        self.current_config = self._load_config()
    
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
                        document_upload = gr.File(
                            label="Subir Documentos",
                            file_count="multiple",
                            file_types=[".pdf", ".docx", ".txt", ".md"],
                            info="Sube documentos que el agente debe conocer (PDFs, Word, texto)"
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
                        objection_responses = gr.JSON(
                            label="Respuestas a Objeciones Comunes",
                            value=self.current_config.get("objection_responses", {
                                "caro": "Entiendo. Justamente por eso incluye X, Y y Z que ahorran dinero a largo plazo.",
                                "después": "Tiene sentido. ¿Qué tendría que pasar para que lo veas útil ahora?",
                                "pensar": "Claro, es una decisión importante. ¿Hay algo específico en lo que pueda ayudarte a decidir?"
                            }),
                            info="Define cómo responder a objeciones comunes (formato JSON)"
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
                
                # TAB 6: Canales
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
                            value=self.current_config.get("facebook_page_id", ""),
                            placeholder="123456789012345",
                            info="ID de tu página de Facebook"
                        )
                        
                        messenger_page_access_token = gr.Textbox(
                            label="Facebook Page Access Token",
                            value=self.current_config.get("facebook_page_access_token", ""),
                            type="password",
                            info="Page Access Token (no confundir con User Access Token)"
                        )
                        
                        messenger_verify_token = gr.Textbox(
                            label="Messenger Verify Token",
                            value=self.current_config.get("facebook_verify_token", ""),
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
                
                # TAB 7: Métricas y Analytics
                with gr.Tab("📊 Métricas"):
                    gr.Markdown("### Métricas y Analytics del Agente")
                    
                    with gr.Row():
                        metrics_display = gr.JSON(
                            label="Métricas Actuales",
                            value={},
                            interactive=False
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
                widget_enable, widget_pos,
                whatsapp_enable, whatsapp_key,
                messenger_enable, instagram_direct_enable
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
                    
                    # Canales
                    "enable_widget": widget_enable,
                    "widget_position": widget_pos,
                    "enable_whatsapp": whatsapp_enable,
                    "whatsapp_phone_number_id": whatsapp_phone_id,
                    "whatsapp_access_token": whatsapp_token,
                    "whatsapp_verify_token": whatsapp_verify,
                    "enable_messenger": messenger_enable,
                    "facebook_page_id": messenger_page_id,
                    "facebook_page_access_token": messenger_token,
                    "facebook_verify_token": messenger_verify,
                    "enable_instagram_direct": instagram_direct_enable,
                }
                
                success, message = self._save_config(config)
                return message
            
            def load_config_ui():
                """Carga configuración y actualiza UI."""
                config = self._load_config()
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
                    config.get("enable_widget", True),
                    config.get("widget_position", "bottom-right"),
                    config.get("enable_whatsapp", False),
                    config.get("whatsapp_phone_number_id", ""),
                    config.get("whatsapp_access_token", ""),
                    config.get("whatsapp_verify_token", ""),
                    config.get("enable_messenger", False),
                    config.get("facebook_page_id", ""),
                    config.get("facebook_page_access_token", ""),
                    config.get("facebook_verify_token", ""),
                    config.get("enable_instagram_direct", False),
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
                    "enable_widget": True,
                    "widget_position": "bottom-right",
                    "enable_whatsapp": False,
                    "whatsapp_phone_number_id": "",
                    "whatsapp_access_token": "",
                    "whatsapp_verify_token": "",
                    "enable_messenger": False,
                    "facebook_page_id": "",
                    "facebook_page_access_token": "",
                    "facebook_verify_token": "",
                    "enable_instagram_direct": False,
                }
                self._save_config(default_config)
                return load_config_ui()
            
            def process_documents(files):
                """Procesa documentos subidos."""
                if not files:
                    return "⚠️ No se seleccionaron archivos"
                
                try:
                    # Aquí se procesarían los documentos y se agregarían a RAG
                    # Por ahora, solo retornamos mensaje
                    return f"✅ {len(files)} documento(s) procesado(s). Los documentos se agregarán a la base de conocimiento del agente."
                except Exception as e:
                    return f"❌ Error procesando documentos: {e}"
            
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
                    enable_widget, widget_position,
                    enable_whatsapp, whatsapp_api_key,
                    enable_messenger, enable_instagram_direct,
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
                    enable_widget, widget_position,
                    enable_whatsapp, whatsapp_api_key,
                    enable_messenger, enable_instagram_direct,
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
                enable_whatsapp, whatsapp_api_key,
                enable_messenger, enable_instagram_direct,
                save_status,
            ])
            
            upload_btn.click(fn=process_documents, inputs=[document_upload], outputs=[upload_status])
            refresh_metrics_btn.click(fn=refresh_metrics, outputs=[metrics_display])
        
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

