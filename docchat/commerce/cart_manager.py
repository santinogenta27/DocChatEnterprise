"""
Cart Manager - Gestión de carrito de compras persistente
"""

from __future__ import annotations

import json
import sqlite3
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path
from datetime import datetime
import uuid

from .product_catalog import Product


@dataclass
class CartItem:
    """Item del carrito."""
    product_id: str
    product_title: str
    quantity: int
    price: float
    options: Dict[str, Any] = None  # Color, tamaño, etc.
    
    def __post_init__(self):
        if self.options is None:
            self.options = {}
    
    @property
    def subtotal(self) -> float:
        """Calcula el subtotal del item."""
        return self.price * self.quantity


@dataclass
class Cart:
    """Carrito de compras."""
    cart_id: str
    session_id: str
    items: List[CartItem]
    created_at: str
    updated_at: str
    
    @property
    def total(self) -> float:
        """Calcula el total del carrito."""
        return sum(item.subtotal for item in self.items)
    
    @property
    def item_count(self) -> int:
        """Número de items en el carrito."""
        return sum(item.quantity for item in self.items)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario."""
        return {
            "cart_id": self.cart_id,
            "session_id": self.session_id,
            "items": [asdict(item) for item in self.items],
            "total": self.total,
            "item_count": self.item_count,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }


class CartManager:
    """
    Gestor de carritos de compras.
    
    Características:
    - Carritos persistentes por sesión
    - Agregar/remover items
    - Actualizar cantidades
    - Calcular totales
    """
    
    def __init__(self, config: Any):
        """
        Inicializa el gestor de carritos.
        
        Args:
            config: Configuración de la aplicación
        """
        self.config = config
        
        # Base de datos de carritos
        cart_dir = Path(config.memory_dir) / "commerce" / "carts"
        cart_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = cart_dir / "carts.db"
        self._init_database()
    
    def _init_database(self):
        """Inicializa la base de datos de carritos."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS carts (
                cart_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                items TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # Crear índice por separado (SQLite no soporta INDEX en CREATE TABLE)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_session ON carts(session_id)")
        
        conn.commit()
        conn.close()
    
    def get_or_create_cart(self, session_id: str) -> Cart:
        """
        Obtiene o crea un carrito para una sesión.
        
        Args:
            session_id: ID de la sesión
        
        Returns:
            Cart existente o nuevo
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT cart_id, items, created_at, updated_at
            FROM carts
            WHERE session_id = ?
            ORDER BY updated_at DESC
            LIMIT 1
        """, (session_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            cart_id, items_json, created_at, updated_at = row
            items = [CartItem(**item) for item in json.loads(items_json)]
            return Cart(
                cart_id=cart_id,
                session_id=session_id,
                items=items,
                created_at=created_at,
                updated_at=updated_at
            )
        else:
            # Crear nuevo carrito
            cart_id = f"CART-{uuid.uuid4().hex[:8].upper()}"
            now = datetime.now().isoformat()
            cart = Cart(
                cart_id=cart_id,
                session_id=session_id,
                items=[],
                created_at=now,
                updated_at=now
            )
            self._save_cart(cart)
            return cart
    
    def add_item(
        self,
        session_id: str,
        product: Product,
        quantity: int = 1,
        options: Optional[Dict[str, Any]] = None
    ) -> Cart:
        """
        Agrega un item al carrito.
        
        Args:
            session_id: ID de la sesión
            product: Producto a agregar
            quantity: Cantidad
            options: Opciones (color, tamaño, etc.)
        
        Returns:
            Cart actualizado
        """
        cart = self.get_or_create_cart(session_id)
        
        # Verificar si el producto ya está en el carrito
        existing_item = None
        for item in cart.items:
            if item.product_id == product.id and item.options == (options or {}):
                existing_item = item
                break
        
        if existing_item:
            # Actualizar cantidad
            existing_item.quantity += quantity
        else:
            # Agregar nuevo item
            cart_item = CartItem(
                product_id=product.id,
                product_title=product.title,
                quantity=quantity,
                price=product.price,
                options=options or {}
            )
            cart.items.append(cart_item)
        
        cart.updated_at = datetime.now().isoformat()
        self._save_cart(cart)
        
        return cart
    
    def remove_item(self, session_id: str, product_id: str, options: Optional[Dict[str, Any]] = None) -> Cart:
        """
        Remueve un item del carrito.
        
        Args:
            session_id: ID de la sesión
            product_id: ID del producto
            options: Opciones del item (para identificar el item específico)
        
        Returns:
            Cart actualizado
        """
        cart = self.get_or_create_cart(session_id)
        
        cart.items = [
            item for item in cart.items
            if not (item.product_id == product_id and item.options == (options or {}))
        ]
        
        cart.updated_at = datetime.now().isoformat()
        self._save_cart(cart)
        
        return cart
    
    def update_item_quantity(
        self,
        session_id: str,
        product_id: str,
        quantity: int,
        options: Optional[Dict[str, Any]] = None
    ) -> Cart:
        """
        Actualiza la cantidad de un item.
        
        Args:
            session_id: ID de la sesión
            product_id: ID del producto
            quantity: Nueva cantidad
            options: Opciones del item
        
        Returns:
            Cart actualizado
        """
        cart = self.get_or_create_cart(session_id)
        
        for item in cart.items:
            if item.product_id == product_id and item.options == (options or {}):
                if quantity <= 0:
                    cart.items.remove(item)
                else:
                    item.quantity = quantity
                break
        
        cart.updated_at = datetime.now().isoformat()
        self._save_cart(cart)
        
        return cart
    
    def clear_cart(self, session_id: str) -> Cart:
        """
        Limpia el carrito.
        
        Args:
            session_id: ID de la sesión
        
        Returns:
            Cart vacío
        """
        cart = self.get_or_create_cart(session_id)
        cart.items = []
        cart.updated_at = datetime.now().isoformat()
        self._save_cart(cart)
        
        return cart
    
    def _save_cart(self, cart: Cart):
        """Guarda el carrito en la base de datos."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        items_json = json.dumps([asdict(item) for item in cart.items])
        
        cursor.execute("""
            INSERT OR REPLACE INTO carts (cart_id, session_id, items, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            cart.cart_id,
            cart.session_id,
            items_json,
            cart.created_at,
            cart.updated_at
        ))
        
        conn.commit()
        conn.close()






