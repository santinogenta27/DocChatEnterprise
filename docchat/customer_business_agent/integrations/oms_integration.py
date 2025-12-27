"""
OMS Integration - Integración con Order Management Systems
Soporta APIs genéricas y sistemas legacy
"""

from __future__ import annotations

import requests
import json
from typing import Dict, Any, Optional, List
from enum import Enum
from dataclasses import dataclass


class OMSType(Enum):
    """Tipos de OMS soportados."""
    SHOPIFY = "shopify"
    WOOCOMMERCE = "woocommerce"
    CUSTOM = "custom"  # Para APIs personalizadas
    LEGACY = "legacy"  # Para sistemas legacy con adaptadores


@dataclass
class OrderUpdate:
    """Modelo de actualización de orden."""
    order_id: str
    delivery_address: Optional[Dict[str, Any]] = None
    delivery_date: Optional[str] = None
    tracking_number: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class OMSIntegration:
    """
    Integración con Order Management Systems.
    
    Permite:
    - Obtener estado de órdenes
    - Actualizar direcciones de entrega
    - Agregar tracking numbers
    - Cambiar fechas de entrega
    - Actualizar estado de órdenes
    """
    
    def __init__(
        self,
        oms_type: OMSType,
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
        api_secret: Optional[str] = None,
        **kwargs
    ):
        """
        Inicializa integración con OMS.
        
        Args:
            oms_type: Tipo de OMS
            api_key: API key
            api_url: URL base de API
            api_secret: API secret (para algunos sistemas)
        """
        self.oms_type = oms_type
        self.api_key = api_key
        self.api_url = api_url
        self.api_secret = api_secret
        self.extra_config = kwargs
        
        self.headers = self._get_headers()
    
    def _get_headers(self) -> Dict[str, str]:
        """Obtiene headers apropiados según tipo de OMS."""
        headers = {"Content-Type": "application/json"}
        
        if self.oms_type == OMSType.SHOPIFY:
            headers["X-Shopify-Access-Token"] = self.api_key
        elif self.oms_type == OMSType.WOOCOMMERCE:
            # WooCommerce usa Basic Auth
            import base64
            credentials = f"{self.api_key}:{self.api_secret}"
            encoded = base64.b64encode(credentials.encode()).decode()
            headers["Authorization"] = f"Basic {encoded}"
        elif self.oms_type == OMSType.CUSTOM:
            if "headers" in self.extra_config:
                headers.update(self.extra_config["headers"])
        elif self.oms_type == OMSType.LEGACY:
            # Headers para sistemas legacy
            headers.update(self.extra_config.get("headers", {}))
        
        return headers
    
    def _get_base_url(self) -> str:
        """Obtiene URL base según tipo de OMS."""
        if self.oms_type == OMSType.SHOPIFY:
            shop_name = self.extra_config.get("shop_name", "")
            return f"https://{shop_name}.myshopify.com/admin/api/2024-01"
        elif self.oms_type == OMSType.WOOCOMMERCE:
            return f"{self.api_url}/wp-json/wc/v3"
        elif self.oms_type == OMSType.CUSTOM:
            return self.api_url or ""
        elif self.oms_type == OMSType.LEGACY:
            return self.api_url or ""
        
        return ""
    
    def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene información de una orden.
        
        Args:
            order_id: ID de la orden
            
        Returns:
            Dict con información de la orden o None si no existe
        """
        # Validación de input
        if not order_id or not isinstance(order_id, str) or len(order_id.strip()) == 0:
            print("⚠️ Order ID inválido")
            return None
        
        try:
            base_url = self._get_base_url()
            if not base_url:
                print("⚠️ Base URL no configurada para OMS")
                return None
            
            if self.oms_type == OMSType.SHOPIFY:
                return self._shopify_get_order(base_url, order_id)
            elif self.oms_type == OMSType.WOOCOMMERCE:
                return self._woocommerce_get_order(base_url, order_id)
            elif self.oms_type == OMSType.CUSTOM:
                return self._custom_get_order(base_url, order_id)
            elif self.oms_type == OMSType.LEGACY:
                return self._legacy_get_order(base_url, order_id)
            
            return None
        except Exception as e:
            print(f"⚠️ Error obteniendo orden de OMS: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _shopify_get_order(self, base_url: str, order_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene orden de Shopify."""
        url = f"{base_url}/orders/{order_id}.json"
        
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            order_data = response.json().get("order", {})
            
            # Normalizar formato
            return {
                "order_id": str(order_data.get("id", order_id)),
                "status": order_data.get("financial_status", "pending"),
                "fulfillment_status": order_data.get("fulfillment_status"),
                "total": float(order_data.get("total_price", 0)),
                "currency": order_data.get("currency", "USD"),
                "delivery_address": {
                    "name": order_data.get("shipping_address", {}).get("name", ""),
                    "street": order_data.get("shipping_address", {}).get("address1", ""),
                    "city": order_data.get("shipping_address", {}).get("city", ""),
                    "state": order_data.get("shipping_address", {}).get("province", ""),
                    "zip": order_data.get("shipping_address", {}).get("zip", ""),
                    "country": order_data.get("shipping_address", {}).get("country", ""),
                },
                "tracking_number": self._extract_tracking_from_shopify(order_data),
                "created_at": order_data.get("created_at"),
                "line_items": [
                    {
                        "product_id": item.get("product_id"),
                        "name": item.get("name"),
                        "quantity": item.get("quantity"),
                        "price": float(item.get("price", 0)),
                    }
                    for item in order_data.get("line_items", [])
                ],
            }
        except Exception as e:
            print(f"⚠️ Error obteniendo orden de Shopify: {e}")
            return None
    
    def _woocommerce_get_order(self, base_url: str, order_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene orden de WooCommerce."""
        url = f"{base_url}/orders/{order_id}"
        
        try:
            response = requests.get(url, headers=self.headers, auth=(self.api_key, self.api_secret), timeout=10)
            response.raise_for_status()
            order_data = response.json()
            
            # Normalizar formato
            return {
                "order_id": str(order_data.get("id", order_id)),
                "status": order_data.get("status", "pending"),
                "total": float(order_data.get("total", 0)),
                "currency": order_data.get("currency", "USD"),
                "delivery_address": {
                    "name": f"{order_data.get('shipping', {}).get('first_name', '')} {order_data.get('shipping', {}).get('last_name', '')}".strip(),
                    "street": order_data.get("shipping", {}).get("address_1", ""),
                    "city": order_data.get("shipping", {}).get("city", ""),
                    "state": order_data.get("shipping", {}).get("state", ""),
                    "zip": order_data.get("shipping", {}).get("postcode", ""),
                    "country": order_data.get("shipping", {}).get("country", ""),
                },
                "tracking_number": order_data.get("meta_data", {}).get("tracking_number"),
                "created_at": order_data.get("date_created"),
                "line_items": [
                    {
                        "product_id": item.get("product_id"),
                        "name": item.get("name"),
                        "quantity": item.get("quantity"),
                        "price": float(item.get("price", 0)),
                    }
                    for item in order_data.get("line_items", [])
                ],
            }
        except Exception as e:
            print(f"⚠️ Error obteniendo orden de WooCommerce: {e}")
            return None
    
    def _custom_get_order(self, base_url: str, order_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene orden de API personalizada."""
        endpoint = self.extra_config.get("order_endpoint", f"/orders/{order_id}")
        url = f"{base_url}{endpoint}"
        
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"⚠️ Error obteniendo orden de API personalizada: {e}")
            return None
    
    def _legacy_get_order(self, base_url: str, order_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene orden de sistema legacy usando adaptador."""
        # Usar adaptador configurado
        adapter_config = self.extra_config.get("adapter", {})
        adapter_type = adapter_config.get("type", "rest")
        
        if adapter_type == "rest":
            endpoint = adapter_config.get("order_endpoint", f"/api/orders/{order_id}")
            url = f"{base_url}{endpoint}"
            
            # Headers especiales para legacy
            legacy_headers = self.headers.copy()
            legacy_headers.update(adapter_config.get("headers", {}))
            
            try:
                response = requests.get(url, headers=legacy_headers, timeout=15)
                response.raise_for_status()
                
                # Transformar respuesta usando mapper si existe
                raw_data = response.json()
                mapper = adapter_config.get("mapper", {})
                if mapper:
                    return self._map_legacy_response(raw_data, mapper.get("order", {}))
                
                return raw_data
            except Exception as e:
                print(f"⚠️ Error obteniendo orden de sistema legacy: {e}")
                return None
        elif adapter_type == "soap":
            # Implementar SOAP si es necesario
            return None
        
        return None
    
    def _map_legacy_response(self, raw_data: Dict[str, Any], mapper: Dict[str, str]) -> Dict[str, Any]:
        """Mapea respuesta de sistema legacy a formato estándar."""
        mapped = {}
        for standard_key, legacy_key in mapper.items():
            if legacy_key in raw_data:
                mapped[standard_key] = raw_data[legacy_key]
        return mapped
    
    def _extract_tracking_from_shopify(self, order_data: Dict[str, Any]) -> Optional[str]:
        """Extrae tracking number de orden de Shopify."""
        fulfillments = order_data.get("fulfillments", [])
        if fulfillments:
            tracking_numbers = [
                f.get("tracking_number")
                for f in fulfillments
                if f.get("tracking_number")
            ]
            if tracking_numbers:
                return tracking_numbers[0]
        return None
    
    def update_order(self, order_update: OrderUpdate) -> Optional[Dict[str, Any]]:
        """
        Actualiza una orden en el OMS.
        
        Args:
            order_update: Datos de actualización
            
        Returns:
            Dict con orden actualizada o None si falla
        """
        base_url = self._get_base_url()
        
        if self.oms_type == OMSType.SHOPIFY:
            return self._shopify_update_order(base_url, order_update)
        elif self.oms_type == OMSType.WOOCOMMERCE:
            return self._woocommerce_update_order(base_url, order_update)
        elif self.oms_type == OMSType.CUSTOM:
            return self._custom_update_order(base_url, order_update)
        elif self.oms_type == OMSType.LEGACY:
            return self._legacy_update_order(base_url, order_update)
        
        return None
    
    def _shopify_update_order(self, base_url: str, order_update: OrderUpdate) -> Optional[Dict[str, Any]]:
        """Actualiza orden en Shopify."""
        url = f"{base_url}/orders/{order_update.order_id}.json"
        
        data = {"order": {}}
        
        if order_update.delivery_address:
            data["order"]["shipping_address"] = {
                "first_name": order_update.delivery_address.get("name", "").split()[0] if order_update.delivery_address.get("name") else "",
                "last_name": " ".join(order_update.delivery_address.get("name", "").split()[1:]) if order_update.delivery_address.get("name") else "",
                "address1": order_update.delivery_address.get("street", ""),
                "city": order_update.delivery_address.get("city", ""),
                "province": order_update.delivery_address.get("state", ""),
                "zip": order_update.delivery_address.get("zip", ""),
                "country": order_update.delivery_address.get("country", ""),
            }
        
        if order_update.tracking_number:
            # Agregar tracking a fulfillment
            data["order"]["note"] = f"Tracking: {order_update.tracking_number}"
        
        if order_update.status:
            data["order"]["financial_status"] = order_update.status
        
        try:
            response = requests.put(url, headers=self.headers, json=data, timeout=10)
            response.raise_for_status()
            return response.json().get("order", {})
        except Exception as e:
            print(f"⚠️ Error actualizando orden en Shopify: {e}")
            return None
    
    def _woocommerce_update_order(self, base_url: str, order_update: OrderUpdate) -> Optional[Dict[str, Any]]:
        """Actualiza orden en WooCommerce."""
        url = f"{base_url}/orders/{order_update.order_id}"
        
        data = {}
        
        if order_update.delivery_address:
            data["shipping"] = {
                "first_name": order_update.delivery_address.get("name", "").split()[0] if order_update.delivery_address.get("name") else "",
                "last_name": " ".join(order_update.delivery_address.get("name", "").split()[1:]) if order_update.delivery_address.get("name") else "",
                "address_1": order_update.delivery_address.get("street", ""),
                "city": order_update.delivery_address.get("city", ""),
                "state": order_update.delivery_address.get("state", ""),
                "postcode": order_update.delivery_address.get("zip", ""),
                "country": order_update.delivery_address.get("country", ""),
            }
        
        if order_update.tracking_number:
            data["meta_data"] = [{
                "key": "tracking_number",
                "value": order_update.tracking_number
            }]
        
        if order_update.status:
            data["status"] = order_update.status
        
        try:
            response = requests.put(url, headers=self.headers, auth=(self.api_key, self.api_secret), json=data, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"⚠️ Error actualizando orden en WooCommerce: {e}")
            return None
    
    def _custom_update_order(self, base_url: str, order_update: OrderUpdate) -> Optional[Dict[str, Any]]:
        """Actualiza orden en API personalizada."""
        endpoint = self.extra_config.get("order_update_endpoint", f"/orders/{order_update.order_id}")
        url = f"{base_url}{endpoint}"
        
        data = {
            "delivery_address": order_update.delivery_address,
            "delivery_date": order_update.delivery_date,
            "tracking_number": order_update.tracking_number,
            "status": order_update.status,
            "notes": order_update.notes,
        }
        
        try:
            response = requests.put(url, headers=self.headers, json=data, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"⚠️ Error actualizando orden en API personalizada: {e}")
            return None
    
    def _legacy_update_order(self, base_url: str, order_update: OrderUpdate) -> Optional[Dict[str, Any]]:
        """Actualiza orden en sistema legacy."""
        adapter_config = self.extra_config.get("adapter", {})
        endpoint = adapter_config.get("order_update_endpoint", f"/api/orders/{order_update.order_id}")
        url = f"{base_url}{endpoint}"
        
        # Mapear datos al formato legacy
        mapper = adapter_config.get("mapper", {}).get("order_update", {})
        legacy_data = {}
        
        if order_update.delivery_address:
            legacy_data[mapper.get("address", "shipping_address")] = order_update.delivery_address
        
        if order_update.tracking_number:
            legacy_data[mapper.get("tracking", "tracking_number")] = order_update.tracking_number
        
        legacy_headers = self.headers.copy()
        legacy_headers.update(adapter_config.get("headers", {}))
        
        try:
            response = requests.put(url, headers=legacy_headers, json=legacy_data, timeout=15)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"⚠️ Error actualizando orden en sistema legacy: {e}")
            return None

