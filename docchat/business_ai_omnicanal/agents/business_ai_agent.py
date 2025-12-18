from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any

from langchain_core.language_models import BaseLanguageModel
from langchain_core.messages import SystemMessage, HumanMessage

from ..state.customer_session import CustomerSessionManager, CustomerSessionState
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
    ) -> Dict[str, Any]:
        """Procesa un mensaje del usuario y devuelve respuesta estructurada.

        La lógica de negocio se divide en:
        - Actualizar estado de sesión y sentimiento
        - Pedir al LLM que decida si la intención es: comprar, soporte, estado de pedido, devolución, etc.
        - Llamar a las tools correspondientes
        - Generar una respuesta final amigable para el usuario
        """
        session.add_message("user", user_message)

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

        # Paso 1: pedir al LLM que entienda intención de alto nivel
        system_prompt = (
            f"Eres el agente oficial de {self.config.brand_name}. "
            "Sabes vender productos, responder dudas, dar estado de pedidos y gestionar devoluciones. "
            "Debes decidir QUÉ acción tomar (ventas vs soporte) y QUÉ tools usar (catálogo, carrito, pago, pedidos, tickets)."
        )
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

        # Búsqueda de productos
        if intent_data.get("needs_product_search"):
            query = intent_data.get("product_query") or user_message
            products = self.catalog_tool.search_products(query=query, limit=5)
            tool_results["products"] = [p.__dict__ for p in products]

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

        # Generar respuesta final amigable
        summary_prompt = (
            "Genera una respuesta amable y clara en español para el cliente, explicando lo que hiciste "
            "(por ejemplo: productos sugeridos, carrito actualizado, link de pago, número de pedido, ticket creado).\n"
            f"Contexto de tools: {json.dumps(tool_results)[:2000]}\n"
            f"Mensaje original del cliente: {user_message[:500]}\n"
        )

        final_resp = self.llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=summary_prompt),
        ])
        final_text = getattr(final_resp, "content", str(final_resp))

        session.add_message("assistant", final_text)

        return {
            "text": final_text,
            "intent": intent,
            "tools": tool_results,
            "sentiment": session.sentiment.value,
            "frustration_score": session.frustration_score,
            "needs_handoff": session.needs_handoff,
            "session": session,
        }

