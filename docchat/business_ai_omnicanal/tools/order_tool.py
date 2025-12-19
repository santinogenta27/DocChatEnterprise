from __future__ import annotations

from typing import Dict, Any, List


class OrderTool:
    """Wrapper para gestión de pedidos.

    Nota: aquí dejamos métodos listos para conectar con el
    sistema de pedidos real (ERP, Shopify, base de datos interna, etc.).
    De momento implementamos una versión mínima en memoria/extensible.
    """

    def __init__(self) -> None:
        # En producción, esto hablaría con DB/ERP.
        self._orders: Dict[str, Dict[str, Any]] = {}

    def create_order(self, session_id: str, cart_snapshot: Dict[str, Any], payment_info: Dict[str, Any]) -> Dict[str, Any]:
        order_id = f"order_{len(self._orders) + 1}"
        order = {
            "order_id": order_id,
            "session_id": session_id,
            "cart": cart_snapshot,
            "payment": payment_info,
            "status": "processing",
        }
        self._orders[order_id] = order
        return order

    def get_order_status(self, order_id: str) -> Dict[str, Any] | None:
        return self._orders.get(order_id)

    def list_orders_for_session(self, session_id: str) -> List[Dict[str, Any]]:
        return [o for o in self._orders.values() if o.get("session_id") == session_id]


