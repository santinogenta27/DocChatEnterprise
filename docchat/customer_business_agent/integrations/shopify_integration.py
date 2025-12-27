"""
Shopify Integration - Integración en tiempo real con Shopify API
Permite consultar productos, stock, precios en tiempo real
"""

from __future__ import annotations

import os
import time
from typing import List, Dict, Optional, Any
from dataclasses import dataclass

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    requests = None


@dataclass
class ShopifyProduct:
    """Producto de Shopify."""
    id: str
    title: str
    description: str
    price: float
    currency: str
    image_url: Optional[str]
    product_type: Optional[str]
    vendor: Optional[str]
    tags: List[str]
    variants: List[Dict[str, Any]]
    stock_quantity: int
    in_stock: bool
    handle: str  # URL slug
    created_at: str
    updated_at: str


class ShopifyIntegration:
    """
    Integración en tiempo real con Shopify API.
    
    Características:
    - Consulta productos en tiempo real
    - Verifica stock actualizado
    - Obtiene precios actuales
    - Búsqueda por nombre, tipo, tags
    """
    
    def __init__(self, shop_url: str, access_token: str):
        """
        Inicializa integración con Shopify.
        
        Args:
            shop_url: URL de la tienda (ej: "mi-tienda.myshopify.com")
            access_token: Token de acceso de la API
        """
        if not REQUESTS_AVAILABLE:
            raise ImportError("requests no está instalado. Instala con: pip install requests")
        
        # Limpiar URL si viene con https://
        shop_url = shop_url.replace("https://", "").replace("http://", "").replace("/", "")
        if not shop_url.endswith(".myshopify.com"):
            shop_url = f"{shop_url}.myshopify.com"
        
        self.shop_url = shop_url
        self.access_token = access_token
        self.api_version = "2024-01"  # Última versión estable
        self.base_url = f"https://{shop_url}/admin/api/{self.api_version}"
        self.headers = {
            "X-Shopify-Access-Token": access_token,
            "Content-Type": "application/json"
        }
        
        # Cache simple (1 minuto TTL)
        self._cache: Dict[str, tuple] = {}  # key -> (data, timestamp)
        self.cache_ttl = 60  # 1 minuto
    
    def _get_cached(self, key: str) -> Optional[Any]:
        """Obtiene valor del cache si no expiró."""
        if key in self._cache:
            data, timestamp = self._cache[key]
            if time.time() - timestamp < self.cache_ttl:
                return data
            else:
                del self._cache[key]
        return None
    
    def _set_cache(self, key: str, value: Any):
        """Guarda valor en cache."""
        self._cache[key] = (value, time.time())
    
    def _make_request(self, endpoint: str, method: str = "GET", params: Optional[Dict] = None) -> Dict[str, Any]:
        """Hace request a Shopify API."""
        url = f"{self.base_url}/{endpoint}"
        
        try:
            if method == "GET":
                response = requests.get(url, headers=self.headers, params=params, timeout=10)
            elif method == "POST":
                response = requests.post(url, headers=self.headers, json=params, timeout=10)
            else:
                raise ValueError(f"Método no soportado: {method}")
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Error en request a Shopify: {e}")
            raise
    
    def search_products(self, query: str, limit: int = 10) -> List[ShopifyProduct]:
        """
        Busca productos en tiempo real por nombre, descripción o tags.
        
        Args:
            query: Término de búsqueda
            limit: Número máximo de resultados
            
        Returns:
            Lista de productos encontrados
        """
        cache_key = f"search_{query}_{limit}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        try:
            # Buscar productos
            params = {
                "title": query,
                "limit": min(limit, 250)  # Shopify máximo 250
            }
            
            response = self._make_request("products.json", params=params)
            products_data = response.get("products", [])
            
            # Obtener inventario para cada producto
            products = []
            for product_data in products_data[:limit]:
                product = self._parse_product(product_data)
                if product:
                    products.append(product)
            
            self._set_cache(cache_key, products)
            return products
            
        except Exception as e:
            print(f"⚠️ Error buscando productos en Shopify: {e}")
            return []
    
    def get_product_by_id(self, product_id: str) -> Optional[ShopifyProduct]:
        """Obtiene un producto específico por ID en tiempo real."""
        cache_key = f"product_{product_id}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        try:
            response = self._make_request(f"products/{product_id}.json")
            product_data = response.get("product")
            
            if product_data:
                product = self._parse_product(product_data)
                self._set_cache(cache_key, product)
                return product
            
            return None
        except Exception as e:
            print(f"⚠️ Error obteniendo producto {product_id} de Shopify: {e}")
            return None
    
    def get_product_by_handle(self, handle: str) -> Optional[ShopifyProduct]:
        """Obtiene un producto por handle (slug) en tiempo real."""
        cache_key = f"handle_{handle}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        try:
            response = self._make_request("products.json", params={"handle": handle})
            products_data = response.get("products", [])
            
            if products_data:
                product = self._parse_product(products_data[0])
                self._set_cache(cache_key, product)
                return product
            
            return None
        except Exception as e:
            print(f"⚠️ Error obteniendo producto {handle} de Shopify: {e}")
            return None
    
    def check_stock(self, variant_id: str) -> Dict[str, Any]:
        """
        Verifica stock de una variante en tiempo real.
        
        Args:
            variant_id: ID de la variante
            
        Returns:
            Dict con stock_quantity, available, etc.
        """
        cache_key = f"stock_{variant_id}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        try:
            response = self._make_request(f"variants/{variant_id}.json")
            variant_data = response.get("variant", {})
            
            stock_info = {
                "variant_id": variant_id,
                "inventory_quantity": variant_data.get("inventory_quantity", 0),
                "available": variant_data.get("inventory_quantity", 0) > 0,
                "inventory_policy": variant_data.get("inventory_policy", "deny"),
                "inventory_management": variant_data.get("inventory_management")
            }
            
            self._set_cache(cache_key, stock_info)
            return stock_info
            
        except Exception as e:
            print(f"⚠️ Error verificando stock de variante {variant_id}: {e}")
            return {
                "variant_id": variant_id,
                "inventory_quantity": 0,
                "available": False,
                "error": str(e)
            }
    
    def get_all_products(self, limit: int = 250) -> List[ShopifyProduct]:
        """Obtiene todos los productos (hasta el límite)."""
        cache_key = f"all_products_{limit}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        try:
            params = {"limit": min(limit, 250)}
            response = self._make_request("products.json", params=params)
            products_data = response.get("products", [])
            
            products = []
            for product_data in products_data:
                product = self._parse_product(product_data)
                if product:
                    products.append(product)
            
            self._set_cache(cache_key, products)
            return products
            
        except Exception as e:
            print(f"⚠️ Error obteniendo todos los productos de Shopify: {e}")
            return []
    
    def _parse_product(self, product_data: Dict[str, Any]) -> Optional[ShopifyProduct]:
        """Parsea datos de producto de Shopify."""
        try:
            # Obtener precio mínimo de variantes
            variants = product_data.get("variants", [])
            prices = [float(v.get("price", 0)) for v in variants if v.get("price")]
            min_price = min(prices) if prices else 0.0
            
            # Calcular stock total
            total_stock = sum(int(v.get("inventory_quantity", 0)) for v in variants)
            in_stock = total_stock > 0
            
            # Obtener imagen principal
            images = product_data.get("images", [])
            image_url = images[0].get("src") if images else None
            
            return ShopifyProduct(
                id=str(product_data.get("id", "")),
                title=product_data.get("title", ""),
                description=product_data.get("body_html", "").replace("<p>", "").replace("</p>", "").strip()[:500],
                price=min_price,
                currency=variants[0].get("currency_code", "USD") if variants else "USD",
                image_url=image_url,
                product_type=product_data.get("product_type"),
                vendor=product_data.get("vendor"),
                tags=product_data.get("tags", "").split(",") if product_data.get("tags") else [],
                variants=[{
                    "id": str(v.get("id", "")),
                    "title": v.get("title", ""),
                    "price": float(v.get("price", 0)),
                    "inventory_quantity": int(v.get("inventory_quantity", 0)),
                    "sku": v.get("sku", ""),
                    "barcode": v.get("barcode", ""),
                } for v in variants],
                stock_quantity=total_stock,
                in_stock=in_stock,
                handle=product_data.get("handle", ""),
                created_at=product_data.get("created_at", ""),
                updated_at=product_data.get("updated_at", "")
            )
        except Exception as e:
            print(f"⚠️ Error parseando producto de Shopify: {e}")
            return None

