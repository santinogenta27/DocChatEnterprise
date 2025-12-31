"""
Cargador de Configuración del Chatbot desde JSON.

Lee configuración guardada desde la UI de Gradio y la aplica al agente.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any, Optional


class ChatbotConfigLoader:
    """
    Carga configuración del chatbot desde archivo JSON.
    
    La configuración se guarda desde la UI de Gradio.
    """
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Inicializa el cargador de configuración.
        
        Args:
            config_path: Ruta al archivo JSON de configuración
        """
        self.config_path = config_path or Path("docchat/star_agent/config/star_agent_config.json")
    
    def load(self) -> Dict[str, Any]:
        """
        Carga configuración desde JSON.
        
        Returns:
            Dict con toda la configuración
        """
        if not self.config_path.exists():
            return {}
        
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Error cargando configuración: {e}")
            return {}
    
    def apply_to_config(self, app_config):
        """
        Aplica configuración cargada a AppConfig.
        
        Args:
            app_config: Instancia de AppConfig
            
        Returns:
            AppConfig actualizado
        """
        config_dict = self.load()
        
        if not config_dict:
            return app_config
        
        # Aplicar configuración básica
        if "brand_name" in config_dict:
            app_config.app_name = config_dict["brand_name"]
        
        if "chatbot_tone" in config_dict:
            app_config.chatbot_tone = config_dict["chatbot_tone"]
        
        if "chatbot_personality" in config_dict:
            app_config.chatbot_personality = config_dict["chatbot_personality"]
        
        if "chatbot_custom_instructions" in config_dict:
            app_config.chatbot_custom_instructions = config_dict["chatbot_custom_instructions"]
        
        if "default_language" in config_dict:
            app_config.chatbot_default_language = config_dict["default_language"]
        
        if "multilingual_enabled" in config_dict:
            app_config.chatbot_multilingual_enabled = config_dict["multilingual_enabled"]
        
        # Aplicar configuración de ingesta automática
        if "enable_auto_ingestion" in config_dict:
            app_config.enable_auto_ingestion = config_dict["enable_auto_ingestion"]
        
        if "website_url" in config_dict:
            app_config.website_url = config_dict["website_url"]
        
        if "instagram_access_token" in config_dict:
            app_config.instagram_access_token = config_dict["instagram_access_token"]
        
        if "facebook_access_token" in config_dict:
            app_config.facebook_access_token = config_dict["facebook_access_token"]
        
        if "facebook_page_id" in config_dict:
            app_config.facebook_page_id = config_dict["facebook_page_id"]
        
        if "google_business_api_key" in config_dict:
            app_config.google_business_api_key = config_dict["google_business_api_key"]
        
        if "google_place_id" in config_dict:
            app_config.google_place_id = config_dict["google_place_id"]
        
        # Aplicar configuración de WhatsApp
        if "enable_whatsapp" in config_dict:
            app_config.enable_whatsapp = config_dict["enable_whatsapp"]
        
        if "whatsapp_phone_number_id" in config_dict:
            app_config.whatsapp_phone_number_id = config_dict["whatsapp_phone_number_id"]
        
        if "whatsapp_access_token" in config_dict:
            app_config.whatsapp_access_token = config_dict["whatsapp_access_token"]
        
        if "whatsapp_verify_token" in config_dict:
            app_config.whatsapp_verify_token = config_dict["whatsapp_verify_token"]
        
        # Aplicar configuración de Messenger
        if "enable_messenger" in config_dict:
            app_config.enable_messenger = config_dict["enable_messenger"]
        
        if "facebook_page_access_token" in config_dict:
            app_config.facebook_page_access_token = config_dict["facebook_page_access_token"]
        
        # Aplicar configuración de RAG
        if "rag_enabled" in config_dict:
            app_config.chatbot_rag_enabled = config_dict["rag_enabled"]
        
        # Aplicar configuración de Stripe
        if "enable_stripe" in config_dict and config_dict["enable_stripe"]:
            if "stripe_secret_key" in config_dict:
                # Guardar en variable de entorno para que PaymentTool lo use
                import os
                stripe_key = config_dict["stripe_secret_key"]
                os.environ["STRIPE_SECRET_KEY"] = stripe_key
                os.environ["STRIPE_API_KEY"] = stripe_key  # También como STRIPE_API_KEY para compatibilidad
                # Guardar en app_config para Sales Closer Elite
                app_config.stripe_api_key = stripe_key
        
        # Cargar base_url para generar links de productos automáticamente
        if "base_url" in config_dict:
            app_config.base_url = config_dict["base_url"]
            # También guardar como variable de entorno para uso directo
            import os
            os.environ["BASE_URL"] = config_dict["base_url"]
        
        # Cargar links configurados si existen
        links_fields = [
            "product_catalog_link", "store_link", "checkout_link", "payment_methods_link",
            "support_link", "contact_link", "faq_link", "shipping_link",
            "returns_link", "privacy_policy_link", "terms_link", "custom_links"
        ]
        if any(field in config_dict for field in links_fields):
            # Guardar links en app_config para acceso del agente
            for field in links_fields:
                if field in config_dict:
                    setattr(app_config, field, config_dict[field])
        
        # Guardar configuración de handoff en app_config (no se aplica directamente, se usa desde UI)
        handoff_fields = [
            "handoff_enabled", "handoff_provider", "handoff_zendesk_subdomain",
            "handoff_zendesk_token", "handoff_zendesk_queue", "handoff_whatsapp_token",
            "handoff_email", "handoff_triggers"
        ]
        for field in handoff_fields:
            if field in config_dict:
                setattr(app_config, field, config_dict[field])
        
        # Guardar configuración de ingesta automática en app_config
        ingestion_fields = [
            "ingestion_scheduler_enabled", "ingestion_interval_hours",
            "ingestion_website_enabled", "ingestion_website_url",
            "ingestion_instagram_enabled", "ingestion_instagram_token",
            "ingestion_facebook_enabled", "ingestion_facebook_token"
        ]
        for field in ingestion_fields:
            if field in config_dict:
                setattr(app_config, field, config_dict[field])
        
        return app_config

