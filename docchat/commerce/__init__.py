"""
Commerce Module - Sales Agent completo con checkout end-to-end
Integra pagos, catálogo de productos, flujo conversacional y cross-selling
"""

from .payment_processor import PaymentProcessor, PaymentResult, PaymentMethod
from .product_catalog import ProductCatalog, Product, ProductSearchResult
from .conversational_flow import ConversationalFlow, UserIntent, ProactiveQuestion
from .cross_selling import CrossSellingEngine, ProductRecommendation
from .cart_manager import CartManager, Cart, CartItem

__all__ = [
    "PaymentProcessor",
    "PaymentResult",
    "PaymentMethod",
    "ProductCatalog",
    "Product",
    "ProductSearchResult",
    "ConversationalFlow",
    "UserIntent",
    "ProactiveQuestion",
    "CrossSellingEngine",
    "ProductRecommendation",
    "CartManager",
    "Cart",
    "CartItem"
]



