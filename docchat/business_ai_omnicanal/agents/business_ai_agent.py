from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, Optional

from langchain_core.language_models import BaseLanguageModel
from langchain_core.messages import SystemMessage, HumanMessage

from ..state.customer_session import CustomerSessionManager, CustomerSessionState, SentimentLabel
from ..sentiment.sentiment_analyzer import SentimentAnalyzer
from ..tools.catalog_tool import CatalogTool
from ..tools.cart_tool import CartTool
from ..tools.payment_tool import PaymentTool
from ..tools.order_tool import OrderTool
from ..tools.support_tool import SupportTool


@dataclass
class BusinessAIConfig:
    brand_name: str = "Your Brand"
    language: str = "es"


class BusinessAIAgent:
    """Agente orquestador de Business AI Omnicanal.

    Combina ventas (catálogo, carrito, pagos) + soporte (pedidos, tickets)
    en un solo flujo conversacional.
    """

    def __init__(
        self,
        llm: BaseLanguageModel,
        session_manager: CustomerSessionManager,
        sentiment_analyzer: SentimentAnalyzer,
        catalog_tool: CatalogTool,
        cart_tool: CartTool,
        payment_tool: PaymentTool,
        order_tool: OrderTool,
        support_tool: SupportTool,
        config: BusinessAIConfig | None = None,
    ) -> None:
        self.llm = llm
        self.session_manager = session_manager
        self.sentiment_analyzer = sentiment_analyzer
        self.catalog_tool = catalog_tool
        self.cart_tool = cart_tool
        self.payment_tool = payment_tool
        self.order_tool = order_tool
        self.support_tool = support_tool
        self.config = config or BusinessAIConfig()

    def handle_message(
        self,
        session: CustomerSessionState,
        user_message: str,
        image_data: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Procesa un mensaje del usuario y devuelve respuesta estructurada.

        La lógica de negocio se divide en:
        - Actualizar estado de sesión y sentimiento
        - Procesar imágenes si vienen (Mix-ECom approach)
        - Pedir al LLM que decida si la intención es: comprar, soporte, estado de pedido, devolución, etc.
        - Llamar a las tools correspondientes
        - Generar una respuesta final amigable para el usuario
        
        Args:
            session: Estado de sesión del cliente
            user_message: Mensaje de texto del usuario
            image_data: Datos de imagen en base64 (opcional, para procesamiento con visión)
        """
        session.add_message("user", user_message)
        
        # Guardar mensaje del usuario en PostgreSQL si está habilitado
        if hasattr(self.session_manager, 'save_message'):
            try:
                self.session_manager.save_message(
                    session_id=session.session_id,
                    role="user",
                    content=user_message,
                    metadata={"image_analysis": image_analysis is not None}
                )
            except:
                pass  # Si falla, continuar sin guardar
        
        # Procesar imagen si viene (Mix-ECom: procesamiento de imágenes para after-sales)
        image_analysis = None
        if image_data or "[Image]" in user_message:
            # Extraer imagen de mensaje si viene en formato [Image] base64
            if "[Image]" in user_message:
                try:
                    image_base64 = user_message.split("[Image]")[1].strip()
                    image_analysis = self._analyze_image(image_base64)
                except:
                    pass
            
            # Si viene como parámetro separado
            if image_data:
                image_analysis = self._analyze_image(image_data)

        # Analizar sentimiento / frustración
        sentiment_result = self.sentiment_analyzer.analyze(user_message, session)
        self.sentiment_analyzer.update_session_sentiment(session, sentiment_result)

        # Si ya necesita handoff humano, enfocarnos en eso
        if session.needs_handoff:
            ticket = self.support_tool.create_ticket(
                session_id=session.session_id,
                subject="Escalamiento automático por frustración",
                description=f"Conversación requiere humano. Último mensaje: {user_message[:500]}",
                priority="high",
            )
            session.open_tickets.append(ticket)
            return {
                "text": "Voy a pasarte con una persona de nuestro equipo para ayudarte mejor.",
                "handoff": True,
                "ticket": ticket,
                "session": session,
            }

        # Paso 1: Construir perfil contextual del usuario (CSALES approach)
        user_profile_context = self._build_user_profile_context(session, user_message)
        
        # Paso 2: pedir al LLM que entienda intención de alto nivel (con perfil contextual)
        system_prompt = (
            f"Eres el agente oficial de {self.config.brand_name}. "
            "Sabes vender productos, responder dudas, dar estado de pedidos y gestionar devoluciones. "
            "Debes decidir QUÉ acción tomar (ventas vs soporte) y QUÉ tools usar (catálogo, carrito, pago, pedidos, tickets).\n\n"
            f"**Perfil del Cliente:**\n{user_profile_context}\n\n"
            "**Instrucciones Especiales (basadas en Mix-ECom, CSALES, Retail-GPT, MegaChat):**\n"
            "- Si el usuario pregunta por un producto, NO solo muestres ese producto. Sugiere complementos (cross-selling).\n"
            "- Si el usuario muestra interés pero duda, usa persuasión estratégica adaptada a su perfil.\n"
            "- Si el usuario envía una imagen, analízala para entender su necesidad (producto, problema, reclamo).\n"
            "- Maneja diálogos mixtos: puedes responder preguntas, recomendar, vender y hacer chit-chat en la misma conversación.\n"
            "- Personaliza tu tono según el perfil del usuario (más formal para B2B, más entusiasta para lifestyle).\n"
            "- Si hay análisis de imagen, úsalo para verificar reclamos o identificar productos."
        )
        
        # Agregar análisis de imagen al prompt si existe
        if image_analysis:
            analysis_prompt += f"\n**Análisis de Imagen:** {json.dumps(image_analysis)}\n"
        analysis_prompt = (
            "Analiza el mensaje del usuario y responde en JSON con esta estructura mínima:\n"
            "{\n"
            "  'intent': 'sales' | 'support' | 'order_status' | 'refund' | 'small_talk',\n"
            "  'needs_product_search': true/false,\n"
            "  'product_query': 'texto o vacío',\n"
            "  'needs_cart_update': true/false,\n"
            "  'cart_action': 'add' | 'remove' | 'none',\n"
            "  'product_id': 'opcional',\n"
            "  'quantity': numero,\n"
            "  'needs_payment': true/false,\n"
            "  'order_id': 'opcional si pregunta por un pedido',\n"
            "  'needs_handoff': true/false\n"
            "}\n"
            f"Mensaje: {user_message[:1500]}\n"
        )

        llm_resp = self.llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=analysis_prompt),
        ])
        content = getattr(llm_resp, "content", str(llm_resp))

        # Parsing muy defensivo del JSON
        import json, re

        match = re.search(r"\{[\s\S]*\}", content)
        if match:
            try:
                intent_data = json.loads(match.group().replace("'", '"'))
            except Exception:
                intent_data = {"intent": "small_talk"}
        else:
            intent_data = {"intent": "small_talk"}

        intent = intent_data.get("intent", "small_talk")

        # Ejecutar acciones de alto nivel según intención
        tool_results: Dict[str, Any] = {}

        # Búsqueda de productos (con cross-selling inteligente)
        if intent_data.get("needs_product_search"):
            query = intent_data.get("product_query") or user_message
            products = self.catalog_tool.search_products(query=query, limit=5)
            tool_results["products"] = [p.__dict__ for p in products]
            
            # Cross-selling: Si hay productos encontrados, buscar complementos
            if products and len(products) > 0:
                primary_product = products[0]
                # Buscar productos relacionados/complementarios
                try:
                    related_products = self.catalog_tool.suggest_alternatives(
                        product_id=primary_product.product_id if hasattr(primary_product, 'product_id') else str(primary_product),
                        limit=3
                    )
                    if related_products:
                        tool_results["cross_sell_products"] = [p.__dict__ for p in related_products]
                except:
                    pass  # Si falla, continuar sin cross-selling

        # Actualización de carrito
        session_id = session.session_id
        if intent_data.get("needs_cart_update"):
            cart_action = intent_data.get("cart_action", "none")
            product_id = intent_data.get("product_id")
            quantity = int(intent_data.get("quantity") or 1)
            if product_id:
                if cart_action == "add":
                    cart = self.cart_tool.add_item(session_id, product_id, quantity)
                elif cart_action == "remove":
                    cart = self.cart_tool.remove_item(session_id, product_id)
                else:
                    cart = self.cart_tool.get_cart(session_id)
            else:
                cart = self.cart_tool.get_cart(session_id)
            tool_results["cart"] = cart.to_dict() if hasattr(cart, "to_dict") else cart.__dict__
            session.cart = tool_results["cart"]

        # Pago
        if intent_data.get("needs_payment"):
            cart = self.cart_tool.get_cart(session_id)
            payment_result = self.payment_tool.create_payment_for_cart(session_id=session_id, cart=cart)
            tool_results["payment"] = payment_result.__dict__

            # Crear orden
            order = self.order_tool.create_order(
                session_id=session_id,
                cart_snapshot=tool_results.get("cart") or (cart.to_dict() if hasattr(cart, "to_dict") else cart.__dict__),
                payment_info=tool_results["payment"],
            )
            tool_results["order"] = order
            session.recent_orders.append(order)

        # Estado de pedido
        if intent == "order_status" and intent_data.get("order_id"):
            order = self.order_tool.get_order_status(intent_data["order_id"])
            tool_results["order_status"] = order

        # Devoluciones / soporte
        if intent in ("support", "refund"):
            ticket = self.support_tool.create_ticket(
                session_id=session_id,
                subject=f"Soporte: {intent}",
                description=user_message[:1000],
                priority="normal" if intent == "support" else "high",
            )
            session.open_tickets.append(ticket)
            tool_results["ticket"] = ticket

        # Generar respuesta final amigable (con personalización y persuasión)
        summary_prompt = (
            "Genera una respuesta amable, clara y personalizada en español para el cliente.\n\n"
            "**Contexto de herramientas ejecutadas:**\n"
            f"{json.dumps(tool_results, default=str)[:2000]}\n\n"
            f"**Mensaje original del cliente:** {user_message[:500]}\n\n"
            f"**Perfil del cliente:** {user_profile_context}\n\n"
            "**Instrucciones de respuesta (basadas en CSALES y MegaChat):**\n"
            "- Si hay productos sugeridos, explica POR QUÉ son buenos para este cliente específico (personalización).\n"
            "- Si hay productos de cross-selling, preséntalos de forma persuasiva pero no agresiva.\n"
            "- Si el cliente muestra dudas sobre precio, usa persuasión estratégica (valor, calidad, beneficios).\n"
            "- Adapta el tono al perfil del cliente (formal vs casual).\n"
            "- Si hay carrito, muestra resumen y anima a completar la compra.\n"
            "- Si hay productos, incluye detalles relevantes (precio, características, disponibilidad).\n"
            "- Sé proactivo: después de resolver la pregunta actual, pregunta si necesita algo más.\n"
        )

        final_resp = self.llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=summary_prompt),
        ])
        final_text = getattr(final_resp, "content", str(final_resp))

        session.add_message("assistant", final_text)
        
        # Guardar mensaje en PostgreSQL si está habilitado (para memoria de largo plazo)
        if hasattr(self.session_manager, 'save_message'):
            try:
                self.session_manager.save_message(
                    session_id=session.session_id,
                    role="assistant",
                    content=final_text,
                    metadata={
                        "intent": intent,
                        "sentiment": session.sentiment.value,
                        "frustration_score": session.frustration_score
                    }
                )
            except:
                pass  # Si falla, continuar sin guardar
        
        # Guardar compra si se completó una orden
        if tool_results.get("order") and hasattr(self.session_manager, 'save_purchase'):
            try:
                order = tool_results["order"]
                products = tool_results.get("cart", {}).get("items", []) if isinstance(tool_results.get("cart"), dict) else []
                total = sum(item.get("price", 0) * item.get("quantity", 1) for item in products if isinstance(item, dict))
                
                self.session_manager.save_purchase(
                    session_id=session.session_id,
                    user_id=session.profile.user_id if session.profile else "unknown",
                    order_id=str(order.get("order_id", "")),
                    products=products,
                    total_amount=float(total)
                )
            except:
                pass  # Si falla, continuar sin guardar

        # Incluir información del carrito en la respuesta (para el widget)
        response_data = {
            "text": final_text,
            "intent": intent,
            "tools": tool_results,
            "sentiment": session.sentiment.value,
            "frustration_score": session.frustration_score,
            "needs_handoff": session.needs_handoff,
            "session": session,
        }
        
        # Agregar carrito si existe (para actualizar badge en widget)
        if session.cart:
            response_data["cart"] = session.cart.get("items", []) if isinstance(session.cart, dict) else []
        
        # Agregar perfil de usuario si se ha inferido
        if hasattr(session, 'inferred_profile'):
            response_data["user_profile"] = session.inferred_profile
        
        return response_data
    
    def _build_user_profile_context(self, session: CustomerSessionState, user_message: str) -> str:
        """Construye contexto del perfil de usuario (CSALES approach).
        
        Basado en:
        - Historial de conversación
        - Productos vistos/interesados
        - Carrito actual
        - Sentimiento
        - Comportamiento (activo/pasivo)
        - Historial de largo plazo (PostgreSQL) si está disponible
        """
        context_parts = []
        
        # Información básica
        if session.profile:
            if session.profile.display_name:
                context_parts.append(f"Nombre: {session.profile.display_name}")
            if session.profile.language:
                context_parts.append(f"Idioma: {session.profile.language}")
        
        # Historial de largo plazo (PostgreSQL) - Memoria de meses
        if hasattr(self.session_manager, 'get_user_history'):
            try:
                user_history = self.session_manager.get_user_history(
                    user_id=session.profile.user_id if session.profile else "unknown",
                    days=180  # Últimos 6 meses
                )
                
                if user_history.get("total_purchases", 0) > 0:
                    context_parts.append(f"Cliente recurrente: {user_history['total_purchases']} compra(s) en últimos 6 meses")
                    context_parts.append(f"Total gastado: ${user_history.get('total_spent', 0):.2f}")
                    
                    if user_history.get("last_purchase_date"):
                        last_purchase = user_history["last_purchase_date"]
                        if isinstance(last_purchase, str):
                            from datetime import datetime
                            try:
                                last_purchase = datetime.fromisoformat(last_purchase.replace('Z', '+00:00'))
                            except:
                                pass
                        if isinstance(last_purchase, datetime):
                            days_ago = (datetime.utcnow() - last_purchase.replace(tzinfo=None)).days
                            context_parts.append(f"Última compra: hace {days_ago} días")
                
                # Productos comprados anteriormente (para cross-selling)
                if user_history.get("purchases"):
                    previous_products = []
                    for purchase in user_history["purchases"][:5]:  # Últimas 5 compras
                        products = purchase.get("products", [])
                        if isinstance(products, str):
                            import json
                            products = json.loads(products)
                        if isinstance(products, list):
                            for p in products:
                                if isinstance(p, dict):
                                    product_name = p.get("name") or p.get("product_name")
                                    if product_name:
                                        previous_products.append(product_name)
                    
                    if previous_products:
                        context_parts.append(f"Productos comprados anteriormente: {', '.join(set(previous_products)[:3])}")
            except Exception as e:
                # Si falla, continuar sin historial de largo plazo
                pass
        
        # Historial de conversación (sesión actual)
        if session.last_messages:
            recent_count = len(session.last_messages)
            context_parts.append(f"Mensajes en esta sesión: {recent_count}")
            
            # Detectar si es usuario activo o pasivo (CSALES)
            avg_message_length = sum(len(msg.get('content', '')) for msg in session.last_messages) / max(recent_count, 1)
            if avg_message_length > 50:
                context_parts.append("Tipo de usuario: Activo (proporciona detalles)")
            elif avg_message_length < 20:
                context_parts.append("Tipo de usuario: Pasivo (respuestas cortas)")
        
        # Carrito
        if session.cart:
            if isinstance(session.cart, dict):
                items = session.cart.get("items", [])
            else:
                items = getattr(session.cart, "items", [])
            if items:
                context_parts.append(f"Carrito: {len(items)} producto(s)")
                total = sum(item.get('price', 0) * item.get('quantity', 1) for item in items if isinstance(item, dict))
                if total > 0:
                    context_parts.append(f"Presupuesto estimado: ${total:.2f}")
        
        # Sentimiento
        if session.sentiment != SentimentLabel.NEUTRAL:
            context_parts.append(f"Sentimiento: {session.sentiment.value}")
        
        # Pedidos recientes (sesión actual)
        if session.recent_orders:
            context_parts.append(f"Pedidos en esta sesión: {len(session.recent_orders)}")
        
        return " | ".join(context_parts) if context_parts else "Cliente nuevo"
    
    def _analyze_image(self, image_base64: str) -> Optional[Dict[str, Any]]:
        """Analiza imagen usando visión (Mix-ECom approach para after-sales).
        
        Usa GPT-4 Vision para:
        - Verificar reclamos de calidad
        - Identificar productos en imágenes
        - Detectar daños o problemas
        """
        try:
            # Si el LLM soporta visión, usarlo
            if hasattr(self.llm, 'with_structured_output') or 'gpt-4' in str(self.llm).lower():
                from langchain_core.messages import HumanMessage
                from langchain_core.messages.content import ImageContent
                
                # Crear mensaje con imagen
                vision_prompt = (
                    "Analiza esta imagen y responde en JSON:\n"
                    "{\n"
                    "  'contains_product': true/false,\n"
                    "  'product_description': 'descripción del producto si es visible',\n"
                    "  'has_issue': true/false,\n"
                    "  'issue_description': 'descripción del problema si hay',\n"
                    "  'can_verify_claim': true/false\n"
                    "}\n"
                )
                
                # Intentar usar visión si está disponible
                try:
                    # Para GPT-4o con visión
                    response = self.llm.invoke([
                        SystemMessage(content="Eres un analizador de imágenes para e-commerce. Analiza productos y problemas."),
                        HumanMessage(content=[
                            {"type": "text", "text": vision_prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
                        ])
                    ])
                    
                    import json, re
                    content = getattr(response, "content", str(response))
                    match = re.search(r"\{[\s\S]*\}", content)
                    if match:
                        return json.loads(match.group().replace("'", '"'))
                except:
                    # Si falla, retornar análisis básico
                    return {
                        "contains_product": True,
                        "can_verify_claim": True,
                        "note": "Imagen recibida, análisis visual disponible"
                    }
        except Exception as e:
            # Si falla completamente, retornar None
            return None



