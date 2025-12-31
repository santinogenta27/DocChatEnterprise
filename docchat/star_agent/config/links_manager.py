"""
Links Manager - Gestor de Links para STAR AGENT.

Permite que el agente acceda a links configurados desde la UI
y los use/envíe a los clientes dinámicamente.

Integrado con IntentLinkMapper para las 3 capas obligatorias:
1. Detectar INTENCIÓN
2. Mapear INTENCIÓN → TIPO DE LINK
3. Gate de CUÁNDO enviar
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, List

from .intent_link_mapper import IntentLinkMapper, UserIntent, LinkType


class LinksManager:
    """
    Gestor de links configurados para el agente.
    
    Carga links desde la configuración guardada y los proporciona
    al agente para usar en respuestas.
    """
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Inicializa el LinksManager.
        
        Args:
            config_path: Ruta al archivo de configuración JSON
        """
        self.config_path = config_path or Path("docchat/star_agent/config/star_agent_config.json")
        self._links_cache: Optional[Dict[str, str]] = None
        self._custom_links_cache: Optional[Dict[str, str]] = None
        self.intent_mapper = IntentLinkMapper()  # Mapper de intención → link
    
    def _load_config(self) -> Dict[str, Any]:
        """Carga configuración desde JSON."""
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️ Error cargando configuración de links: {e}")
        return {}
    
    def _refresh_cache(self):
        """Refresca el cache de links desde la configuración."""
        config = self._load_config()
        
        # Links estándar (mapeo directo a LinkType)
        self._links_cache = {
            LinkType.CATALOG.value: config.get("product_catalog_link", ""),
            LinkType.STORE.value: config.get("store_link", ""),
            LinkType.CHECKOUT.value: config.get("checkout_link", ""),
            LinkType.PAYMENT_METHODS.value: config.get("payment_methods_link", ""),
            LinkType.SUPPORT.value: config.get("support_link", ""),
            LinkType.CONTACT.value: config.get("contact_link", ""),
            LinkType.FAQ.value: config.get("faq_link", ""),
            LinkType.SHIPPING.value: config.get("shipping_link", ""),
            LinkType.RETURNS.value: config.get("returns_link", ""),
            LinkType.PRIVACY_POLICY.value: config.get("privacy_policy_link", ""),
            LinkType.TERMS.value: config.get("terms_link", ""),
            # Mantener compatibilidad con nombres antiguos
            "product_catalog": config.get("product_catalog_link", ""),
            "store": config.get("store_link", ""),
            "checkout": config.get("checkout_link", ""),
            "payment_methods": config.get("payment_methods_link", ""),
            "support": config.get("support_link", ""),
            "contact": config.get("contact_link", ""),
            "faq": config.get("faq_link", ""),
            "shipping": config.get("shipping_link", ""),
            "returns": config.get("returns_link", ""),
            "privacy_policy": config.get("privacy_policy_link", ""),
            "terms": config.get("terms_link", ""),
        }
        
        # Links personalizados
        self._custom_links_cache = config.get("custom_links", {})
        if not isinstance(self._custom_links_cache, dict):
            self._custom_links_cache = {}
    
    def get_link(self, link_type: str) -> Optional[str]:
        """
        Obtiene un link específico por tipo.
        
        Args:
            link_type: Tipo de link (product_catalog, store, checkout, support, etc.)
                      o etiqueta de link personalizado
        
        Returns:
            URL del link o None si no existe
        """
        if self._links_cache is None:
            self._refresh_cache()
        
        # Buscar en links estándar
        link = self._links_cache.get(link_type)
        if link:
            return link
        
        # Buscar en links personalizados
        if self._custom_links_cache and link_type in self._custom_links_cache:
            return self._custom_links_cache[link_type]
        
        return None
    
    def get_all_links(self) -> Dict[str, str]:
        """
        Obtiene todos los links disponibles.
        
        Returns:
            Dict con todos los links (estándar + personalizados)
        """
        if self._links_cache is None:
            self._refresh_cache()
        
        all_links = {k: v for k, v in self._links_cache.items() if v}
        if self._custom_links_cache:
            all_links.update(self._custom_links_cache)
        
        return all_links
    
    def get_links_by_category(self, category: str) -> Dict[str, str]:
        """
        Obtiene links de una categoría específica.
        
        Args:
            category: Categoría (products, payment, support, policies, custom)
        
        Returns:
            Dict con links de la categoría
        """
        if self._links_cache is None:
            self._refresh_cache()
        
        categories = {
            "products": ["product_catalog", "store"],
            "payment": ["checkout", "payment_methods"],
            "support": ["support", "contact", "faq"],
            "policies": ["shipping", "returns", "privacy_policy", "terms"],
        }
        
        if category == "custom":
            return self._custom_links_cache or {}
        
        category_links = categories.get(category, [])
        return {k: v for k, v in self._links_cache.items() if k in category_links and v}
    
    def format_link_in_response(self, link_type: str, label: Optional[str] = None) -> str:
        """
        Formatea un link para incluir en una respuesta del agente.
        
        Args:
            link_type: Tipo de link
            label: Etiqueta personalizada (si no se provee, usa el tipo)
        
        Returns:
            String formateado con el link o mensaje si no existe
        """
        link = self.get_link(link_type)
        if not link:
            return ""
        
        label = label or link_type.replace("_", " ").title()
        return f"[{label}]({link})"
    
    def get_link_for_intent(self, intent: UserIntent, sales_stage: Optional[str] = None) -> Optional[str]:
        """
        Obtiene el link correcto para una intención específica (CAPA 2).
        
        Implementa el mapeo INTENCIÓN → TIPO DE LINK → URL.
        
        Args:
            intent: Intención detectada del usuario
            sales_stage: Etapa de venta (opcional, para gate)
            
        Returns:
            URL del link correspondiente o None
        """
        # Gate de CUÁNDO enviar (CAPA 3)
        if not self.intent_mapper.should_include_link(intent, sales_stage):
            return None
        
        # Mapear INTENCIÓN → TIPO DE LINK (CAPA 2)
        link_type = self.intent_mapper.get_link_type_for_intent(intent)
        if not link_type:
            return None
        
        # Obtener URL del link
        return self.get_link(link_type.value)
    
    def format_link_for_intent(self, intent: UserIntent, sales_stage: Optional[str] = None, label: Optional[str] = None) -> str:
        """
        Formatea un link para una intención específica.
        
        Args:
            intent: Intención detectada
            sales_stage: Etapa de venta
            label: Etiqueta personalizada para el link
            
        Returns:
            Link formateado en Markdown o string vacío
        """
        link_url = self.get_link_for_intent(intent, sales_stage)
        if not link_url:
            return ""
        
        link_type = self.intent_mapper.get_link_type_for_intent(intent)
        if not link_type:
            return ""
        
        # Generar label si no se proporciona
        if not label:
            label_map = {
                LinkType.CATALOG: "Ver catálogo",
                LinkType.CHECKOUT: "Ir al checkout",
                LinkType.PAYMENT_METHODS: "Ver métodos de pago",
                LinkType.SHIPPING: "Ver info de envíos",
                LinkType.RETURNS: "Ver política de devoluciones",
                LinkType.SUPPORT: "Contactar soporte",
                LinkType.FAQ: "Ver preguntas frecuentes",
                LinkType.CONTACT: "Contactar",
                LinkType.STORE: "Ir a la tienda",
            }
            label = label_map.get(link_type, link_type.value.replace("_", " ").title())
        
        return f"[{label}]({link_url})"
    
    def get_relevant_links_for_query(self, query: str, sales_stage: Optional[str] = None) -> List[str]:
        """
        Obtiene links relevantes para una consulta usando el sistema de 3 capas.
        
        Implementa:
        1. Detecta INTENCIÓN (CAPA 1)
        2. Mapea INTENCIÓN → TIPO DE LINK (CAPA 2)
        3. Aplica gate de CUÁNDO enviar (CAPA 3)
        
        Args:
            query: Consulta del usuario
            sales_stage: Etapa de venta (opcional)
        
        Returns:
            Lista de links formateados relevantes para la consulta
        """
        # CAPA 1: Detectar INTENCIÓN
        intent = self.intent_mapper.detect_intent(query, sales_stage)
        
        # CAPA 2 + 3: Mapear y aplicar gate
        link_formatted = self.format_link_for_intent(intent, sales_stage)
        
        if link_formatted:
            return [link_formatted]
        
        return []

