"""
Payment Processor - Integración con Stripe y PayPal
Procesa pagos end-to-end dentro del chat
"""

from __future__ import annotations

import os
from enum import Enum
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime

try:
    import stripe
    STRIPE_AVAILABLE = True
except ImportError:
    STRIPE_AVAILABLE = False
    stripe = None

try:
    from paypalrestsdk import Payment as PayPalPayment
    PAYPAL_AVAILABLE = True
except ImportError:
    PAYPAL_AVAILABLE = False
    PayPalPayment = None


class PaymentMethod(Enum):
    """Métodos de pago soportados."""
    STRIPE = "stripe"
    PAYPAL = "paypal"
    META_PAY = "meta_pay"  # Futuro


@dataclass
class PaymentResult:
    """Resultado de un pago procesado."""
    success: bool
    payment_id: str
    payment_method: PaymentMethod
    amount: float
    currency: str = "USD"
    status: str = "pending"
    transaction_id: Optional[str] = None
    error_message: Optional[str] = None
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()


class PaymentProcessor:
    """
    Procesador de pagos con integración real a Stripe y PayPal.
    
    Características:
    - Procesa pagos dentro del chat
    - Soporta Stripe y PayPal
    - Genera links de pago seguros
    - Confirma pagos automáticamente
    """
    
    def __init__(self, config: Any):
        """
        Inicializa el procesador de pagos.
        
        Args:
            config: Configuración de la aplicación
        """
        self.config = config
        
        # Configurar Stripe
        self.stripe_secret_key = os.getenv("STRIPE_SECRET_KEY") or getattr(config, 'stripe_secret_key', None)
        self.stripe_publishable_key = os.getenv("STRIPE_PUBLISHABLE_KEY") or getattr(config, 'stripe_publishable_key', None)
        
        if STRIPE_AVAILABLE and self.stripe_secret_key:
            stripe.api_key = self.stripe_secret_key
            self.stripe_enabled = True
        else:
            self.stripe_enabled = False
            print("⚠️ Stripe no disponible. Instala con: pip install stripe")
        
        # Configurar PayPal
        self.paypal_client_id = os.getenv("PAYPAL_CLIENT_ID") or getattr(config, 'paypal_client_id', None)
        self.paypal_client_secret = os.getenv("PAYPAL_CLIENT_SECRET") or getattr(config, 'paypal_client_secret', None)
        self.paypal_mode = os.getenv("PAYPAL_MODE", "sandbox")  # sandbox o live
        
        if PAYPAL_AVAILABLE and self.paypal_client_id and self.paypal_client_secret:
            PayPalPayment.configure({
                "mode": self.paypal_mode,
                "client_id": self.paypal_client_id,
                "client_secret": self.paypal_client_secret
            })
            self.paypal_enabled = True
        else:
            self.paypal_enabled = False
            print("⚠️ PayPal no disponible. Instala con: pip install paypalrestsdk")
    
    def create_payment_intent(
        self,
        amount: float,
        currency: str = "USD",
        payment_method: PaymentMethod = PaymentMethod.STRIPE,
        metadata: Optional[Dict[str, Any]] = None
    ) -> PaymentResult:
        """
        Crea una intención de pago.
        
        Args:
            amount: Monto a pagar
            currency: Moneda (USD, EUR, etc.)
            payment_method: Método de pago
            metadata: Metadata adicional (order_id, customer_id, etc.)
        
        Returns:
            PaymentResult con payment_id para completar el pago
        """
        if payment_method == PaymentMethod.STRIPE:
            return self._create_stripe_payment_intent(amount, currency, metadata)
        elif payment_method == PaymentMethod.PAYPAL:
            return self._create_paypal_payment(amount, currency, metadata)
        else:
            return PaymentResult(
                success=False,
                payment_id="",
                payment_method=payment_method,
                amount=amount,
                currency=currency,
                error_message=f"Método de pago no soportado: {payment_method.value}"
            )
    
    def _create_stripe_payment_intent(
        self,
        amount: float,
        currency: str,
        metadata: Optional[Dict[str, Any]]
    ) -> PaymentResult:
        """Crea un Payment Intent de Stripe."""
        if not self.stripe_enabled:
            # Modo simulación
            payment_id = f"pi_sim_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            return PaymentResult(
                success=True,
                payment_id=payment_id,
                payment_method=PaymentMethod.STRIPE,
                amount=amount,
                currency=currency,
                status="requires_payment_method"
            )
        
        try:
            intent = stripe.PaymentIntent.create(
                amount=int(amount * 100),  # Stripe usa centavos
                currency=currency.lower(),
                metadata=metadata or {},
                automatic_payment_methods={
                    "enabled": True
                }
            )
            
            return PaymentResult(
                success=True,
                payment_id=intent.id,
                payment_method=PaymentMethod.STRIPE,
                amount=amount,
                currency=currency,
                status=intent.status,
                transaction_id=intent.id
            )
        except Exception as e:
            return PaymentResult(
                success=False,
                payment_id="",
                payment_method=PaymentMethod.STRIPE,
                amount=amount,
                currency=currency,
                error_message=str(e)
            )
    
    def _create_paypal_payment(
        self,
        amount: float,
        currency: str,
        metadata: Optional[Dict[str, Any]]
    ) -> PaymentResult:
        """Crea un pago de PayPal."""
        if not self.paypal_enabled:
            # Modo simulación
            payment_id = f"paypal_sim_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            return PaymentResult(
                success=True,
                payment_id=payment_id,
                payment_method=PaymentMethod.PAYPAL,
                amount=amount,
                currency=currency,
                status="created"
            )
        
        try:
            payment = PayPalPayment({
                "intent": "sale",
                "payer": {
                    "payment_method": "paypal"
                },
                "transactions": [{
                    "amount": {
                        "total": f"{amount:.2f}",
                        "currency": currency
                    },
                    "description": metadata.get("description", "Purchase") if metadata else "Purchase"
                }],
                "redirect_urls": {
                    "return_url": metadata.get("return_url", "https://example.com/success") if metadata else "https://example.com/success",
                    "cancel_url": metadata.get("cancel_url", "https://example.com/cancel") if metadata else "https://example.com/cancel"
                }
            })
            
            if payment.create():
                return PaymentResult(
                    success=True,
                    payment_id=payment.id,
                    payment_method=PaymentMethod.PAYPAL,
                    amount=amount,
                    currency=currency,
                    status="created",
                    transaction_id=payment.id
                )
            else:
                return PaymentResult(
                    success=False,
                    payment_id="",
                    payment_method=PaymentMethod.PAYPAL,
                    amount=amount,
                    currency=currency,
                    error_message=str(payment.error)
                )
        except Exception as e:
            return PaymentResult(
                success=False,
                payment_id="",
                payment_method=PaymentMethod.PAYPAL,
                amount=amount,
                currency=currency,
                error_message=str(e)
            )
    
    def confirm_payment(
        self,
        payment_id: str,
        payment_method: PaymentMethod,
        payment_method_id: Optional[str] = None
    ) -> PaymentResult:
        """
        Confirma un pago.
        
        Args:
            payment_id: ID del pago a confirmar
            payment_method: Método de pago usado
            payment_method_id: ID del método de pago (para Stripe)
        
        Returns:
            PaymentResult con estado final
        """
        if payment_method == PaymentMethod.STRIPE:
            return self._confirm_stripe_payment(payment_id, payment_method_id)
        elif payment_method == PaymentMethod.PAYPAL:
            return self._confirm_paypal_payment(payment_id)
        else:
            return PaymentResult(
                success=False,
                payment_id=payment_id,
                payment_method=payment_method,
                amount=0.0,
                error_message=f"Método de pago no soportado: {payment_method.value}"
            )
    
    def _confirm_stripe_payment(
        self,
        payment_id: str,
        payment_method_id: Optional[str]
    ) -> PaymentResult:
        """Confirma un pago de Stripe."""
        if not self.stripe_enabled:
            # Modo simulación
            return PaymentResult(
                success=True,
                payment_id=payment_id,
                payment_method=PaymentMethod.STRIPE,
                amount=0.0,
                status="succeeded",
                transaction_id=payment_id
            )
        
        try:
            intent = stripe.PaymentIntent.retrieve(payment_id)
            
            if payment_method_id:
                intent.confirm(payment_method=payment_method_id)
            else:
                intent.confirm()
            
            return PaymentResult(
                success=intent.status == "succeeded",
                payment_id=payment_id,
                payment_method=PaymentMethod.STRIPE,
                amount=intent.amount / 100.0,
                currency=intent.currency.upper(),
                status=intent.status,
                transaction_id=intent.id
            )
        except Exception as e:
            return PaymentResult(
                success=False,
                payment_id=payment_id,
                payment_method=PaymentMethod.STRIPE,
                amount=0.0,
                error_message=str(e)
            )
    
    def _confirm_paypal_payment(self, payment_id: str) -> PaymentResult:
        """Confirma un pago de PayPal."""
        if not self.paypal_enabled:
            # Modo simulación
            return PaymentResult(
                success=True,
                payment_id=payment_id,
                payment_method=PaymentMethod.PAYPAL,
                amount=0.0,
                status="approved",
                transaction_id=payment_id
            )
        
        try:
            payment = PayPalPayment.find(payment_id)
            
            if payment.execute({"payer_id": payment.payer.payer_info.payer_id}):
                return PaymentResult(
                    success=True,
                    payment_id=payment_id,
                    payment_method=PaymentMethod.PAYPAL,
                    amount=float(payment.transactions[0].amount.total),
                    currency=payment.transactions[0].amount.currency,
                    status="approved",
                    transaction_id=payment.id
                )
            else:
                return PaymentResult(
                    success=False,
                    payment_id=payment_id,
                    payment_method=PaymentMethod.PAYPAL,
                    amount=0.0,
                    error_message=str(payment.error)
                )
        except Exception as e:
            return PaymentResult(
                success=False,
                payment_id=payment_id,
                payment_method=PaymentMethod.PAYPAL,
                amount=0.0,
                error_message=str(e)
            )
    
    def get_payment_link(
        self,
        payment_id: str,
        payment_method: PaymentMethod
    ) -> Optional[str]:
        """
        Obtiene un link de pago para compartir con el cliente.
        
        Args:
            payment_id: ID del pago
            payment_method: Método de pago
        
        Returns:
            URL del link de pago o None
        """
        if payment_method == PaymentMethod.STRIPE and self.stripe_enabled:
            try:
                intent = stripe.PaymentIntent.retrieve(payment_id)
                # Crear Checkout Session para link de pago
                session = stripe.checkout.Session.create(
                    payment_intent_data={
                        "metadata": intent.metadata
                    },
                    line_items=[{
                        "price_data": {
                            "currency": intent.currency,
                            "product_data": {
                                "name": "Purchase"
                            },
                            "unit_amount": intent.amount
                        },
                        "quantity": 1
                    }],
                    mode="payment",
                    success_url="https://example.com/success",
                    cancel_url="https://example.com/cancel"
                )
                return session.url
            except Exception as e:
                print(f"Error creando link de pago: {e}")
                return None
        
        return None



