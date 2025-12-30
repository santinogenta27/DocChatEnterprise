"""
Links Manager - Gestor de Links para STAR AGENT.

Permite que el agente acceda a links configurados desde la UI
y los use/envíe a los clientes dinámicamente.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, List


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
        
        # Links estándar
        self._links_cache = {
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
    
    def get_relevant_links_for_query(self, query: str) -> List[str]:
        """
        Obtiene links relevantes para una consulta del usuario.
        
        Args:
            query: Consulta del usuario
        
        Returns:
            Lista de links formateados relevantes para la consulta
        """
        query_lower = query.lower()
        relevant_links = []
        
        # Mapeo de palabras clave a tipos de links
        keyword_mapping = {
            "producto": "product_catalog",
            "catálogo": "product_catalog",
            "tienda": "store",
            "comprar": "checkout",
            "pagar": "checkout",
            "pago": "payment_methods",
            "método de pago": "payment_methods",
            "soporte": "support",
            "ayuda": "support",
            "contacto": "contact",
            "pregunta": "faq",
            "frecuente": "faq",
            "envío": "shipping",
            "entrega": "shipping",
            "devolución": "returns",
            "política": "privacy_policy",
            "privacidad": "privacy_policy",
            "término": "terms",
            "condición": "terms",
        }
        
        for keyword, link_type in keyword_mapping.items():
            if keyword in query_lower:
                link = self.get_link(link_type)
                if link:
                    formatted = self.format_link_in_response(link_type)
                    if formatted and formatted not in relevant_links:
                        relevant_links.append(formatted)
        
        return relevant_links

