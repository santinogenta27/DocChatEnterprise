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





















