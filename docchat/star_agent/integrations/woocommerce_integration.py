"""
WooCommerce Integration - IntegraciÃ³n en tiempo real con WooCommerce API
Permite consultar productos, stock, precios en tiempo real
"""

from __future__ import annotations

import os
import time
import base64
from typing import List, Dict, Optional, Any
from dataclasses import dataclass

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    requests = None


@dataclass
class WooCommerceProduct:
    """Producto de WooCommerce."""
    id: str
    name: str
    description: str
    price: float
    currency: str
    image_url: Optional[str]
    categories: List[str]
    tags: List[str]
    stock_quantity: int
    in_stock: bool
    sku: Optional[str]
    permalink: str  # URL del producto
    created_at: str
    updated_at: str


class WooCommerceIntegration:
    """
    IntegraciÃ³n en tiempo real con WooCommerce API.
    
    CaracterÃ­sticas:
    - Consulta productos en tiempo real
    - Verifica stock actualizado
    - Obtiene precios actuales
    - BÃºsqueda por nombre, categorÃ­a, tags
    """
    
    def __init__(self, store_url: str, consumer_key: str, consumer_secret: str):
        """
        Inicializa integraciÃ³n con WooCommerce.
        
        Args:
            store_url: URL de la tienda (ej: "https://mi-tienda.com")
            consumer_key: Consumer Key de WooCommerce
            consumer_secret: Consumer Secret de WooCommerce
        """
        if not REQUESTS_AVAILABLE:
            raise ImportError("requests no estÃ¡ instalado. Instala con: pip install requests")
        
        # Limpiar URL
        store_url = store_url.rstrip("/")
        if not store_url.startswith("http"):
            store_url = f"https://{store_url}"
        
        self.store_url = store_url
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.api_version = "wc/v3"
        self.base_url = f"{store_url}/wp-json/wc/v3"
        
        # AutenticaciÃ³n HTTP Basic Auth
        auth_string = f"{consumer_key}:{consumer_secret}"
        auth_bytes = auth_string.encode("ascii")
        auth_b64 = base64.b64encode(auth_bytes).decode("ascii")
        self.headers = {
            "Authorization": f"Basic {auth_b64}",
            "Content-Type": "application/json"
        }
        
        # Cache simple (1 minuto TTL)
        self._cache: Dict[str, tuple] = {}
        self.cache_ttl = 60
    
    def _get_cached(self, key: str) -> Optional[Any]:
        """Obtiene valor del cache si no expirÃ³."""
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
    
    def _make_request(self, endpoint: str, method: str = "GET", params: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Hace request a WooCommerce API."""
        url = f"{self.base_url}/{endpoint}"
        
        try:
            if method == "GET":
                response = requests.get(url, headers=self.headers, params=params, timeout=10, auth=(self.consumer_key, self.consumer_secret))
            elif method == "POST":
                response = requests.post(url, headers=self.headers, json=params, timeout=10, auth=(self.consumer_key, self.consumer_secret))
            else:
                raise ValueError(f"MÃ©todo no soportado: {method}")
            
            response.raise_for_status()
            
            # WooCommerce devuelve array directamente
            if isinstance(response.json(), list):
                return response.json()
            else:
                return [response.json()]
                
        except requests.exceptions.RequestException as e:
            print(f"âš ï¸ Error en request a WooCommerce: {e}")
            return []
    
    def search_products(self, query: str, limit: int = 10) -> List[WooCommerceProduct]:
        """
        Busca productos en tiempo real por nombre, descripciÃ³n o SKU.
        
        Args:
            query: TÃ©rmino de bÃºsqueda
            limit: NÃºmero mÃ¡ximo de resultados
            
        Returns:
            Lista de productos encontrados
        """
        cache_key = f"search_{query}_{limit}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        try:
            params = {
                "search": query,
                "per_page": min(limit, 100),  # WooCommerce mÃ¡ximo 100
                "status": "publish"
            }
            
            products_data = self._make_request("products", params=params)
            products = []
            
            for product_data in products_data[:limit]:
                product = self._parse_product(product_data)
                if product:
                    products.append(product)
            
            self._set_cache(cache_key, products)
            return products
            
        except Exception as e:
            print(f"âš ï¸ Error buscando productos en WooCommerce: {e}")
            return []
    
    def get_product_by_id(self, product_id: str) -> Optional[WooCommerceProduct]:
        """Obtiene un producto especÃ­fico por ID en tiempo real."""
        cache_key = f"product_{product_id}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        try:
            products_data = self._make_request(f"products/{product_id}")
            
            if products_data:
                product = self._parse_product(products_data[0])
                self._set_cache(cache_key, product)
                return product
            
            return None
        except Exception as e:
            print(f"âš ï¸ Error obteniendo producto {product_id} de WooCommerce: {e}")
            return None
    
    def get_all_products(self, limit: int = 100) -> List[WooCommerceProduct]:
        """Obtiene todos los productos (hasta el lÃ­mite)."""
        cache_key = f"all_products_{limit}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        try:
            params = {
                "per_page": min(limit, 100),
                "status": "publish"
            }
            products_data = self._make_request("products", params=params)
            
            products = []
            for product_data in products_data:
                product = self._parse_product(product_data)
                if product:
                    products.append(product)
            
            self._set_cache(cache_key, products)
            return products
            
        except Exception as e:
            print(f"âš ï¸ Error obteniendo todos los productos de WooCommerce: {e}")
            return []
    
    def _parse_product(self, product_data: Dict[str, Any]) -> Optional[WooCommerceProduct]:
        """Parsea datos de producto de WooCommerce."""
        try:
            # Obtener precio (regular_price o sale_price)
            price = float(product_data.get("sale_price") or product_data.get("regular_price") or 0)
            
            # Stock
            stock_quantity = int(product_data.get("stock_quantity", 0))
            stock_status = product_data.get("stock_status", "outofstock")
            in_stock = stock_status == "instock" or stock_quantity > 0
            
            # Imagen principal
            images = product_data.get("images", [])
            image_url = images[0].get("src") if images else None
            
            # CategorÃ­as
            categories = [cat.get("name", "") for cat in product_data.get("categories", [])]
            
            # Tags
            tags = [tag.get("name", "") for tag in product_data.get("tags", [])]
            
            return WooCommerceProduct(
                id=str(product_data.get("id", "")),
                name=product_data.get("name", ""),
                description=product_data.get("description", "").replace("<p>", "").replace("</p>", "").strip()[:500],
                price=price,
                currency=product_data.get("currency", "USD"),
                image_url=image_url,
                categories=categories,
                tags=tags,
                stock_quantity=stock_quantity,
                in_stock=in_stock,
                sku=product_data.get("sku"),
                permalink=product_data.get("permalink", ""),
                created_at=product_data.get("date_created", ""),
                updated_at=product_data.get("date_modified", "")
            )
        except Exception as e:
            print(f"âš ï¸ Error parseando producto de WooCommerce: {e}")
            return None


