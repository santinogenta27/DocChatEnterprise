"""
Mapeo de Intención → Tipo de Link para STAR AGENT.

Implementa las 3 capas obligatorias:
1. Detectar INTENCIÓN en la conversación
2. Mapear INTENCIÓN → TIPO DE LINK
3. Gate de CUÁNDO enviar el link (se aplica después)
"""

from __future__ import annotations
from typing import Optional, Dict, Any
from enum import Enum


class UserIntent(str, Enum):
    """Intenciones del usuario para mapeo a links."""
    BROWSE_PRODUCTS = "browse_products"  # "Quiero ver zapatillas"
    PRICE_INQUIRY = "price_inquiry"  # "¿Cuánto cuestan?"
    PURCHASE_INTENT = "purchase_intent"  # "Quiero comprar"
    GO_TO_CHECKOUT = "go_to_checkout"  # "Quiero pagar ahora"
    PAYMENT_INFO = "payment_info"  # "¿Cómo pago?" / "¿Qué métodos de pago aceptan?"
    SHIPPING_INFO = "shipping_info"  # "¿Hacen envíos?"
    RETURNS_INFO = "returns_info"  # "¿Puedo devolver?"
    SUPPORT = "support"  # "Necesito ayuda"
    FAQ = "faq"  # Preguntas frecuentes
    CONTACT = "contact"  # "Quiero contactar"
    GENERAL = "general"  # Sin intención específica


class LinkType(str, Enum):
    """Tipos de links disponibles."""
    CATALOG = "catalog"  # Catálogo de productos
    PRODUCT = "product"  # Producto específico (generado dinámicamente)
    CHECKOUT = "checkout"  # Checkout/carrito
    PAYMENT_METHODS = "payment_methods"  # Métodos de pago
    SHIPPING = "shipping"  # Info de envíos
    RETURNS = "returns"  # Política de devoluciones
    SUPPORT = "support"  # Soporte/ayuda
    FAQ = "faq"  # Preguntas frecuentes
    CONTACT = "contact"  # Contacto
    STORE = "store"  # Tienda principal
    PRIVACY_POLICY = "privacy_policy"  # Política de privacidad
    TERMS = "terms"  # Términos y condiciones


# Mapeo INTENCIÓN → TIPO DE LINK (CAPA 2)
INTENT_TO_LINK_TYPE: Dict[UserIntent, LinkType] = {
    UserIntent.BROWSE_PRODUCTS: LinkType.CATALOG,
    UserIntent.PRICE_INQUIRY: LinkType.PRODUCT,  # Se generará dinámicamente si hay producto específico
    UserIntent.PURCHASE_INTENT: LinkType.PRODUCT,  # Se generará dinámicamente si hay producto específico
    UserIntent.GO_TO_CHECKOUT: LinkType.CHECKOUT,
    UserIntent.PAYMENT_INFO: LinkType.PAYMENT_METHODS,
    UserIntent.SHIPPING_INFO: LinkType.SHIPPING,
    UserIntent.RETURNS_INFO: LinkType.RETURNS,
    UserIntent.SUPPORT: LinkType.SUPPORT,
    UserIntent.FAQ: LinkType.FAQ,
    UserIntent.CONTACT: LinkType.CONTACT,
    UserIntent.GENERAL: LinkType.STORE,  # Link genérico a tienda
}


