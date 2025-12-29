"""
Abandoned Cart Service - Servicio de Recuperación de Carritos Abandonados
Maneja recordatorios automáticos y recuperación de carritos abandonados
"""

from __future__ import annotations

import time
from typing import List, Dict, Optional, Any
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict, field
import json


@dataclass
class AbandonedCart:
    """Carrito abandonado."""
    user_id: str
    session_id: str
    items: List[Dict[str, Any]]
    total_amount: float
    currency: str
    abandoned_at: str
    last_reminder_sent: Optional[str] = None
    reminders_sent: int = 0
    recovered: bool = False
    recovered_at: Optional[str] = None


class AbandonedCartService:
    """
    Servicio de recuperación de carritos abandonados.
    
    Características:
    - Detección automática de carritos abandonados
    - Recordatorios programados inteligentes
    - Integración con webhooks de Shopify/WooCommerce
    """
    
    def __init__(self, storage_dir: Path):
        """
        Inicializa el servicio de carritos abandonados.
        
        Args:
            storage_dir: Directorio para almacenar carritos abandonados
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Carritos en memoria
        self._abandoned_carts: Dict[str, AbandonedCart] = {}
        
        # Configuración
        self.abandonment_threshold_minutes = 5  # Considerar abandonado después de 5 minutos
        self.reminder_intervals_minutes = [30, 1440, 4320]  # 30 min, 24h, 72h
        self.max_reminders = 3
    
    def track_cart(self, user_id: str, session_id: str, items: List[Dict], total_amount: float, currency: str = "USD"):
        """
        Registra o actualiza un carrito.
        
        Args:
            user_id: ID del usuario
            session_id: ID de la sesión
            items: Items en el carrito
            total_amount: Monto total
            currency: Moneda
        """
        cart_key = f"{user_id}_{session_id}"
        
        # Si el carrito ya existe y se actualizó, resetear timestamp
        if cart_key in self._abandoned_carts:
            cart = self._abandoned_carts[cart_key]
            cart.items = items
            cart.total_amount = total_amount
            cart.abandoned_at = datetime.now().isoformat()
            cart.recovered = False  # Resetear si se actualizó
        else:
            # Crear nuevo carrito
            cart = AbandonedCart(
                user_id=user_id,
                session_id=session_id,
                items=items,
                total_amount=total_amount,
                currency=currency,
                abandoned_at=datetime.now().isoformat()
            )
            self._abandoned_carts[cart_key] = cart
        
        # Guardar
        self._save_cart(cart)
    
    def mark_cart_recovered(self, user_id: str, session_id: str):
        """
        Marca un carrito como recuperado (compra completada).
        
        Args:
            user_id: ID del usuario
            session_id: ID de la sesión
        """
        cart_key = f"{user_id}_{session_id}"
        
        if cart_key in self._abandoned_carts:
            cart = self._abandoned_carts[cart_key]
            cart.recovered = True
            cart.recovered_at = datetime.now().isoformat()
            self._save_cart(cart)
    
    def get_abandoned_carts_for_reminder(self) -> List[AbandonedCart]:
        """
        Obtiene carritos que necesitan recordatorio.
        
        Returns:
            Lista de carritos que necesitan recordatorio
        """
        now = datetime.now()
        carts_to_remind = []
        
        for cart in self._abandoned_carts.values():
            if cart.recovered:
                continue
            
            if cart.reminders_sent >= self.max_reminders:
                continue
            
            abandoned_at = datetime.fromisoformat(cart.abandoned_at)
            minutes_since_abandonment = (now - abandoned_at).total_seconds() / 60
            
            # Determinar si necesita recordatorio según intervalos
            next_reminder_interval = self.reminder_intervals_minutes[cart.reminders_sent] if cart.reminders_sent < len(self.reminder_intervals_minutes) else None
            
            if next_reminder_interval and minutes_since_abandonment >= next_reminder_interval:
                # Verificar que no se haya enviado recordatorio recientemente
                if cart.last_reminder_sent:
                    last_reminder = datetime.fromisoformat(cart.last_reminder_sent)
                    minutes_since_last_reminder = (now - last_reminder).total_seconds() / 60
                    if minutes_since_last_reminder < 10:  # No enviar recordatorios muy seguidos
                        continue
                
                carts_to_remind.append(cart)
        
        return carts_to_remind
    
    def mark_reminder_sent(self, cart: AbandonedCart):
        """Marca que se envió un recordatorio."""
        cart.last_reminder_sent = datetime.now().isoformat()
        cart.reminders_sent += 1
        self._save_cart(cart)
    
    def generate_reminder_message(self, cart: AbandonedCart) -> str:
        """
        Genera mensaje de recordatorio personalizado.
        
        Args:
            cart: Carrito abandonado
            
        Returns:
            Mensaje de recordatorio
        """
        items_count = len(cart.items)
        items_description = ", ".join([item.get("name", "producto") for item in cart.items[:3]])
        if items_count > 3:
            items_description += f" y {items_count - 3} más"
        
        # Mensaje personalizado según número de recordatorios
        if cart.reminders_sent == 0:
            message = (
                f"Hola! 👋 Vi que dejaste {items_count} producto(s) en tu carrito: {items_description}. "
                f"¿Tienes alguna pregunta o necesitas ayuda con algo? Estoy aquí para ayudarte."
            )
        elif cart.reminders_sent == 1:
            message = (
                f"Recordatorio amigable: Tu carrito con {items_count} producto(s) sigue esperándote. "
                f"¿Hay algo específico en lo que pueda ayudarte a decidir?"
            )
        else:
            # Último recordatorio, más directo
            message = (
                f"Última oportunidad: Tu carrito con {items_count} producto(s) sigue disponible. "
                f"¿Te gustaría continuar con tu compra o tienes alguna duda que pueda resolver?"
            )
        
        return message
    
    def handle_webhook_event(self, event_data: Dict[str, Any]) -> Optional[AbandonedCart]:
        """
        Maneja evento de webhook de Shopify/WooCommerce (carrito abandonado).
        
        Args:
            event_data: Datos del evento del webhook
            
        Returns:
            AbandonedCart si se detectó abandono, None si no
        """
        # Formato esperado del webhook
        user_id = event_data.get("user_id") or event_data.get("customer_id")
        session_id = event_data.get("session_id") or event_data.get("checkout_token")
        items = event_data.get("items", [])
        total_amount = float(event_data.get("total", 0))
        currency = event_data.get("currency", "USD")
        event_type = event_data.get("event_type", "")
        
        # Solo procesar si es evento de abandono
        if event_type not in ["cart_abandoned", "checkout_abandoned", "cart_updated"]:
            return None
        
        if not user_id or not items:
            return None
        
        # Registrar carrito
        self.track_cart(user_id, session_id, items, total_amount, currency)
        
        return self._abandoned_carts.get(f"{user_id}_{session_id}")
    
    def _save_cart(self, cart: AbandonedCart):
        """Guarda un carrito en disco."""
        cart_file = self.storage_dir / f"cart_{cart.user_id}_{cart.session_id}.json"
        
        try:
            with open(cart_file, "w", encoding="utf-8") as f:
                json.dump(asdict(cart), f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️ Error guardando carrito abandonado: {e}")
    
    def _load_cart(self, user_id: str, session_id: str) -> Optional[AbandonedCart]:
        """Carga un carrito desde disco."""
        cart_file = self.storage_dir / f"cart_{user_id}_{session_id}.json"
        
        if not cart_file.exists():
            return None
        
        try:
            with open(cart_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return AbandonedCart(**data)
        except Exception as e:
            print(f"⚠️ Error cargando carrito: {e}")
            return None

