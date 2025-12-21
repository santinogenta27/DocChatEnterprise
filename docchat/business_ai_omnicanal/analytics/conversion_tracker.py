"""
Conversion Tracker - Tracking de Conversiones Completo
Rastrea eventos críticos: add_to_cart, checkout, purchase_complete
Integración con Google Analytics, Meta Pixel, y tracking interno
"""

from __future__ import annotations

import json
import time
from typing import Dict, Optional, Any, List
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict, field
from enum import Enum


class ConversionEvent(Enum):
    """Eventos de conversión rastreables."""
    PRODUCT_VIEWED = "product_viewed"
    ADD_TO_CART = "add_to_cart"
    REMOVE_FROM_CART = "remove_from_cart"
    INITIATE_CHECKOUT = "initiate_checkout"
    ADD_PAYMENT_INFO = "add_payment_info"
    PURCHASE_COMPLETE = "purchase_complete"
    LEAD_GENERATED = "lead_generated"
    APPOINTMENT_BOOKED = "appointment_booked"


@dataclass
class ConversionEventData:
    """Datos de un evento de conversión."""
    event_type: ConversionEvent
    session_id: str
    user_id: str
    timestamp: str
    value: float = 0.0  # Valor monetario del evento
    currency: str = "USD"
    product_id: Optional[str] = None
    product_name: Optional[str] = None
    quantity: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)