class IntentLinkMapper:
    """
    Mapea intenciones del usuario a tipos de links.
    
    Implementa las 3 capas:
    1. Detecta intención del mensaje
    2. Mapea intención → tipo de link
    3. Gate de cuándo enviar (se aplica después)
    """
    
    def detect_intent(self, message: str, sales_stage: Optional[str] = None) -> UserIntent:
        """
        Detecta la intención del usuario (CAPA 1).
        
        Args:
            message: Mensaje del usuario
            sales_stage: Etapa de venta (opcional, para contexto adicional)
            
        Returns:
            UserIntent detectada
        """
        msg_lower = message.lower()
        
        # GO_TO_CHECKOUT (más específico primero)
        if any(phrase in msg_lower for phrase in [
            "quiero pagar", "pagar ahora", "ir a pagar", "proceder al pago",
            "completar compra", "finalizar compra", "checkout", "carrito"
        ]):
            return UserIntent.GO_TO_CHECKOUT
        
        # PURCHASE_INTENT
        if any(phrase in msg_lower for phrase in [
            "quiero comprar", "me interesa comprar", "dame", "quiero ese", 
            "agregar al carrito", "añadir al carrito", "agregar carrito"
        ]):
            return UserIntent.PURCHASE_INTENT
        
        # PRICE_INQUIRY
        if any(phrase in msg_lower for phrase in [
            "cuánto cuesta", "cuánto vale", "precio de", "precio del",
            "qué precio", "costo", "valor"
        ]):
            return UserIntent.PRICE_INQUIRY
        
        # PAYMENT_INFO
        if any(phrase in msg_lower for phrase in [
            "métodos de pago", "formas de pago", "cómo pago", "con qué puedo pagar",
            "aceptan tarjeta", "aceptan paypal", "aceptan transferencia"
        ]):
            return UserIntent.PAYMENT_INFO
        
        # SHIPPING_INFO
        if any(phrase in msg_lower for phrase in [
            "hacen envíos", "envían", "envío", "entrega", "cuánto tarda",
            "tiempo de entrega", "envío gratis", "costo de envío"
        ]):
            return UserIntent.SHIPPING_INFO
        
        # RETURNS_INFO
        if any(phrase in msg_lower for phrase in [
            "puedo devolver", "política de devoluciones", "devoluciones",
            "puedo cambiar", "garantía de devolución"
        ]):
            return UserIntent.RETURNS_INFO
        
        # BROWSE_PRODUCTS
        if any(phrase in msg_lower for phrase in [
            "quiero ver", "muéstrame", "muéstrenme", "qué tienen",
            "qué productos", "catálogo", "productos", "ver zapatillas",
            "ver ropa", "ver accesorios", "listado"
        ]):
            return UserIntent.BROWSE_PRODUCTS
        
        # SUPPORT
        if any(phrase in msg_lower for phrase in [
            "necesito ayuda", "ayuda", "soporte", "problema", "tengo un problema",
            "no funciona", "error"
        ]):
            return UserIntent.SUPPORT
        
        # FAQ
        if any(phrase in msg_lower for phrase in [
            "preguntas frecuentes", "faq", "dudas comunes"
        ]):
            return UserIntent.FAQ
        
        # CONTACT
        if any(phrase in msg_lower for phrase in [
            "contactar", "contacto", "hablar con", "comunicarme", "teléfono",
            "email", "correo"
        ]):
            return UserIntent.CONTACT
        
        # Por defecto, si está en READY/CLOSING, puede ser purchase_intent
        if sales_stage in ["ready", "closing"]:
            return UserIntent.PURCHASE_INTENT
        
        # GENERAL (sin intención específica)
        return UserIntent.GENERAL
    
    def get_link_type_for_intent(self, intent: UserIntent) -> Optional[LinkType]:
        """
        Mapea intención → tipo de link (CAPA 2).
        
        Args:
            intent: Intención detectada
            
        Returns:
            LinkType correspondiente o None
        """
        return INTENT_TO_LINK_TYPE.get(intent)
    
    def should_include_link(self, intent: UserIntent, sales_stage: Optional[str] = None) -> bool:
        """
        Gate de CUÁNDO enviar el link (CAPA 3).
        
        Aplica reglas adicionales sobre cuándo es apropiado enviar el link.
        
        Args:
            intent: Intención detectada
            sales_stage: Etapa de venta
            
        Returns:
            True si se debe incluir el link, False si no
        """
        # Si es GENERAL sin intención clara, NO enviar link
        if intent == UserIntent.GENERAL:
            return False
        
        # Si es BROWSE_PRODUCTS en etapa INTEREST, SÍ enviar link al catálogo
        if intent == UserIntent.BROWSE_PRODUCTS:
            return True  # Siempre enviar link al catálogo cuando quiere ver productos
        
        # Si está en READY/CLOSING, SÍ enviar links relevantes
        if sales_stage in ["ready", "closing"]:
            return True
        
        # Para otras intenciones, enviar si son específicas
        if intent in [
            UserIntent.GO_TO_CHECKOUT,
            UserIntent.PAYMENT_INFO,
            UserIntent.SHIPPING_INFO,
            UserIntent.RETURNS_INFO,
            UserIntent.SUPPORT,
            UserIntent.FAQ,
            UserIntent.CONTACT,
        ]:
            return True
        
        # Para PRICE_INQUIRY y PURCHASE_INTENT, depende de si hay producto específico
        # Esto se maneja en otro lugar con _should_include_product_links()
        return True

