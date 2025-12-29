from __future__ import annotations

import os
from typing import Dict, Any, Optional

try:
    import stripe
    STRIPE_AVAILABLE = True
except ImportError:
    STRIPE_AVAILABLE = False
    stripe = None

from ...commerce.payment_processor import PaymentProcessor, PaymentResult, PaymentMethod
from ...commerce.cart_manager import Cart


class PaymentTool:
    """
    Wrapper de pago que recibe un Cart y procesa el cobro.
    
    Integración completa con Stripe según especificaciones:
    - Payment Links para checkout rápido
    - Payment Intents para procesamiento directo
    - Soporte para múltiples métodos de pago
    """

    def __init__(self, payment_processor: PaymentProcessor) -> None:
        self.payment_processor = payment_processor
        
        # Inicializar Stripe si está disponible
        self.stripe_api_key = os.getenv("STRIPE_SECRET_KEY") or os.getenv("STRIPE_API_KEY")
        if STRIPE_AVAILABLE and self.stripe_api_key:
            stripe.api_key = self.stripe_api_key
            self.stripe_enabled = True
        else:
            self.stripe_enabled = False
            if not STRIPE_AVAILABLE:
                print("⚠️ Stripe no disponible. Instala con: pip install stripe")

    def create_payment_for_cart(
        self,
        session_id: str,
        cart: Cart,
        payment_method: str = "stripe",
        currency: str = "usd",
        metadata: Dict[str, Any] | None = None,
    ) -> PaymentResult:
        """
        Crea pago para carrito con integración Stripe completa.
        
        Args:
            session_id: ID de sesión del cliente
            cart: Carrito con items
            payment_method: Método de pago (stripe, paypal, etc.)
            currency: Moneda (usd, eur, etc.)
            metadata: Metadata adicional
            
        Returns:
            PaymentResult con payment_link o payment_intent
        """
        if not cart.items:
            raise ValueError("El carrito está vacío")

        amount = cart.total
        method = PaymentMethod(payment_method)

        # Si es Stripe y está habilitado, usar Payment Links
        if payment_method == "stripe" and self.stripe_enabled:
            return self._create_stripe_payment_link(
                session_id=session_id,
                cart=cart,
                amount=amount,
                currency=currency,
                metadata=metadata,
            )
        
        # Fallback a PaymentProcessor estándar
        intent = self.payment_processor.create_payment_intent(
            session_id=session_id,
            amount=amount,
            currency=currency,
            payment_method=method,
            metadata=metadata or {"cart_id": cart.cart_id},
        )

        return intent
    
    def _create_stripe_payment_link(
        self,
        session_id: str,
        cart: Cart,
        amount: float,
        currency: str,
        metadata: Optional[Dict[str, Any]],
    ) -> PaymentResult:
        """
        Crea Payment Link de Stripe para checkout rápido.
        
        Implementa:
        - Payment Links para widget web
        - Line items desde carrito
        - Metadata de sesión
        """
        try:
            # Crear line items desde carrito
            line_items = []
            for item in cart.items:
                # Buscar precio del producto
                price_data = {
                    "currency": currency,
                    "product_data": {
                        "name": getattr(item, 'product_name', f"Product {item.product_id}"),
                        "description": getattr(item, 'product_description', ''),
                    },
                    "unit_amount": int(getattr(item, 'price', 0) * 100),  # Stripe usa centavos
                }
                
                line_items.append({
                    "price_data": price_data,
                    "quantity": item.quantity,
                })
            
            # Crear Payment Link
            payment_link = stripe.PaymentLink.create(
                line_items=line_items,
                mode='payment',
                metadata={
                    "session_id": session_id,
                    "cart_id": cart.cart_id,
                    **(metadata or {}),
                },
                after_completion={
                    "type": "redirect",
                    "redirect": {
                        "url": f"https://your-website.com/thank-you?session_id={session_id}"
                    }
                }
            )
            
            # Crear PaymentResult compatible
            result = PaymentResult(
                payment_id=payment_link.id,
                status="pending",
                amount=amount,
                currency=currency,
                payment_method=PaymentMethod("stripe"),
            )
            
            # Agregar payment_link como atributo adicional
            result.payment_link = payment_link.url
            result.payment_link_id = payment_link.id
            
            return result
            
        except Exception as e:
            print(f"⚠️ Error creando Stripe Payment Link: {e}")
            # Fallback a método estándar
            return self.payment_processor.create_payment_intent(
                session_id=session_id,
                amount=amount,
                currency=currency,
                payment_method=PaymentMethod("stripe"),
                metadata=metadata or {"cart_id": cart.cart_id},
            )
    
    def create_payment_link(
        self,
        product_id: str,
        amount: float,
        currency: str = "usd",
    ) -> str:
        """
        Crea Payment Link simple de Stripe (función directa según especificaciones).
        
        Args:
            product_id: ID del producto
            amount: Monto en la moneda especificada
            currency: Moneda (usd, eur, etc.)
            
        Returns:
            URL del Payment Link
        """
        if not self.stripe_enabled:
            raise ValueError("Stripe no está habilitado. Configura STRIPE_SECRET_KEY")
        
        try:
            payment_link = stripe.PaymentLink.create(
                line_items=[{
                    'price_data': {
                        'currency': currency,
                        'product': product_id,
                        'unit_amount': int(amount * 100),  # Convertir a centavos
                    },
                    'quantity': 1,
                }],
                mode='payment'
            )
            return payment_link.url
        except Exception as e:
            raise ValueError(f"Error creando Payment Link: {e}")

