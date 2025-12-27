"""
Subscription Service - Gestión de Suscripciones
Inspirado en Sierra.ai - Permite crear, actualizar y gestionar suscripciones
"""

from __future__ import annotations

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
import json


class SubscriptionStatus(Enum):
    """Estado de la suscripción."""
    ACTIVE = "active"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


@dataclass
class Subscription:
    """Modelo de suscripción."""
    subscription_id: str
    customer_id: str
    session_id: str
    product_id: str
    product_name: str
    frequency_weeks: int  # Cada cuántas semanas se entrega
    next_delivery_date: str  # ISO format
    delivery_address: Dict[str, Any]
    payment_method: str  # "card_on_file", "paypal", etc.
    discount_percentage: float  # Descuento por suscripción
    status: SubscriptionStatus
    created_at: str
    updated_at: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class SubscriptionService:
    """
    Servicio de gestión de suscripciones.
    
    Permite:
    - Crear suscripciones
    - Actualizar direcciones de entrega
    - Cambiar frecuencia
    - Pausar/reanudar
    - Cancelar
    """
    
    def __init__(self, storage_dir: Optional[Path] = None):
        """Inicializa el servicio de suscripciones."""
        if storage_dir is None:
            storage_dir = Path("memory") / "customer_business_agent" / "subscriptions"
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._subscriptions: Dict[str, Subscription] = {}
        self._load_subscriptions()
    
    def _load_subscriptions(self):
        """Carga suscripciones desde disco."""
        subscriptions_file = self.storage_dir / "subscriptions.json"
        if subscriptions_file.exists():
            try:
                with open(subscriptions_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for sub_data in data.get("subscriptions", []):
                        sub = Subscription(**sub_data)
                        sub.status = SubscriptionStatus(sub.status) if isinstance(sub.status, str) else sub.status
                        self._subscriptions[sub.subscription_id] = sub
            except Exception as e:
                print(f"⚠️ Error cargando suscripciones: {e}")
    
    def _save_subscriptions(self):
        """Guarda suscripciones en disco."""
        subscriptions_file = self.storage_dir / "subscriptions.json"
        try:
            data = {
                "subscriptions": [
                    {
                        "subscription_id": sub.subscription_id,
                        "customer_id": sub.customer_id,
                        "session_id": sub.session_id,
                        "product_id": sub.product_id,
                        "product_name": sub.product_name,
                        "frequency_weeks": sub.frequency_weeks,
                        "next_delivery_date": sub.next_delivery_date,
                        "delivery_address": sub.delivery_address,
                        "payment_method": sub.payment_method,
                        "discount_percentage": sub.discount_percentage,
                        "status": sub.status.value,
                        "created_at": sub.created_at,
                        "updated_at": sub.updated_at,
                        "metadata": sub.metadata,
                    }
                    for sub in self._subscriptions.values()
                ]
            }
            with open(subscriptions_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️ Error guardando suscripciones: {e}")
    
    def create_subscription(
        self,
        customer_id: str,
        session_id: str,
        product_id: str,
        product_name: str,
        frequency_weeks: int = 4,
        delivery_address: Optional[Dict[str, Any]] = None,
        payment_method: str = "card_on_file",
        discount_percentage: float = 15.0,
    ) -> Subscription:
        """
        Crea una nueva suscripción.
        
        Args:
            customer_id: ID del cliente
            session_id: ID de sesión
            product_id: ID del producto
            product_name: Nombre del producto
            frequency_weeks: Frecuencia en semanas (default: 4 = mensual)
            delivery_address: Dirección de entrega
            payment_method: Método de pago
            discount_percentage: Descuento por suscripción
            
        Returns:
            Subscription creada
        """
        subscription_id = f"sub_{len(self._subscriptions) + 1}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Calcular próxima fecha de entrega
        next_delivery = datetime.now() + timedelta(weeks=frequency_weeks)
        
        subscription = Subscription(
            subscription_id=subscription_id,
            customer_id=customer_id,
            session_id=session_id,
            product_id=product_id,
            product_name=product_name,
            frequency_weeks=frequency_weeks,
            next_delivery_date=next_delivery.isoformat(),
            delivery_address=delivery_address or {},
            payment_method=payment_method,
            discount_percentage=discount_percentage,
            status=SubscriptionStatus.ACTIVE,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
        )
        
        self._subscriptions[subscription_id] = subscription
        self._save_subscriptions()
        
        return subscription
    
    def get_subscription(self, subscription_id: str) -> Optional[Subscription]:
        """Obtiene una suscripción por ID."""
        return self._subscriptions.get(subscription_id)
    
    def get_customer_subscriptions(self, customer_id: str) -> List[Subscription]:
        """Obtiene todas las suscripciones de un cliente."""
        return [sub for sub in self._subscriptions.values() if sub.customer_id == customer_id]
    
    def update_delivery_address(
        self,
        subscription_id: str,
        new_address: Dict[str, Any],
    ) -> Optional[Subscription]:
        """
        Actualiza la dirección de entrega de una suscripción.
        
        Args:
            subscription_id: ID de la suscripción
            new_address: Nueva dirección (name, street, city, state, zip, country)
            
        Returns:
            Subscription actualizada o None si no existe
        """
        subscription = self._subscriptions.get(subscription_id)
        if not subscription:
            return None
        
        subscription.delivery_address = new_address
        subscription.updated_at = datetime.now().isoformat()
        self._save_subscriptions()
        
        return subscription
    
    def update_frequency(
        self,
        subscription_id: str,
        new_frequency_weeks: int,
    ) -> Optional[Subscription]:
        """
        Actualiza la frecuencia de entrega.
        
        Args:
            subscription_id: ID de la suscripción
            new_frequency_weeks: Nueva frecuencia en semanas
            
        Returns:
            Subscription actualizada o None si no existe
        """
        subscription = self._subscriptions.get(subscription_id)
        if not subscription:
            return None
        
        subscription.frequency_weeks = new_frequency_weeks
        # Recalcular próxima entrega
        next_delivery = datetime.fromisoformat(subscription.next_delivery_date)
        # Ajustar basándose en la nueva frecuencia
        subscription.next_delivery_date = (next_delivery + timedelta(weeks=new_frequency_weeks)).isoformat()
        subscription.updated_at = datetime.now().isoformat()
        self._save_subscriptions()
        
        return subscription
    
    def pause_subscription(self, subscription_id: str) -> Optional[Subscription]:
        """Pausa una suscripción."""
        subscription = self._subscriptions.get(subscription_id)
        if not subscription:
            return None
        
        subscription.status = SubscriptionStatus.PAUSED
        subscription.updated_at = datetime.now().isoformat()
        self._save_subscriptions()
        
        return subscription
    
    def resume_subscription(self, subscription_id: str) -> Optional[Subscription]:
        """Reanuda una suscripción pausada."""
        subscription = self._subscriptions.get(subscription_id)
        if not subscription:
            return None
        
        subscription.status = SubscriptionStatus.ACTIVE
        subscription.updated_at = datetime.now().isoformat()
        self._save_subscriptions()
        
        return subscription
    
    def cancel_subscription(self, subscription_id: str) -> Optional[Subscription]:
        """Cancela una suscripción."""
        subscription = self._subscriptions.get(subscription_id)
        if not subscription:
            return None
        
        subscription.status = SubscriptionStatus.CANCELLED
        subscription.updated_at = datetime.now().isoformat()
        self._save_subscriptions()
        
        return subscription
    
    def is_customer_subscription_candidate(
        self,
        customer_id: str,
        order_history: List[Dict[str, Any]],
        total_spent: float,
    ) -> bool:
        """
        Determina si un cliente es buen candidato para suscripción.
        
        Basado en:
        - Historial de pedidos (regularidad)
        - Total gastado
        - Tipo de productos comprados
        
        Returns:
            True si es buen candidato
        """
        # Criterios simples (se pueden mejorar con ML)
        if len(order_history) >= 2:  # Al menos 2 pedidos previos
            return True
        
        if total_spent > 100:  # Ha gastado más de $100
            return True
        
        return False