class ConversionTracker:
    """
    Tracker de conversiones completo.
    
    Características:
    - Tracking de eventos críticos (add_to_cart, checkout, purchase)
    - Integración con Google Analytics, Meta Pixel
    - Tracking interno en base de datos
    - Métricas de ROI y conversión
    """
    
    def __init__(self, storage_dir: Path, enable_ga: bool = False, enable_meta_pixel: bool = False):
        """
        Inicializa el tracker de conversiones.
        
        Args:
            storage_dir: Directorio para almacenar eventos
            enable_ga: Habilitar Google Analytics (requiere GA_ID)
            enable_meta_pixel: Habilitar Meta Pixel (requiere PIXEL_ID)
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Configuración
        self.enable_ga = enable_ga
        self.enable_meta_pixel = enable_meta_pixel
        self.ga_id = None
        self.pixel_id = None
        
        # Cargar configuración si está habilitada
        if enable_ga:
            import os
            self.ga_id = os.getenv("GOOGLE_ANALYTICS_ID")
        
        if enable_meta_pixel:
            import os
            self.pixel_id = os.getenv("META_PIXEL_ID")
        
        # Eventos en memoria (para batch writing)
        self._events_buffer: List[ConversionEventData] = []
        self._buffer_size = 10
    
    def track_event(self,
                   event_type: ConversionEvent,
                   session_id: str,
                   user_id: str,
                   value: float = 0.0,
                   currency: str = "USD",
                   product_id: Optional[str] = None,
                   product_name: Optional[str] = None,
                   quantity: int = 1,
                   metadata: Optional[Dict] = None) -> ConversionEventData:
        """
        Rastrea un evento de conversión.
        
        Args:
            event_type: Tipo de evento
            session_id: ID de la sesión
            user_id: ID del usuario
            value: Valor monetario
            currency: Moneda
            product_id: ID del producto (opcional)
            product_name: Nombre del producto (opcional)
            quantity: Cantidad
            metadata: Metadata adicional
            
        Returns:
            ConversionEventData registrado
        """
        event_data = ConversionEventData(
            event_type=event_type,
            session_id=session_id,
            user_id=user_id,
            timestamp=datetime.now().isoformat(),
            value=value,
            currency=currency,
            product_id=product_id,
            product_name=product_name,
            quantity=quantity,
            metadata=metadata or {}
        )
        
        # Añadir a buffer
        self._events_buffer.append(event_data)
        
        # Escribir si el buffer está lleno
        if len(self._events_buffer) >= self._buffer_size:
            self._flush_buffer()
        
        # Enviar a servicios externos
        self._send_to_external_services(event_data)
        
        # Log
        print(f"📊 [Conversion Tracking] {event_type.value}: {product_name or 'N/A'} | Value: {value} {currency} | Session: {session_id[:8]}")
        
        return event_data
    
    def track_product_viewed(self, session_id: str, user_id: str, product_id: str, product_name: str, price: float = 0.0):
        """Rastrea visualización de producto."""
        return self.track_event(
            event_type=ConversionEvent.PRODUCT_VIEWED,
            session_id=session_id,
            user_id=user_id,
            value=price,
            product_id=product_id,
            product_name=product_name
        )
    
    def track_add_to_cart(self, session_id: str, user_id: str, product_id: str, product_name: str, price: float, quantity: int = 1):
        """Rastrea producto añadido al carrito."""
        return self.track_event(
            event_type=ConversionEvent.ADD_TO_CART,
            session_id=session_id,
            user_id=user_id,
            value=price * quantity,
            product_id=product_id,
            product_name=product_name,
            quantity=quantity
        )
    
    def track_initiate_checkout(self, session_id: str, user_id: str, cart_value: float, items: List[Dict]):
        """Rastrea inicio de checkout."""
        return self.track_event(
            event_type=ConversionEvent.INITIATE_CHECKOUT,
            session_id=session_id,
            user_id=user_id,
            value=cart_value,
            metadata={"items": items}
        )
    
    def track_purchase_complete(self, session_id: str, user_id: str, order_id: str, total: float, items: List[Dict], currency: str = "USD"):
        """Rastrea compra completada."""
        return self.track_event(
            event_type=ConversionEvent.PURCHASE_COMPLETE,
            session_id=session_id,
            user_id=user_id,
            value=total,
            currency=currency,
            metadata={
                "order_id": order_id,
                "items": items
            }
        )
    
    def track_lead_generated(self, session_id: str, user_id: str, lead_score: float, lead_source: str = "chatbot"):
        """Rastrea generación de lead."""
        return self.track_event(
            event_type=ConversionEvent.LEAD_GENERATED,
            session_id=session_id,
            user_id=user_id,
            value=lead_score,  # Usar score como valor estimado
            metadata={"lead_source": lead_source, "lead_score": lead_score}
        )
    
    def _flush_buffer(self):
        """Escribe eventos del buffer a disco."""
        if not self._events_buffer:
            return
        
        # Escribir a archivo JSON
        events_file = self.storage_dir / f"conversion_events_{datetime.now().strftime('%Y%m%d')}.jsonl"
        
        try:
            with open(events_file, "a", encoding="utf-8") as f:
                for event in self._events_buffer:
                    f.write(json.dumps(asdict(event), ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"⚠️ Error escribiendo eventos de conversión: {e}")
        
        # Limpiar buffer
        self._events_buffer.clear()
    
    def _send_to_external_services(self, event_data: ConversionEventData):
        """Envía eventos a servicios externos (GA, Meta Pixel)."""
        # Google Analytics
        if self.enable_ga and self.ga_id:
            self._send_to_google_analytics(event_data)
        
        # Meta Pixel
        if self.enable_meta_pixel and self.pixel_id:
            self._send_to_meta_pixel(event_data)
    
    def _send_to_google_analytics(self, event_data: ConversionEventData):
        """Envía evento a Google Analytics (Measurement Protocol)."""
        try:
            import requests
            
            ga_endpoint = f"https://www.google-analytics.com/mp/collect?measurement_id={self.ga_id}&api_secret=YOUR_API_SECRET"
            
            payload = {
                "client_id": event_data.user_id,
                "events": [{
                    "name": event_data.event_type.value,
                    "params": {
                        "value": event_data.value,
                        "currency": event_data.currency,
                        "items": [{
                            "item_id": event_data.product_id,
                            "item_name": event_data.product_name,
                            "quantity": event_data.quantity,
                            "price": event_data.value / event_data.quantity if event_data.quantity > 0 else event_data.value
                        }] if event_data.product_id else []
                    }
                }]
            }
            
            # Nota: En producción, esto debe hacerse de forma asíncrona
            # requests.post(ga_endpoint, json=payload, timeout=2)
            
        except Exception as e:
            print(f"⚠️ Error enviando a Google Analytics: {e}")
    
    def _send_to_meta_pixel(self, event_data: ConversionEventData):
        """Envía evento a Meta Pixel (Conversions API)."""
        try:
            import requests
            
            meta_endpoint = f"https://graph.facebook.com/v18.0/{self.pixel_id}/events"
            
            payload = {
                "data": [{
                    "event_name": event_data.event_type.value,
                    "event_time": int(time.time()),
                    "user_data": {
                        "external_id": event_data.user_id
                    },
                    "custom_data": {
                        "value": event_data.value,
                        "currency": event_data.currency
                    }
                }]
            }
            
            # Nota: Requiere access_token, debe hacerse de forma asíncrona en producción
            # requests.post(meta_endpoint, json=payload, headers={"Authorization": f"Bearer {access_token}"}, timeout=2)
            
        except Exception as e:
            print(f"⚠️ Error enviando a Meta Pixel: {e}")
    
    def get_conversion_stats(self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Obtiene estadísticas de conversión.
        
        Args:
            start_date: Fecha de inicio
            end_date: Fecha de fin
            
        Returns:
            Dict con estadísticas
        """
        # Cargar eventos del período
        events = self._load_events_period(start_date, end_date)
        
        # Calcular métricas
        total_revenue = sum(e.value for e in events if e.event_type == ConversionEvent.PURCHASE_COMPLETE)
        total_adds_to_cart = len([e for e in events if e.event_type == ConversionEvent.ADD_TO_CART])
        total_checkouts = len([e for e in events if e.event_type == ConversionEvent.INITIATE_CHECKOUT])
        total_purchases = len([e for e in events if e.event_type == ConversionEvent.PURCHASE_COMPLETE])
        total_leads = len([e for e in events if e.event_type == ConversionEvent.LEAD_GENERATED])
        
        # Calcular tasas de conversión
        cart_to_checkout_rate = (total_checkouts / total_adds_to_cart * 100) if total_adds_to_cart > 0 else 0
        checkout_to_purchase_rate = (total_purchases / total_checkouts * 100) if total_checkouts > 0 else 0
        overall_conversion_rate = (total_purchases / len(events) * 100) if events else 0
        
        return {
            "period": {
                "start": start_date.isoformat() if start_date else None,
                "end": end_date.isoformat() if end_date else None
            },
            "events": {
                "total": len(events),
                "add_to_cart": total_adds_to_cart,
                "checkouts": total_checkouts,
                "purchases": total_purchases,
                "leads": total_leads
            },
            "revenue": {
                "total": total_revenue,
                "average_order_value": total_revenue / total_purchases if total_purchases > 0 else 0
            },
            "conversion_rates": {
                "cart_to_checkout": cart_to_checkout_rate,
                "checkout_to_purchase": checkout_to_purchase_rate,
                "overall": overall_conversion_rate
            }
        }
    
    def _load_events_period(self, start_date: Optional[datetime], end_date: Optional[datetime]) -> List[ConversionEventData]:
        """Carga eventos del período especificado."""
        events = []
        
        # Flush buffer primero
        self._flush_buffer()
        
        # Cargar eventos de archivos JSONL
        for events_file in self.storage_dir.glob("conversion_events_*.jsonl"):
            try:
                with open(events_file, "r", encoding="utf-8") as f:
                    for line in f:
                        if not line.strip():
                            continue
                        event_dict = json.loads(line)
                        event = ConversionEventData(**event_dict)
                        
                        # Filtrar por fecha
                        event_time = datetime.fromisoformat(event.timestamp)
                        if start_date and event_time < start_date:
                            continue
                        if end_date and event_time > end_date:
                            continue
                        
                        events.append(event)
            except Exception as e:
                print(f"⚠️ Error cargando eventos de {events_file}: {e}")
        
        return events
    
    def flush(self):
        """Fuerza escritura de buffer (llamar antes de cerrar)."""
        self._flush_buffer()

