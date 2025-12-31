"""
Product Catalog - Integración con Shopify y catálogo local
Búsqueda de productos en tiempo real, stock, precios actualizados
"""

from __future__ import annotations

import os
import json
import sqlite3
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path
from datetime import datetime

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    requests = None


@dataclass
class Product:
    """Producto del catálogo."""
    id: str
    title: str
    description: str
    price: float
    currency: str = "USD"
    image_url: Optional[str] = None
    product_type: Optional[str] = None
    vendor: Optional[str] = None
    tags: List[str] = None
    variants: List[Dict[str, Any]] = None
    stock_quantity: int = 0
    in_stock: bool = True
    metadata: Dict[str, Any] = None
    url: Optional[str] = None  # URL del producto en e-commerce
    shopify_url: Optional[str] = None  # URL específica de Shopify (si aplica)
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.variants is None:
            self.variants = []
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario."""
        return asdict(self)


@dataclass
class ProductSearchResult:
    """Resultado de búsqueda de productos."""
    products: List[Product]
    total_count: int
    query: str
    filters_applied: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.filters_applied is None:
            self.filters_applied = {}


class ProductCatalog:
    """
    Catálogo de productos con integración a Shopify y almacenamiento local.
    
    Características:
    - Sincronización con Shopify (API)
    - Catálogo local persistente
    - Búsqueda en tiempo real
    - Verificación de stock
    - Precios actualizados
    """
    
    def __init__(self, config: Any):
        """
        Inicializa el catálogo de productos.
        
        Args:
            config: Configuración de la aplicación
        """
        self.config = config
        
        # Configurar Shopify
        self.shopify_shop_url = os.getenv("SHOPIFY_SHOP_URL") or getattr(config, 'shopify_shop_url', None)
        self.shopify_access_token = os.getenv("SHOPIFY_ACCESS_TOKEN") or getattr(config, 'shopify_access_token', None)
        self.shopify_enabled = bool(self.shopify_shop_url and self.shopify_access_token)
        
        # Base de datos local para catálogo
        catalog_dir = Path(config.memory_dir) / "commerce" / "catalog"
        catalog_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = catalog_dir / "products.db"
        self._init_database()
        
        # Cache de productos
        self._products_cache: Dict[str, Product] = {}
    
    def _init_database(self):
        """Inicializa la base de datos de productos."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                price REAL NOT NULL,
                currency TEXT DEFAULT 'USD',
                image_url TEXT,
                product_type TEXT,
                vendor TEXT,
                tags TEXT,
                variants TEXT,
                stock_quantity INTEGER DEFAULT 0,
                in_stock INTEGER DEFAULT 1,
                metadata TEXT,
                updated_at TEXT NOT NULL,
                shopify_id TEXT
            )
        """)
        
        # Crear índices por separado (SQLite no soporta INDEX en CREATE TABLE)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_title ON products(title)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_type ON products(product_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_vendor ON products(vendor)")
        
        conn.commit()
        conn.close()
    
    def sync_from_shopify(self) -> int:
        """
        Sincroniza productos desde Shopify.
        
        Returns:
            Número de productos sincronizados
        """
        if not self.shopify_enabled:
            print("⚠️ Shopify no configurado. Usando catálogo local.")
            return 0
        
        if not REQUESTS_AVAILABLE:
            print("⚠️ requests no disponible. Instala con: pip install requests")
            return 0
        
        try:
            # Obtener productos de Shopify
            url = f"https://{self.shopify_shop_url}/admin/api/2024-01/products.json"
            headers = {
                "X-Shopify-Access-Token": self.shopify_access_token
            }
            
            response = requests.get(url, headers=headers, params={"limit": 250})
            response.raise_for_status()
            
            data = response.json()
            products_data = data.get("products", [])
            
            # Guardar en base de datos local
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            synced_count = 0
            for product_data in products_data:
                product = self._shopify_to_product(product_data)
                self._save_product_to_db(cursor, product)
                synced_count += 1
            
            conn.commit()
            conn.close()
            
            # Limpiar cache
            self._products_cache.clear()
            
            print(f"✅ Sincronizados {synced_count} productos desde Shopify")
            return synced_count
            
        except Exception as e:
            print(f"⚠️ Error sincronizando desde Shopify: {e}")
            return 0
    
    def _shopify_to_product(self, shopify_product: Dict[str, Any]) -> Product:
        """Convierte un producto de Shopify a Product."""
        variants = shopify_product.get("variants", [])
        total_stock = sum(v.get("inventory_quantity", 0) for v in variants)
        
        # Generar URL de Shopify para el producto
        shopify_id = shopify_product.get("id", "")
        handle = shopify_product.get("handle", "")
        shopify_url = None
        if self.shopify_shop_url and handle:
            # URL formato: https://shop.myshopify.com/products/handle
            shopify_url = f"https://{self.shopify_shop_url}/products/{handle}"
        
        return Product(
            id=str(shopify_id),  # Convertir a string
            title=shopify_product.get("title", ""),
            description=shopify_product.get("body_html", ""),
            price=float(variants[0].get("price", 0)) if variants else 0.0,
            currency="USD",  # Shopify puede tener diferentes monedas
            image_url=shopify_product.get("images", [{}])[0].get("src") if shopify_product.get("images") else None,
            product_type=shopify_product.get("product_type"),
            vendor=shopify_product.get("vendor"),
            tags=shopify_product.get("tags", "").split(",") if shopify_product.get("tags") else [],
            variants=[{
                "id": v.get("id"),
                "title": v.get("title"),
                "price": float(v.get("price", 0)),
                "sku": v.get("sku"),
                "inventory_quantity": v.get("inventory_quantity", 0)
            } for v in variants],
            stock_quantity=total_stock,
            in_stock=total_stock > 0,
            shopify_url=shopify_url,  # Agregar URL de Shopify
            metadata={"shopify_id": shopify_id}
        )
    
    def _save_product_to_db(self, cursor: sqlite3.Cursor, product: Product):
        """Guarda un producto en la base de datos."""
        cursor.execute("""
            INSERT OR REPLACE INTO products 
            (id, title, description, price, currency, image_url, product_type, vendor, 
             tags, variants, stock_quantity, in_stock, metadata, updated_at, shopify_id, url, shopify_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            product.id,
            product.title,
            product.description,
            product.price,
            product.currency,
            product.image_url,
            product.product_type,
            product.vendor,
            json.dumps(product.tags),
            json.dumps(product.variants),
            product.stock_quantity,
            1 if product.in_stock else 0,
            json.dumps(product.metadata),
            datetime.now().isoformat(),
            product.metadata.get("shopify_id") if product.metadata else None,
            product.url,  # Agregar URL
            product.shopify_url  # Agregar shopify_url
        ))
    
    def search_products(
        self,
        query: str,
        product_type: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        in_stock_only: bool = True,
        limit: int = 20
    ) -> ProductSearchResult:
        """
        Busca productos en el catálogo.
        
        Args:
            query: Término de búsqueda
            product_type: Tipo de producto (filtro)
            min_price: Precio mínimo
            max_price: Precio máximo
            in_stock_only: Solo productos en stock
            limit: Límite de resultados
        
        Returns:
            ProductSearchResult con productos encontrados
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Construir query SQL
        sql = "SELECT * FROM products WHERE 1=1"
        params = []
        
        if query:
            sql += " AND (title LIKE ? OR description LIKE ? OR tags LIKE ?)"
            query_pattern = f"%{query}%"
            params.extend([query_pattern, query_pattern, query_pattern])
        
        if product_type:
            sql += " AND product_type = ?"
            params.append(product_type)
        
        if min_price is not None:
            sql += " AND price >= ?"
            params.append(min_price)
        
        if max_price is not None:
            sql += " AND price <= ?"
            params.append(max_price)
        
        if in_stock_only:
            sql += " AND in_stock = 1"
        
        sql += " ORDER BY title LIMIT ?"
        params.append(limit)
        
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        conn.close()
        
        # Convertir a objetos Product
        products = []
        for row in rows:
            product = self._row_to_product(row)
            products.append(product)
        
        filters = {
            "query": query,
            "product_type": product_type,
            "min_price": min_price,
            "max_price": max_price,
            "in_stock_only": in_stock_only
        }
        
        return ProductSearchResult(
            products=products,
            total_count=len(products),
            query=query,
            filters_applied=filters
        )
    
    def _row_to_product(self, row: tuple) -> Product:
        """Convierte una fila de la BD a Product."""
        # Manejar columnas antiguas (sin url) y nuevas (con url)
        url = row[14] if len(row) > 14 else None
        shopify_url = row[15] if len(row) > 15 else None
        
        return Product(
            id=row[0],
            title=row[1],
            description=row[2] or "",
            price=row[3],
            currency=row[4] or "USD",
            image_url=row[5],
            product_type=row[6],
            vendor=row[7],
            tags=json.loads(row[8]) if row[8] else [],
            variants=json.loads(row[9]) if row[9] else [],
            stock_quantity=row[10] or 0,
            in_stock=bool(row[11]),
            metadata=json.loads(row[12]) if row[12] else {},
            url=url,
            shopify_url=shopify_url
        )
    
    def get_product(self, product_id: str) -> Optional[Product]:
        """
        Obtiene un producto por ID.
        
        Args:
            product_id: ID del producto
        
        Returns:
            Product o None si no existe
        """
        # Verificar cache
        if product_id in self._products_cache:
            return self._products_cache[product_id]
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            product = self._row_to_product(row)
            self._products_cache[product_id] = product
            return product
        
        return None
    
    def add_product(self, product: Product):
        """
        Agrega o actualiza un producto en el catálogo local.
        
        Args:
            product: Producto a agregar/actualizar
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        self._save_product_to_db(cursor, product)
        
        conn.commit()
        conn.close()
        
        # Actualizar cache
        self._products_cache[product.id] = product
    
    def update_stock(self, product_id: str, quantity: int):
        """
        Actualiza el stock de un producto.
        
        Args:
            product_id: ID del producto
            quantity: Nueva cantidad en stock
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE products 
            SET stock_quantity = ?, in_stock = ?, updated_at = ?
            WHERE id = ?
        """, (quantity, 1 if quantity > 0 else 0, datetime.now().isoformat(), product_id))
        
        conn.commit()
        conn.close()
        
        # Actualizar cache
        if product_id in self._products_cache:
            self._products_cache[product_id].stock_quantity = quantity
            self._products_cache[product_id].in_stock = quantity > 0
    
    def get_related_products(self, product_id: str, limit: int = 5) -> List[Product]:
        """
        Obtiene productos relacionados.
        
        Args:
            product_id: ID del producto
            limit: Número de productos relacionados
        
        Returns:
            Lista de productos relacionados
        """
        product = self.get_product(product_id)
        if not product:
            return []
        
        # Buscar por tipo de producto y vendor
        result = self.search_products(
            query="",
            product_type=product.product_type,
            limit=limit + 1  # +1 para excluir el producto actual
        )
        
        # Filtrar el producto actual
        related = [p for p in result.products if p.id != product_id]
        return related[:limit]
















