from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Any, Optional

from ...commerce.product_catalog import ProductCatalog, Product, ProductSearchResult


@dataclass
class CatalogConfig:
    """Configuración ligera para el catálogo."""
    source: str = "internal"  # internal, shopify, etc.


class CatalogTool:
    """Wrapper de alto nivel sobre ProductCatalog.

    Expone métodos pensados para el agente de negocio,
    ocultando detalles de implementación.
    """

    def __init__(self, catalog: ProductCatalog) -> None:
        self.catalog = catalog

    def search_products(self, query: str, limit: int = 10) -> ProductSearchResult:
        """Busca productos y devuelve ProductSearchResult."""
        return self.catalog.search_products(query=query, limit=limit)

    def get_product(self, product_id: str) -> Optional[Product]:
        return self.catalog.get_product(product_id)

    def check_stock(self, product_id: str, quantity: int = 1) -> bool:
        product = self.catalog.get_product(product_id)
        if not product:
            return False
        return product.stock >= quantity

    def suggest_alternatives(self, product_id: str, limit: int = 5) -> List[Product]:
        """Sugiere productos alternativos/relacionados."""
        return self.catalog.get_related_products(product_id=product_id, limit=limit)
    
    def get_product_link(self, product_id: str, base_url: str = None) -> Optional[str]:
        """
        Genera link al producto.
        
        Prioridad:
        1. URL del producto si existe
        2. shopify_url si existe
        3. URL generada desde base_url si se proporciona
        
        Args:
            product_id: ID del producto
            base_url: URL base del e-commerce (ej: "https://tienda.com")
            
        Returns:
            URL del producto o None
        """
        product = self.get_product(product_id)
        if not product:
            return None
        
        # Prioridad 1: URL directa del producto
        if product.url:
            return product.url
        
        # Prioridad 2: URL de Shopify
        if product.shopify_url:
            return product.shopify_url
        
        # Prioridad 3: Generar URL desde base_url
        if base_url:
            # Limpiar base_url (quitar trailing slash)
            base_url = base_url.rstrip('/')
            return f"{base_url}/products/{product_id}"
        
        return None
    
    def get_products_with_links(self, query: str, base_url: str = None, limit: int = 10) -> Dict[str, Any]:
        """
        Busca productos y genera links automáticamente.
        
        Returns:
            Dict con productos y sus links
        """
        result = self.search_products(query=query, limit=limit)
        
        products_with_links = []
        for product in result.products:
            product_dict = product.to_dict() if hasattr(product, 'to_dict') else product.__dict__
            link = self.get_product_link(product.id, base_url=base_url)
            if link:
                product_dict['url'] = link
            products_with_links.append(product_dict)
        
        return {
            "products": products_with_links,
            "total_count": result.total_count,
            "query": query
        }

