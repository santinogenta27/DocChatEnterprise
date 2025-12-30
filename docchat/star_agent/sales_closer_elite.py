"""
Sales Closer Elite - Funciones Completas según Especificaciones.

Este módulo contiene las implementaciones completas de las funciones
del Sales Closer Elite según las especificaciones exactas proporcionadas.
"""

from __future__ import annotations

from typing import Dict, Any, Optional, List
from enum import Enum
from datetime import datetime
import json

try:
    import stripe
    STRIPE_AVAILABLE = True
except ImportError:
    STRIPE_AVAILABLE = False
    print("⚠️ Stripe no disponible. Instala con: pip install stripe")


class SalesStage(str, Enum):
    """Etapas de venta según especificaciones."""
    INTEREST = "interest"
    CONSIDERATION = "consideration"
    READY = "ready"
    CLOSING = "closing"
    COMPLETED = "completed"


class SalesStrategy(str, Enum):
    """Estrategias de venta según especificaciones."""
    ANCHORING = "anchoring"
    ROI = "roi"
    SOCIAL_PROOF = "social_proof"
    URGENCY = "urgency"
    STANDARD = "standard"


class SalesCloserElite:
    """
    Sales Closer Elite - Implementación completa según especificaciones.
    
    Código exacto según especificaciones del usuario para:
    - detect_sales_stage()
    - sales_strategy()
    - handle_objection()
    - close_sale()
    - request_payment()
    - log_event()
    """
    
    def __init__(self, stripe_api_key: Optional[str] = None):
        """
        Inicializa Sales Closer Elite.
        
        Args:
            stripe_api_key: API key de Stripe para pagos (opcional)
        """
        if STRIPE_AVAILABLE and stripe_api_key:
            stripe.api_key = stripe_api_key
            self.stripe_enabled = True
        else:
            self.stripe_enabled = False
        
        # Métricas de eventos
        self.event_log: List[Dict[str, Any]] = []
    
    def detect_sales_stage(self, query: str) -> str:
        """
        Detecta etapa de venta según especificaciones exactas.
        
        Código exacto según especificaciones:
        - "precio", "cuánto cuesta", "comprar", "pagar" -> READY
        - "envío", "funciona", "garantía" -> CONSIDERATION
        - default -> INTEREST
        
        Args:
            query: Consulta del usuario
            
        Returns:
            Etapa de venta detectada (READY, CONSIDERATION, INTEREST)
        """
        q = query.lower()
        if any(x in q for x in ["precio", "cuánto cuesta", "comprar", "pagar"]):
            return SalesStage.READY.value
        if any(x in q for x in ["envío", "funciona", "garantía"]):
            return SalesStage.CONSIDERATION.value
        return SalesStage.INTEREST.value
    
    def sales_strategy(self, query: str) -> str:
        """
        Selecciona estrategia de venta según especificaciones exactas.
        
        Código exacto según especificaciones:
        - "precio" -> ANCHORING
        - "vale la pena" -> ROI
        - "opiniones" -> SOCIAL_PROOF
        - default -> STANDARD
        
        Args:
            query: Consulta del usuario
            
        Returns:
            Estrategia de venta (ANCHORING, ROI, SOCIAL_PROOF, STANDARD)
        """
        q = query.lower()
        if "precio" in q:
            return SalesStrategy.ANCHORING.value
        if "vale la pena" in q:
            return SalesStrategy.ROI.value
        if "opiniones" in q:
            return SalesStrategy.SOCIAL_PROOF.value
        return SalesStrategy.STANDARD.value
    
    def handle_objection(self, objection: str) -> str:
        """
        Maneja objeciones según especificaciones exactas.
        
        Código exacto según especificaciones:
        - "caro" -> respuesta sobre valor a largo plazo
        - "después" -> pregunta sobre qué tendría que pasar
        - otros -> respuesta genérica
        
        Args:
            objection: Objeción del cliente
            
        Returns:
            Respuesta para manejar la objeción
        """
        objection_lower = objection.lower()
        
        if "caro" in objection_lower:
            return "Entiendo. Justamente por eso incluye X, Y y Z que ahorran dinero a largo plazo."
        
        if "después" in objection_lower:
            return "Tiene sentido. ¿Qué tendría que pasar para que lo veas útil ahora?"
        
        # Respuesta genérica para otras objeciones
        return "Entiendo tu preocupación. ¿Puedes contarme más sobre qué te preocupa específicamente?"
    
    def close_sale(self) -> str:
        """
        Cierre directo según especificaciones exactas.
        
        Código exacto según especificaciones:
        "¿Querés que lo procesemos ahora y te lo envío enseguida?"
        
        Returns:
            Mensaje de cierre directo
        """
        return "¿Querés que lo procesemos ahora y te lo envío enseguida?"
    
    def create_payment_link(self, product_id: str, amount: float, currency: str = "usd") -> Optional[str]:
        """
        Crea link de pago usando Stripe según especificaciones.
        
        Args:
            product_id: ID del producto en Stripe
            amount: Monto a cobrar
            currency: Moneda (default: usd)
            
        Returns:
            URL del link de pago o None si hay error
        """
        if not self.stripe_enabled:
            print("⚠️ Stripe no está habilitado. Configura stripe_api_key.")
            return None
        
        try:
            # Crear precio si no existe
            price = stripe.Price.create(
                unit_amount=int(amount * 100),  # Stripe usa centavos
                currency=currency,
                product=product_id,
            )
            
            # Crear Payment Link
            payment_link = stripe.PaymentLink.create(
                line_items=[{'price': price.id, 'quantity': 1}],
                mode='payment'
            )
            
            return payment_link.url
        except Exception as e:
            print(f"❌ Error creando payment link: {e}")
            return None
    
    def request_payment(self, session_id: str, cart: Dict[str, Any]) -> Dict[str, Any]:
        """
        Solicita pago para el carrito.
        
        Args:
            session_id: ID de sesión
            cart: Información del carrito
            
        Returns:
            Dict con payment_link y metadata
        """
        # Calcular total del carrito
        total = sum(
            item.get("price", 0) * item.get("quantity", 1)
            for item in cart.get("items", [])
        )
        
        if total <= 0:
            return {
                "error": True,
                "message": "El carrito está vacío"
            }
        
        # Crear payment link (usar primer producto como referencia)
        items = cart.get("items", [])
        if not items:
            return {
                "error": True,
                "message": "No hay items en el carrito"
            }
        
        # Obtener product_id del primer item
        product_id = items[0].get("product_id", "default_product")
        payment_link = self.create_payment_link(product_id, total)
        
        if not payment_link:
            return {
                "error": True,
                "message": "Error creando link de pago"
            }
        
        # Log del evento
        self.log_event(
            event_type="payment_initiated",
            session_id=session_id,
            metadata={
                "total": total,
                "items_count": len(items),
                "payment_link": payment_link,
            }
        )
        
        return {
            "payment_link": payment_link,
            "total": total,
            "currency": "usd",
            "session_id": session_id,
        }
    
    def log_event(
        self,
        event_type: str,
        session_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Registra evento para métricas.
        
        Args:
            event_type: Tipo de evento (conversion, cart_add, payment_initiated, etc.)
            session_id: ID de sesión
            metadata: Metadata adicional del evento
        """
        event = {
            "event_type": event_type,
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {},
        }
        
        self.event_log.append(event)
    
    def get_conversion_metrics(self) -> Dict[str, Any]:
        """
        Obtiene métricas de conversión.
        
        Returns:
            Dict con métricas (conversion_rate, revenue, drop_off, etc.)
        """
        total_sessions = len(set(e["session_id"] for e in self.event_log))
        conversions = len([e for e in self.event_log if e["event_type"] == "conversion"])
        payments = len([e for e in self.event_log if e["event_type"] == "payment_initiated"])
        cart_adds = len([e for e in self.event_log if e["event_type"] == "cart_add"])
        
        conversion_rate = (conversions / total_sessions * 100) if total_sessions > 0 else 0
        drop_off_rate = ((cart_adds - payments) / cart_adds * 100) if cart_adds > 0 else 0
        
        # Calcular revenue total
        revenue = sum(
            e["metadata"].get("total", 0)
            for e in self.event_log
            if e["event_type"] == "payment_completed" and "total" in e.get("metadata", {})
        )
        
        return {
            "total_sessions": total_sessions,
            "conversions": conversions,
            "conversion_rate": round(conversion_rate, 2),
            "cart_adds": cart_adds,
            "payments_initiated": payments,
            "drop_off_rate": round(drop_off_rate, 2),
            "revenue": revenue,
        }

