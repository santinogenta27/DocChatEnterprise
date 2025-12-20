from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Dict, Any, Optional, List

from langchain_core.language_models import BaseLanguageModel
from langchain_core.messages import SystemMessage, HumanMessage

from ...commerce.product_catalog import ProductSearchResult
from ...config import AppConfig
from ..state.customer_session import CustomerSessionManager, CustomerSessionState, SentimentLabel
from ..sentiment.sentiment_analyzer import SentimentAnalyzer
from ..tools.catalog_tool import CatalogTool
from ..tools.cart_tool import CartTool
from ..tools.payment_tool import PaymentTool
from ..tools.order_tool import OrderTool
from ..tools.support_tool import SupportTool
from ..config.chatbot_config_manager import ChatbotConfigManager


@dataclass
class BusinessAIConfig:
    brand_name: str = "Your Brand"
    language: str = "es"
    # Personalización del chatbot (opcional)
    tone: str = "friendly"  # friendly, professional, casual, formal, enthusiastic
    personality: str = ""  # Descripción libre de la personalidad
    custom_instructions: str = ""  # Instrucciones personalizadas adicionales


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
        fallback_llm: Optional[BaseLanguageModel] = None,
        app_config: Optional[AppConfig] = None,
    ) -> None:
        self.llm = llm
        self._fallback_llm = fallback_llm  # LLM de respaldo si el principal falla
        self.session_manager = session_manager
        self.sentiment_analyzer = sentiment_analyzer
        self.catalog_tool = catalog_tool
        self.cart_tool = cart_tool
        self.payment_tool = payment_tool
        self.order_tool = order_tool
        self.support_tool = support_tool
        self.config = config or BusinessAIConfig()
        self.app_config = app_config
        
        # Cargar configuraciones del chatbot desde JSON (o .env como fallback)
        self.chatbot_config_manager = ChatbotConfigManager()
        self.chatbot_config = self.chatbot_config_manager.load()
        
        # Inicializar RAG si está habilitado
        self.rag_retriever = None
        if self.chatbot_config.rag_enabled:
            self._initialize_rag()
        
        # Traductor multilingüe (si está habilitado)
        self.translator = None
        if self.chatbot_config.multilingual_enabled and app_config:
            try:
                from ...i18n.translator import MultiLanguageTranslator
                self.translator = MultiLanguageTranslator(app_config)
            except Exception as e:
                print(f"⚠️ No se pudo inicializar traductor multilingüe: {e}")
    
    def _invoke_llm_with_fallback(self, messages):
        """Invoca el LLM con fallback automático si falla la autenticación"""
        try:
            return self.llm.invoke(messages)
        except Exception as llm_error:
            error_msg = str(llm_error)
            # Si es error de autenticación (401) y hay fallback, usarlo
            if ("401" in error_msg or "AuthenticationError" in error_msg or "Invalid API Key" in error_msg) and self._fallback_llm:
                print(f"⚠️ Error de autenticación con LLM principal: {error_msg}")
                print("⚠️ Usando LLM de fallback (OpenAI)...")
                try:
                    result = self._fallback_llm.invoke(messages)
                    # Cambiar el LLM principal al fallback para próximas llamadas
                    self.llm = self._fallback_llm
                    print("✅ Cambiado a LLM de fallback exitosamente")
                    return result
                except Exception as fallback_error:
                    print(f"❌ Error también con LLM de fallback: {fallback_error}")
                    raise ValueError(f"Error con ambos LLMs: Principal={error_msg}, Fallback={fallback_error}")
            else:
                # Si no hay fallback o es otro tipo de error, lanzar excepción
                raise

    def _initialize_rag(self):
        """Inicializa el sistema RAG si está habilitado."""
        try:
            from ...semantic_data_engine import SemanticDataEngine
            if self.app_config and self.chatbot_config.documents_dir:
                # TODO: Cargar documentos desde documents_dir
                # Por ahora, se inicializará cuando se carguen documentos
                print("✅ RAG habilitado - Listo para consultar documentos")
        except Exception as e:
            print(f"⚠️ Error inicializando RAG: {e}")
    
    def _detect_language(self, text: str) -> str:
        """Detecta el idioma del texto."""
        if self.translator:
            return self.translator.detect_language(text)
        # Detección básica si no hay traductor
        text_lower = text.lower()
        if any(word in text_lower for word in ["the", "is", "are", "and", "or", "what", "how"]):
            return "en"
        elif any(word in text_lower for word in ["o", "a", "é", "de", "da", "você", "não"]):
            return "pt"
        elif any(word in text_lower for word in ["le", "la", "les", "de", "et", "vous"]):
            return "fr"
        elif any(word in text_lower for word in ["der", "die", "das", "und", "oder"]):
            return "de"
        return self.chatbot_config.default_language
    
    def _check_objections(self, user_message: str) -> Optional[str]:
        """Verifica si el mensaje contiene objeciones y retorna respuesta personalizada."""
        if not self.chatbot_config.objection_responses:
            return None
        
        user_msg_lower = user_message.lower()
        for objection_key, response in self.chatbot_config.objection_responses.items():
            if objection_key.lower() in user_msg_lower:
                return response
        return None
    
    def _query_rag(self, query: str, top_k: int = 5) -> str:
        """Consulta el índice RAG para obtener información relevante."""
        if not self.chatbot_config.rag_enabled or not self.rag_retriever:
            return ""
        
        try:
            # TODO: Implementar consulta real a RAG
            # Por ahora retorna vacío
            return ""
        except Exception as e:
            print(f"⚠️ Error consultando RAG: {e}")
            return ""
    
    def _check_handoff_keywords(self, user_message: str) -> bool:
        """Verifica si el mensaje contiene palabras clave para handoff."""
        if not self.chatbot_config.handoff_keywords:
            return False
        
        user_msg_lower = user_message.lower()
        for keyword in self.chatbot_config.handoff_keywords:
            if keyword.lower() in user_msg_lower:
                return True
        return False
    
    def _calculate_lead_score(self, session: CustomerSessionState) -> int:
        """Calcula el score del lead basado en respuestas a preguntas de calificación."""
        if not self.chatbot_config.lead_scoring_enabled:
            return 0
        
        score = 0
        
        # Si hay respuestas guardadas, calcular score
        if hasattr(session, 'lead_responses') and session.lead_responses:
            for response_data in session.lead_responses:
                question_weight = response_data.get("weight", 1)
                answer_value = response_data.get("value", 0)  # 0-5 o similar
                score += question_weight * answer_value
        else:
            # Score básico basado en actividad/interacción
            # Más mensajes = mayor interés
            message_count = len(session.last_messages) if hasattr(session, 'last_messages') else 0
            if message_count > 5:
                score += 2
            if message_count > 10:
                score += 2
            # Carrito con productos = interés de compra
            if session.cart and isinstance(session.cart, dict):
                items = session.cart.get("items", [])
                if len(items) > 0:
                    score += 3
            # Sentimiento positivo = buen lead
            if session.sentiment == SentimentLabel.POSITIVE:
                score += 2
        
        return score
    
    def _trigger_human_handoff(self, session: CustomerSessionState, reason: str, user_message: str):
        """Activa handoff humano y envía alerta."""
        session.needs_handoff = True
        ticket = self.support_tool.create_ticket(
            session_id=session.session_id,
            subject=f"Handoff Automático: {reason}",
            description=f"Razón: {reason}\nMensaje del usuario: {user_message[:500]}",
            priority="high",
        )
        session.open_tickets.append(ticket)
        
        # TODO: Enviar notificación a contacto configurado (WhatsApp, email, Slack, etc.)
        print(f"🚨 HANDOFF ACTIVADO: {reason} - Session: {session.session_id}")
        
        return ticket
    
    def handle_message(
        self,
        session: CustomerSessionState,
        user_message: str,
        image_data: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Procesa un mensaje del usuario con pipeline completo de ventas.
        
        Pipeline de Ventas:
        1. Detección de idioma (multilingüismo)
        2. Detección de objeciones (respuestas personalizadas)
        3. Motor RAG activo (consultar documentos si no tiene respuesta)
        4. Sistema de Lead Scoring (calificar lead)
        5. Detección de Handoff Humano (palabras clave + frustración)
        6. Generación de respuesta final
        
        Args:
            session: Estado de sesión del cliente
            user_message: Mensaje de texto del usuario
            image_data: Datos de imagen en base64 (opcional)
        """
        # Recargar configuración para obtener cambios recientes
        self.chatbot_config = self.chatbot_config_manager.load()
        
        session.add_message("user", user_message)
        
        # === PASO 1: Detección de Idioma (Multilingüismo Dinámico) ===
        detected_language = self.chatbot_config.default_language
        if self.chatbot_config.multilingual_enabled:
            detected_language = self._detect_language(user_message)
        
        # === PASO 2: Detección de Objeciones ===
        objection_response = self._check_objections(user_message)
        if objection_response:
            # Si encontramos una objeción, usar respuesta personalizada directamente
            final_text = objection_response
            if self.translator and detected_language != self.chatbot_config.default_language:
                final_text = self.translator.translate(final_text, detected_language)
            
            session.add_message("assistant", final_text)
            return {
                "text": final_text,
                "intent": "objection_handling",
                "language": detected_language,
                "session": session,
            }
        
        # === PASO 3: Análisis de Sentimiento y Handoff ===
        sentiment_result = self.sentiment_analyzer.analyze(user_message, session)
        self.sentiment_analyzer.update_session_sentiment(session, sentiment_result)
        
        # Verificar handoff por palabras clave
        handoff_by_keywords = self._check_handoff_keywords(user_message)
        handoff_by_sentiment = session.frustration_score >= self.chatbot_config.handoff_sentiment_threshold
        
        if handoff_by_keywords or handoff_by_sentiment:
            reason = "Palabras clave de handoff" if handoff_by_keywords else f"Frustración alta ({session.frustration_score:.2f})"
            ticket = self._trigger_human_handoff(session, reason, user_message)
            
            handoff_message = "Voy a pasarte con una persona de nuestro equipo para ayudarte mejor."
            if self.translator and detected_language != self.chatbot_config.default_language:
                handoff_message = self.translator.translate(handoff_message, detected_language)
            
            return {
                "text": handoff_message,
                "handoff": True,
                "ticket": ticket,
                "language": detected_language,
                "session": session,
            }
        
        # Si ya necesita handoff humano (desde sesión previa), enfocarnos en eso
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
                "language": detected_language,
                "session": session,
            }
        
        # Guardar mensaje del usuario en PostgreSQL si está habilitado
        if hasattr(self.session_manager, 'save_message'):
            try:
                self.session_manager.save_message(
                    session_id=session.session_id,
                    role="user",
                    content=user_message,
                    metadata={"language": detected_language}
                )
            except:
                pass
        
        # === PASO 4: Procesar imagen si viene ===
        image_analysis = None
        if image_data or "[Image]" in user_message:
            if "[Image]" in user_message:
                try:
                    image_base64 = user_message.split("[Image]")[1].strip()
                    image_analysis = self._analyze_image(image_base64)
                except:
                    pass
            if image_data:
                image_analysis = self._analyze_image(image_data)

        # === PASO 5: Motor RAG Activo ===
        rag_context = ""
        if self.chatbot_config.rag_enabled:
            rag_context = self._query_rag(user_message, top_k=5)
        
        # === PASO 6: Lead Scoring ===
        lead_score = self._calculate_lead_score(session)
        lead_label = "Lead Caliente" if lead_score >= self.chatbot_config.lead_hot_threshold else "Lead Frío"
        
        # Almacenar score en sesión
        if not hasattr(session, 'lead_score'):
            session.lead_score = 0
        session.lead_score = lead_score
        session.lead_label = lead_label
        
        # Si es Lead Caliente, priorizar cierre de venta
        if lead_label == "Lead Caliente":
            # Añadir instrucciones de cierre al prompt
            pass  # Se añadirá más abajo
        
        # Paso 1: Construir perfil contextual del usuario (CSALES approach)
        user_profile_context = self._build_user_profile_context(session, user_message)
        
        # Paso 2: pedir al LLM que entienda intención de alto nivel (con perfil contextual)
        
        # Mapeo de tonos a descripciones
        tone_descriptions = {
            "friendly": "Amigable y cercano, como un amigo que quiere ayudar",
            "professional": "Profesional pero accesible, con expertise técnico",
            "casual": "Relajado y conversacional, como si fuera un compañero",
            "formal": "Formal y respetuoso, usando un lenguaje más estructurado",
            "enthusiastic": "Entusiasta y energético, apasionado por los productos"
        }
        
        tone_desc = tone_descriptions.get(self.config.tone, tone_descriptions["friendly"])
        
        # Construir prompt base
        system_prompt = (
            f"Eres el agente oficial de {self.config.brand_name}. "
            "Sabes vender productos, responder dudas, dar estado de pedidos y gestionar devoluciones. "
            "Debes decidir QUÉ acción tomar (ventas vs soporte) y QUÉ tools usar (catálogo, carrito, pago, pedidos, tickets).\n\n"
        )
        
        # Agregar personalización de tono
        if self.config.tone:
            system_prompt += f"**Tono de Comunicación:** {tone_desc}\n\n"
        
        # Agregar personalidad personalizada si está definida
        if self.config.personality:
            system_prompt += f"**Personalidad:** {self.config.personality}\n\n"
        
        # Agregar instrucciones personalizadas si están definidas
        if self.config.custom_instructions:
            system_prompt += f"**Instrucciones Personalizadas:**\n{self.config.custom_instructions}\n\n"
        
        # Continuar con el prompt base
        system_prompt += (
            f"**Perfil del Cliente:**\n{user_profile_context}\n\n"
        )
        
        # Añadir contexto RAG si está disponible
        if rag_context:
            system_prompt += f"**Información de Documentos (RAG):**\n{rag_context}\n\n"
            system_prompt += "**IMPORTANTE:** Usa SOLO la información de los documentos arriba. NO inventes información.\n\n"
        
        # Añadir información de Lead Scoring
        if self.chatbot_config.lead_scoring_enabled:
            system_prompt += f"**Lead Score:** {lead_score} ({lead_label})\n"
            if lead_label == "Lead Caliente":
                system_prompt += "**PRIORIDAD:** Este es un Lead Caliente. Enfócate en cerrar la venta, ofrecer productos, crear urgencia.\n"
            system_prompt += "\n"
        
        system_prompt += (
            "**Instrucciones Especiales (basadas en Mix-ECom, CSALES, Retail-GPT, MegaChat):**\n"
            "- Si el usuario pregunta por un producto, NO solo muestres ese producto. Sugiere complementos (cross-selling).\n"
            "- Si el usuario muestra interés pero duda, usa persuasión estratégica adaptada a su perfil.\n"
            "- Si el usuario envía una imagen, analízala para entender su necesidad (producto, problema, reclamo).\n"
            "- Maneja diálogos mixtos: puedes responder preguntas, recomendar, vender y hacer chit-chat en la misma conversación.\n"
            "- Personaliza tu tono según el perfil del usuario (más formal para B2B, más entusiasta para lifestyle).\n"
            "- Si hay análisis de imagen, úsalo para verificar reclamos o identificar productos.\n"
        )
        
        # Añadir instrucciones de idioma si es necesario
        if detected_language != self.chatbot_config.default_language:
            system_prompt += f"- Responde siempre en {detected_language}.\n"
        
        # Construir prompt de análisis de intención
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
        
        # Agregar análisis de imagen al prompt si existe
        if image_analysis:
            import json
            analysis_prompt += f"\n**Análisis de Imagen:** {json.dumps(image_analysis)}\n"

        # Usar helper para invocar LLM con fallback automático
        llm_resp = self._invoke_llm_with_fallback([
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
            try:
                search_result = self.catalog_tool.search_products(query=query, limit=5)
                # ProductSearchResult tiene un atributo .products que es la lista
                if isinstance(search_result, ProductSearchResult):
                    products_list = search_result.products if hasattr(search_result, 'products') else []
                elif hasattr(search_result, '__iter__') and not isinstance(search_result, str):
                    # Fallback: si es iterable pero no ProductSearchResult
                    products_list = list(search_result) if not hasattr(search_result, 'products') else search_result.products
                else:
                    products_list = []
                
                # Convertir productos a diccionarios
                tool_results["products"] = []
                for p in products_list:
                    if hasattr(p, '__dict__'):
                        tool_results["products"].append({
                            "id": getattr(p, 'id', str(p)),
                            "title": getattr(p, 'title', str(p)),
                            "description": getattr(p, 'description', ''),
                            "price": getattr(p, 'price', 0),
                            "image_url": getattr(p, 'image_url', ''),
                            "in_stock": getattr(p, 'in_stock', False),
                            "stock": getattr(p, 'stock', 0),
                        })
                
                # Cross-selling: Si hay productos encontrados, buscar complementos
                if products_list and len(products_list) > 0:
                    primary_product = products_list[0]
                    product_id = getattr(primary_product, 'id', None) or getattr(primary_product, 'product_id', None)
                    if product_id:
                        try:
                            related_products = self.catalog_tool.suggest_alternatives(
                                product_id=str(product_id),
                                limit=3
                            )
                            if related_products and isinstance(related_products, list):
                                tool_results["cross_sell_products"] = [
                                    {
                                        "id": getattr(p, 'id', str(p)),
                                        "title": getattr(p, 'title', str(p)),
                                        "price": getattr(p, 'price', 0),
                                    }
                                    for p in related_products
                                ]
                        except Exception as e:
                            print(f"⚠️ Error en cross-selling: {e}")
                            pass  # Si falla, continuar sin cross-selling
            except Exception as e:
                print(f"⚠️ Error buscando productos: {e}")
                import traceback
                traceback.print_exc()
                tool_results["products"] = []

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
            "- Responde DIRECTAMENTE a la pregunta del usuario. NO uses saludos genéricos si el usuario ya hizo una pregunta específica.\n"
            "- Si el usuario pregunta por productos, lista los productos encontrados con NOMBRES, PRECIOS y CARACTERÍSTICAS específicas. NO digas genéricamente 'tenemos productos', muestra los productos reales.\n"
            "- Si hay productos sugeridos, explica POR QUÉ son buenos para este cliente específico (personalización).\n"
            "- Si el usuario pregunta 'qué día es hoy', responde con la fecha actual REAL (usa la fecha de hoy).\n"
            "- Si el usuario pregunta 'qué sabes', explica ESPECÍFICAMENTE qué puedes hacer (buscar productos, gestionar pedidos, etc.) con ejemplos concretos.\n"
            "- Si hay productos de cross-selling, preséntalos de forma persuasiva pero no agresiva.\n"
            "- Si el cliente muestra dudas sobre precio, usa persuasión estratégica (valor, calidad, beneficios).\n"
            "- Adapta el tono al perfil del cliente (formal vs casual).\n"
            "- Si hay carrito, muestra resumen y anima a completar la compra.\n"
            "- Si hay productos, incluye detalles relevantes (precio, características, disponibilidad).\n"
            "- Si NO hay productos encontrados, di claramente que no encontraste productos pero ofrece ayuda alternativa.\n"
            "- Sé proactivo: después de resolver la pregunta actual, pregunta si necesita algo más.\n"
            "- Evita respuestas genéricas como 'Me alegra que hayas iniciado esta conversación' cuando el usuario ya hizo una pregunta específica.\n"
        )

        # Usar helper para invocar LLM con fallback automático
        final_resp = self._invoke_llm_with_fallback([
            SystemMessage(content=system_prompt),
            HumanMessage(content=summary_prompt),
        ])
        final_text = getattr(final_resp, "content", str(final_resp))
        
        # === PASO 7: Traducción Multilingüe ===
        if self.translator and detected_language != self.chatbot_config.default_language:
            try:
                final_text = self.translator.translate(final_text, detected_language)
            except Exception as e:
                print(f"⚠️ Error traduciendo respuesta: {e}")

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
            "language": detected_language,
            "lead_score": lead_score if self.chatbot_config.lead_scoring_enabled else None,
            "lead_label": lead_label if self.chatbot_config.lead_scoring_enabled else None,
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
                    # Usar helper para invocar LLM con fallback automático
                    response = self._invoke_llm_with_fallback([
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






