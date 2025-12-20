from __future__ import annotations

from typing import Dict, Any

from ...commerce.cart_manager import CartManager, Cart


class CartTool:
    """Wrapper sobre CartManager para gestión de carrito."""

    def __init__(self, cart_manager: CartManager) -> None:
        self.cart_manager = cart_manager

    def get_cart(self, session_id: str) -> Cart:
        return self.cart_manager.get_or_create_cart(session_id)

    def add_item(self, session_id: str, product_id: str, quantity: int = 1) -> Cart:
        return self.cart_manager.add_to_cart(session_id=session_id, product_id=product_id, quantity=quantity)

    def update_item(self, session_id: str, product_id: str, quantity: int) -> Cart:
        return self.cart_manager.update_cart_item(session_id=session_id, product_id=product_id, quantity=quantity)

    def remove_item(self, session_id: str, product_id: str) -> Cart:
        return self.cart_manager.remove_from_cart(session_id=session_id, product_id=product_id)

    def clear_cart(self, session_id: str) -> Cart:
        return self.cart_manager.clear_cart(session_id=session_id)












