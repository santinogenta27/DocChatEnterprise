from __future__ import annotations

from typing import Dict, Any

from ...commerce.payment_processor import PaymentProcessor, PaymentResult, PaymentMethod
from ...commerce.cart_manager import Cart


class PaymentTool:
    """Wrapper de pago que recibe un Cart y procesa el cobro."""

    def __init__(self, payment_processor: PaymentProcessor) -> None:
        self.payment_processor = payment_processor

    def create_payment_for_cart(
        self,
        session_id: str,
        cart: Cart,
        payment_method: str = "stripe",
        currency: str = "usd",
        metadata: Dict[str, Any] | None = None,
    ) -> PaymentResult:
        if not cart.items:
            raise ValueError("El carrito está vacío")

        amount = cart.total
        method = PaymentMethod(payment_method)

        intent = self.payment_processor.create_payment_intent(
            session_id=session_id,
            amount=amount,
            currency=currency,
            payment_method=method,
            metadata=metadata or {"cart_id": cart.cart_id},
        )

        return intent



