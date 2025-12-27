from __future__ import annotations

from typing import Dict, Any, List, Optional
from datetime import datetime


class OrderTool:
    """Wrapper para gestión de pedidos.

    Nota: aquí dejamos métodos listos para conectar con el
    sistema de pedidos real (ERP, Shopify, base de datos interna, etc.).
    De momento implementamos una versión mínima en memoria/extensible.
    
    Inspirado en Sierra.ai - Permite actualizar órdenes en tiempo real.
    """

    def __init__(self) -> None:
        # En producción, esto hablaría con DB/ERP.
        self._orders: Dict[str, Dict[str, Any]] = {}

    def create_order(self, session_id: str, cart_snapshot: Dict[str, Any], payment_info: Dict[str, Any]) -> Dict[str, Any]:
        """Crea una nueva orden."""
        order_id = f"order_{len(self._orders) + 1}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        order = {
            "order_id": order_id,
            "session_id": session_id,
            "cart": cart_snapshot,
            "payment": payment_info,
            "status": "processing",
            "delivery_address": cart_snapshot.get("delivery_address", {}),
            "delivery_date": cart_snapshot.get("delivery_date"),
            "tracking_number": None,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        self._orders[order_id] = order
        return order

    def get_order_status(self, order_id: str) -> Dict[str, Any] | None:
        """Obtiene el estado de una orden."""
        return self._orders.get(order_id)
    
    def get_order_by_email_and_id(self, email: str, order_id: str) -> Optional[Dict[str, Any]]:
        """
        Busca una orden por email y order_id.
        
        Args:
            email: Email del cliente
            order_id: ID de la orden
            
        Returns:
            Orden encontrada o None
        """
        # Buscar por order_id primero
        order = self._orders.get(order_id)
        if order:
            # Verificar que el email coincida (si está guardado)
            order_email = order.get("customer_email")
            if not order_email or order_email.lower() == email.lower():
                return order
        
        # Buscar en todas las órdenes
        for order in self._orders.values():
            order_email = order.get("customer_email")
            if order_email and order_email.lower() == email.lower():
                order_num = order.get("order_id", "").split("_")[-1] if "_" in order.get("order_id", "") else ""
                if order_num in order_id or order_id in order.get("order_id", ""):
                    return order
        
        return None

    def list_orders_for_session(self, session_id: str) -> List[Dict[str, Any]]:
        """Lista todas las órdenes de una sesión."""
        return [o for o in self._orders.values() if o.get("session_id") == session_id]
    
    def update_order_delivery_address(
        self,
        order_id: str,
        new_address: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        Actualiza la dirección de entrega de una orden.
        
        Args:
            order_id: ID de la orden
            new_address: Nueva dirección (name, street, city, state, zip, country)
            
        Returns:
            Orden actualizada o None si no existe
        """
        order = self._orders.get(order_id)
        if not order:
            return None
        
        order["delivery_address"] = new_address
        order["updated_at"] = datetime.now().isoformat()
        
        return order
    
    def update_order_delivery_date(
        self,
        order_id: str,
        new_delivery_date: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Actualiza la fecha de entrega de una orden.
        
        Args:
            order_id: ID de la orden
            new_delivery_date: Nueva fecha de entrega (ISO format o "tomorrow", "next_week", etc.)
            
        Returns:
            Orden actualizada o None si no existe
        """
        order = self._orders.get(order_id)
        if not order:
            return None
        
        order["delivery_date"] = new_delivery_date
        order["updated_at"] = datetime.now().isoformat()
        
        return order
    
    def add_tracking_number(
        self,
        order_id: str,
        tracking_number: str,
        carrier: str = "UPS",
    ) -> Optional[Dict[str, Any]]:
        """
        Agrega número de seguimiento a una orden.
        
        Args:
            order_id: ID de la orden
            tracking_number: Número de seguimiento
            carrier: Transportista (UPS, FedEx, etc.)
            
        Returns:
            Orden actualizada o None si no existe
        """
        order = self._orders.get(order_id)
        if not order:
            return None
        
        order["tracking_number"] = tracking_number
        order["tracking_carrier"] = carrier
        order["updated_at"] = datetime.now().isoformat()
        
        return order


































